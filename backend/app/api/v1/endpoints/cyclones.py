import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.entities import Cyclone, Observation, Prediction, PredictionPoint, RiskZone, PopulationExposure
from backend.app.schemas.entities import (
    CycloneOut, CycloneCreate, ObservationOut, PredictionOut,
    RiskZoneOut, PopulationExposureOut
)
from ml.pipeline import ml_pipeline

router = APIRouter()

from datetime import datetime, timezone
from data.adapters.ibtracs import IBTrACSAdapter

def _format_ibtracs_storm(storm: dict) -> dict:
    pts = storm.get("track", [])
    first_time = pts[0]["time"] if pts else "2023-01-01T00:00:00Z"
    last_time = pts[-1]["time"] if pts else first_time
    genesis = datetime.fromisoformat(first_time.replace("Z", "+00:00"))
    dissipation = datetime.fromisoformat(last_time.replace("Z", "+00:00"))
    last_pt = pts[-1] if pts else {"lat": 20.0, "lon": 70.0}
    basin_raw = storm.get("basin", "North Indian Ocean")
    basin_clean = "Arabian Sea" if "Arabian" in basin_raw else ("Bay of Bengal" if "Bengal" in basin_raw else basin_raw)
    
    return {
        "id": f"ibtracs-{storm['name'].lower()}-{storm['year']}",
        "name": storm["name"],
        "basin": basin_clean,
        "status": "historical",
        "current_lat": last_pt["lat"],
        "current_lon": last_pt["lon"],
        "current_wind_speed_kts": storm["max_wind_kts"],
        "current_pressure_hpa": storm["min_pressure_hpa"],
        "current_category": storm["category"],
        "current_heading_deg": 40.0,
        "current_speed_kmh": 14.0,
        "confidence_score": 1.0,
        "risk_level": "Past Landfall Event",
        "genesis_time": genesis,
        "dissipation_time": dissipation,
        "created_at": genesis,
        "updated_at": dissipation
    }

@router.get("", response_model=List[CycloneOut])
def get_all_cyclones(status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Cyclone)
    if status_filter:
        query = query.filter(Cyclone.status == status_filter)
    active_cyclones = query.order_by(Cyclone.updated_at.desc()).all()
    
    # If status_filter is specifically not "active", include historical catalog from IBTrACS
    results = list(active_cyclones)
    if status_filter in [None, "historical", "HISTORICAL"]:
        for storm in IBTrACSAdapter.HISTORICAL_CATALOG:
            # Skip Biparjoy if it's already in active_cyclones
            if storm["name"].upper() == "BIPARJOY" and any(c.name.upper() == "BIPARJOY" for c in active_cyclones):
                continue
            results.append(_format_ibtracs_storm(storm))
            
    return results

@router.get("/{cyclone_id}", response_model=CycloneOut)
def get_cyclone_by_id(cyclone_id: str, db: Session = Depends(get_db)):
    cyclone = db.query(Cyclone).filter(Cyclone.id == cyclone_id).first()
    if cyclone:
        return cyclone
    
    # Check IBTrACS historical catalog
    for storm in IBTrACSAdapter.HISTORICAL_CATALOG:
        formatted = _format_ibtracs_storm(storm)
        if formatted["id"] == cyclone_id or storm.get("sid") == cyclone_id or storm["name"].lower() == cyclone_id.lower():
            return formatted
            
    raise HTTPException(status_code=404, detail="Cyclone not found")

@router.get("/{cyclone_id}/track", response_model=List[ObservationOut])
def get_cyclone_track(cyclone_id: str, db: Session = Depends(get_db)):
    cyclone = db.query(Cyclone).filter(Cyclone.id == cyclone_id).first()
    if cyclone:
        return db.query(Observation).filter(Observation.cyclone_id == cyclone_id).order_by(Observation.timestamp.asc()).all()

    # Check IBTrACS historical catalog
    for storm in IBTrACSAdapter.HISTORICAL_CATALOG:
        formatted = _format_ibtracs_storm(storm)
        if formatted["id"] == cyclone_id or storm.get("sid") == cyclone_id or storm["name"].lower() == cyclone_id.lower():
            observations = []
            for idx, pt in enumerate(storm.get("track", [])):
                t_str = pt["time"].replace("Z", "+00:00")
                t_dt = datetime.fromisoformat(t_str)
                observations.append({
                    "id": f"obs-{storm['name'].lower()}-{idx}",
                    "cyclone_id": formatted["id"],
                    "timestamp": t_dt,
                    "lat": pt["lat"],
                    "lon": pt["lon"],
                    "wind_speed_kts": pt.get("wind_kts", 45.0),
                    "central_pressure_hpa": pt.get("pressure_hpa", 990.0),
                    "imd_category": storm["category"],
                    "source": "NOAA IBTrACS v04r00",
                    "is_forecast": False,
                    "created_at": t_dt
                })
            return observations

    raise HTTPException(status_code=404, detail="Cyclone not found")

@router.get("/{cyclone_id}/forecast")
def get_cyclone_forecast(cyclone_id: str, db: Session = Depends(get_db)):
    cyclone = db.query(Cyclone).filter(Cyclone.id == cyclone_id).first()
    if not cyclone:
        for storm in IBTrACSAdapter.HISTORICAL_CATALOG:
            formatted = _format_ibtracs_storm(storm)
            if formatted["id"] == cyclone_id or storm.get("sid") == cyclone_id or storm["name"].lower() == cyclone_id.lower():
                pts = storm.get("track", [])
                last_pt = pts[-1] if pts else {"lat": 20.0, "lon": 70.0, "wind_kts": 65.0, "pressure_hpa": 980.0}
                return ml_pipeline.run_full_inference(
                    cyclone_id=formatted["id"],
                    current_lat=last_pt["lat"],
                    current_lon=last_pt["lon"],
                    current_wind_kts=last_pt.get("wind_kts", 65.0),
                    current_pressure_hpa=last_pt.get("pressure_hpa", 980.0),
                    current_heading_deg=40.0,
                    current_speed_kmh=14.0
                )
        raise HTTPException(status_code=404, detail="Cyclone not found")

    prediction = db.query(Prediction).filter(Prediction.cyclone_id == cyclone_id).order_by(Prediction.run_timestamp.desc()).first()
    if not prediction:
        # Run on the fly with ML pipeline
        inference = ml_pipeline.run_full_inference(
            cyclone_id=cyclone.id,
            current_lat=cyclone.current_lat or 21.65,
            current_lon=cyclone.current_lon or 66.85,
            current_wind_kts=cyclone.current_wind_speed_kts or 85.0,
            current_pressure_hpa=cyclone.current_pressure_hpa or 964.0,
            current_heading_deg=cyclone.current_heading_deg or 38.0,
            current_speed_kmh=cyclone.current_speed_kmh or 11.5
        )
        return inference

    points = db.query(PredictionPoint).filter(PredictionPoint.prediction_id == prediction.id).order_by(PredictionPoint.forecast_hour.asc()).all()
    return {
        "cyclone_id": cyclone.id,
        "model_version": prediction.model_version,
        "run_timestamp": prediction.run_timestamp.isoformat(),
        "overall_confidence": prediction.overall_confidence,
        "detection_status": prediction.detection_status,
        "development_stage": prediction.development_stage,
        "explanation": prediction.explanation,
        "forecast_points": [
            {
                "forecast_hour": p.forecast_hour,
                "valid_time": p.valid_time.isoformat(),
                "lat": p.lat,
                "lon": p.lon,
                "predicted_wind_speed_kts": p.predicted_wind_speed_kts,
                "predicted_wind_speed_kmh": round(p.predicted_wind_speed_kts * 1.852, 1),
                "predicted_pressure_hpa": p.predicted_pressure_hpa,
                "category": p.category,
                "uncertainty_radius_km": p.uncertainty_radius_km,
                "confidence_score": p.confidence_score
            }
            for p in points
        ]
    }

@router.get("/{cyclone_id}/risk")
def get_cyclone_risk_zones(cyclone_id: str, db: Session = Depends(get_db)):
    cyclone = db.query(Cyclone).filter(Cyclone.id == cyclone_id).first()
    if not cyclone:
        raise HTTPException(status_code=404, detail="Cyclone not found")

    zones = db.query(RiskZone).filter(RiskZone.cyclone_id == cyclone_id).all()
    return [
        {
            "id": z.id,
            "forecast_hour": z.forecast_hour,
            "zone_type": z.zone_type,
            "severity": z.severity,
            "hazard_score": z.hazard_score,
            "exposure_score": z.exposure_score,
            "vulnerability_score": z.vulnerability_score,
            "composite_risk_score": z.composite_risk_score,
            "affected_district": z.affected_district,
            "affected_state": z.affected_state,
            "polygon_geojson": z.polygon_geojson
        }
        for z in zones
    ]

@router.get("/{cyclone_id}/exposure")
def get_cyclone_exposure(cyclone_id: str, db: Session = Depends(get_db)):
    cyclone = db.query(Cyclone).filter(Cyclone.id == cyclone_id).first()
    if not cyclone:
        raise HTTPException(status_code=404, detail="Cyclone not found")

    records = (
        db.query(PopulationExposure)
        .join(RiskZone)
        .filter(RiskZone.cyclone_id == cyclone_id)
        .all()
    )
    return [
        {
            "id": r.id,
            "district": r.district,
            "total_population": r.total_population,
            "vulnerable_population": r.vulnerable_population,
            "evacuation_needed_count": r.evacuation_needed_count,
            "data_source": r.dataSource
        }
        for r in records
    ]

@router.get("/{cyclone_id}/location-intelligence")
def get_location_specific_intelligence(
    cyclone_id: str,
    lat: float = 23.2380,
    lon: float = 68.6180,
    db: Session = Depends(get_db)
):
    """
    Computes location-specific intelligence when an operator clicks on the map:
    - Distance to cyclone center
    - Local risk score and risk category
    - Nearest shelter and nearest hospital
    - Evacuation route and transit time
    - Actionable recommendations
    """
    cyclone = db.query(Cyclone).filter(Cyclone.id == cyclone_id).first()
    if not cyclone:
        raise HTTPException(status_code=404, detail="Cyclone not found")

    from geospatial.routing import EvacuationRoutingEngine
    from geospatial.risk_engine import RiskEngine
    from data.adapters.osm_overpass import OSMOverpassAdapter
    from alerts.templates import ALERT_ACTION_TEMPLATES

    c_lat = cyclone.current_lat or 21.65
    c_lon = cyclone.current_lon or 66.85
    c_wind = cyclone.current_wind_speed_kts or 85.0
    c_press = cyclone.current_pressure_hpa or 964.0

    # 1. Distance in km and Bearing in degrees
    dist_to_eye_km = EvacuationRoutingEngine.haversine_distance_km(lat, lon, c_lat, c_lon)
    d_lon_rad = math.radians(lon - c_lon)
    lat1_rad = math.radians(c_lat)
    lat2_rad = math.radians(lat)
    y_b = math.sin(d_lon_rad) * math.cos(lat2_rad)
    x_b = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lon_rad)
    bearing_deg = (math.degrees(math.atan2(y_b, x_b)) + 360.0) % 360.0

    # 2. Local wind estimation using Holland vortex profile approximation
    r_max_km = 45.0 # Radius of maximum winds
    if dist_to_eye_km < r_max_km:
        local_wind_kts = c_wind * (dist_to_eye_km / r_max_km)
    else:
        decay = (r_max_km / max(r_max_km, dist_to_eye_km)) ** 0.55
        local_wind_kts = max(20.0, c_wind * decay)

    # 3. Local Risk Calculation
    risk_assessment = RiskEngine.calculate_risk(
        wind_speed_kts=local_wind_kts,
        central_pressure_hpa=c_press + min(30.0, dist_to_eye_km * 0.12),
        distance_to_coast_km=max(5.0, min(150.0, dist_to_eye_km * 0.4)),
        population_count=650000,
        critical_infrastructure_count=18,
        coastal_elevation_m=6.0,
        forecast_lead_time_hours=24
    )

    # 4. Nearest Facilities
    all_facilities = OSMOverpassAdapter.get_facilities()
    shelters = [f for f in all_facilities if f["facility_type"] == "shelter"]
    hospitals = [f for f in all_facilities if f["facility_type"] == "hospital"]

    nearest_shelters = EvacuationRoutingEngine.find_nearest_facilities(lat, lon, shelters, top_k=2)
    nearest_hospitals = EvacuationRoutingEngine.find_nearest_facilities(lat, lon, hospitals, top_k=2)

    # 5. Evacuation Route to Closest Shelter
    target_shelter = nearest_shelters[0] if nearest_shelters else shelters[0]
    route_plan = EvacuationRoutingEngine.generate_evacuation_route(
        origin_lat=lat,
        origin_lon=lon,
        origin_name=f"Selected Location ({lat:.3f}°N, {lon:.3f}°E)",
        shelter=target_shelter,
        cyclone_center_lat=c_lat,
        cyclone_center_lon=c_lon
    )

    # 6. Actionable recommendations based on local risk tier
    category = risk_assessment["risk_category"]
    actions = ALERT_ACTION_TEMPLATES.get("Citizens", {}).get(
        category,
        ALERT_ACTION_TEMPLATES.get("Citizens", {}).get("Moderate Risk", [])
    )

    # 7. Additional operational kinematics & surge proxy
    landfall_lat, landfall_lon = 23.28, 68.65  # Forecast landfall point near Jakhau
    landfall_proximity_km = round(EvacuationRoutingEngine.haversine_distance_km(lat, lon, landfall_lat, landfall_lon), 1)

    speed_kmh = max(6.0, float(cyclone.current_speed_kmh or 11.5))
    gale_radius_km = 120.0
    if dist_to_eye_km <= gale_radius_km:
        gale_onset_hours = 0.0
        gale_onset_text = "CURRENT / IMMINENT (Inside Gale Radius)"
    else:
        gale_onset_hours = round((dist_to_eye_km - gale_radius_km) / speed_kmh, 1)
        gale_onset_text = f"~{gale_onset_hours} hours"

    peak_intensity_window = "T+24h to T+36h (Landfall Horizon)"

    # Empirical surge proxy based on local wind & distance
    if local_wind_kts >= 64:
        inundation_risk = "Extreme (Estimated 3.0m - 4.5m Surge Inundation)"
    elif local_wind_kts >= 45:
        inundation_risk = "High (Estimated 2.0m - 3.0m Surge Inundation)"
    elif local_wind_kts >= 30:
        inundation_risk = "Moderate (Estimated 1.0m - 2.0m Surge Inundation)"
    else:
        inundation_risk = "Low (Wave Runup < 1.0m)"

    return {
        "location": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "cyclone_distance_km": round(dist_to_eye_km, 1),
        "bearing_deg": round(bearing_deg, 1),
        "landfall_proximity_km": landfall_proximity_km,
        "gale_onset_hours": gale_onset_hours,
        "gale_onset_text": gale_onset_text,
        "peak_intensity_window": peak_intensity_window,
        "inundation_risk": inundation_risk,
        "local_estimated_wind_kts": round(local_wind_kts, 1),
        "local_estimated_wind_kmh": round(local_wind_kts * 1.852, 1),
        "risk": risk_assessment,
        "nearest_shelter": nearest_shelters[0] if nearest_shelters else None,
        "nearest_hospital": nearest_hospitals[0] if nearest_hospitals else None,
        "evacuation_corridor": route_plan,
        "recommended_actions": actions,
        "confidence_score": cyclone.confidence_score or 0.92,
        "disclaimer": "Location-specific decision intelligence. Evacuation routing provides recommended corridors; follow official District Collectorate emergency orders."
    }


