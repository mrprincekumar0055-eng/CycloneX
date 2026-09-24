"""
Seed Database with CycloneX Demo & Benchmark Data
Creates tables and inserts verified initial data for testing and demonstrations.
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import Base, engine, SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.entities import (
    Role, User, Cyclone, Observation, Prediction, PredictionPoint,
    RiskZone, PopulationExposure, Facility, Shelter, Hospital, Route,
    Alert, ModelVersion, ModelMetric, DataSource
)
from ml.pipeline import ml_pipeline
from geospatial.cones import ConeGenerator
from geospatial.risk_engine import RiskEngine
from geospatial.exposure import ExposureEngine
from geospatial.routing import EvacuationRoutingEngine
from alerts.engine import AlertEngine
from data.adapters.osm_overpass import OSMOverpassAdapter
from data.demo_scenarios.biparjoy import DEMO_BIPARJOY

def seed():
    print("[CycloneX] Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Seed Roles
        roles_data = [
            ("admin", "Platform Administrator with full access"),
            ("official", "District Collector / Disaster Management Official"),
            ("responder", "First Responder / NDRF / SDRF / Coast Guard"),
            ("citizen", "General Public Coastal Resident")
        ]
        role_map = {}
        for r_name, r_desc in roles_data:
            role = db.query(Role).filter_by(name=r_name).first()
            if not role:
                role = Role(name=r_name, description=r_desc)
                db.add(role)
                db.flush()
            role_map[r_name] = role

        # 2. Seed Default Users
        if not db.query(User).filter_by(email="admin@cyclonex.gov.in").first():
            admin_user = User(
                email="admin@cyclonex.gov.in",
                full_name="National Cyclone Warning Centre (NCWC)",
                hashed_password=get_password_hash("Admin@CycloneX2026"),
                role_id=role_map["admin"].id,
                is_active=True
            )
            db.add(admin_user)

        if not db.query(User).filter_by(email="collector.kutch@gujarat.gov.in").first():
            official_user = User(
                email="collector.kutch@gujarat.gov.in",
                full_name="District Magistrate & Collector, Kutch",
                hashed_password=get_password_hash("Kutch@Disaster2026"),
                role_id=role_map["official"].id,
                is_active=True
            )
            db.add(official_user)

        # 3. Seed Active Cyclone (Biparjoy)
        cyc_info = DEMO_BIPARJOY["cyclone"]
        cyclone = db.query(Cyclone).filter_by(name=cyc_info["name"]).first()
        if not cyclone:
            cyclone = Cyclone(
                id=cyc_info["id"],
                name=cyc_info["name"],
                basin=cyc_info["basin"],
                status=cyc_info["status"],
                current_lat=cyc_info["current_lat"],
                current_lon=cyc_info["current_lon"],
                current_wind_speed_kts=cyc_info["current_wind_speed_kts"],
                current_pressure_hpa=cyc_info["current_pressure_hpa"],
                current_category=cyc_info["current_category"],
                current_heading_deg=cyc_info["current_heading_deg"],
                current_speed_kmh=cyc_info["current_speed_kmh"],
                confidence_score=cyc_info["confidence_score"],
                risk_level=cyc_info["risk_level"]
            )
            db.add(cyclone)
            db.flush()

            # Add historical track observations
            for obs in DEMO_BIPARJOY["historical_observations"]:
                o = Observation(
                    cyclone_id=cyclone.id,
                    timestamp=datetime.fromisoformat(obs["timestamp"].replace("Z", "+00:00")),
                    lat=obs["lat"],
                    lon=obs["lon"],
                    wind_speed_kts=obs["wind_speed_kts"],
                    central_pressure_hpa=obs["central_pressure_hpa"],
                    imd_category=obs["imd_category"],
                    source="IMD / JTWC Verified",
                    is_forecast=False
                )
                db.add(o)

            # 4. Generate AI Inference & Predictions
            inference = ml_pipeline.run_full_inference(
                cyclone_id=cyclone.id,
                current_lat=cyclone.current_lat,
                current_lon=cyclone.current_lon,
                current_wind_kts=cyclone.current_wind_speed_kts,
                current_pressure_hpa=cyclone.current_pressure_hpa,
                current_heading_deg=cyclone.current_heading_deg,
                current_speed_kmh=cyclone.current_speed_kmh,
                sst_c=DEMO_BIPARJOY["environmental"]["sst_c"],
                wind_shear_kts=DEMO_BIPARJOY["environmental"]["wind_shear_kts"],
                cloud_top_temp_c=DEMO_BIPARJOY["environmental"]["cloud_top_temp_c"]
            )

            prediction = Prediction(
                cyclone_id=cyclone.id,
                model_version=inference["model_version"],
                run_timestamp=datetime.fromisoformat(inference["inference_timestamp"]),
                overall_confidence=inference["detection"]["probability"],
                detection_status=inference["detection"]["status"],
                development_stage=inference["classification"]["imd_label"],
                explanation=inference["explanation"]["summary"]
            )
            db.add(prediction)
            db.flush()

            forecast_pts_for_cone = []
            for fp in inference["forecast_points"]:
                pred_pt = PredictionPoint(
                    prediction_id=prediction.id,
                    forecast_hour=fp["forecast_hour"],
                    valid_time=datetime.fromisoformat(fp["valid_time"]),
                    lat=fp["lat"],
                    lon=fp["lon"],
                    predicted_wind_speed_kts=fp["predicted_wind_speed_kts"],
                    predicted_pressure_hpa=fp["predicted_pressure_hpa"],
                    category=fp["category"],
                    uncertainty_radius_km=fp["uncertainty_radius_km"],
                    confidence_score=fp["confidence_score"]
                )
                db.add(pred_pt)
                forecast_pts_for_cone.append(fp)

            # 5. Risk Zones (Uncertainty cone & wind swaths)
            cone_geo = ConeGenerator.generate_uncertainty_cone(forecast_pts_for_cone)
            risk_zone = RiskZone(
                cyclone_id=cyclone.id,
                forecast_hour=24,
                zone_type="uncertainty_cone_envelope",
                severity="High",
                hazard_score=0.88,
                exposure_score=0.82,
                vulnerability_score=0.75,
                composite_risk_score=0.85,
                affected_district="Kutch Coastal Corridor",
                affected_state="Gujarat",
                polygon_geojson=cone_geo
            )
            db.add(risk_zone)
            db.flush()

            # 6. Population Exposure
            exposures = ExposureEngine.calculate_district_exposure(
                cyclone_name=cyclone.name,
                wind_speed_kts=cyclone.current_wind_speed_kts
            )
            for exp in exposures[:3]:
                pop_rec = PopulationExposure(
                    risk_zone_id=risk_zone.id,
                    district=exp["district"],
                    total_population=exp["total_population"],
                    vulnerable_population=exp["vulnerable_population"],
                    evacuation_needed_count=exp["evacuation_needed"],
                    dataSource=exp["data_source"]
                )
                db.add(pop_rec)

            # 7. Facilities, Shelters & Hospitals
            facilities = OSMOverpassAdapter.get_facilities()
            shelter_entity_list = []
            for fac in facilities:
                f_obj = Facility(
                    id=fac["id"],
                    name=fac["name"],
                    facility_type=fac["facility_type"],
                    lat=fac["lat"],
                    lon=fac["lon"],
                    district=fac.get("district"),
                    state=fac.get("state"),
                    is_officially_verified=fac.get("is_verified", False)
                )
                db.add(f_obj)
                
                if fac["facility_type"] == "shelter":
                    s_obj = Shelter(
                        id=f"sh-{fac['id']}",
                        facility_id=fac["id"],
                        name=fac["name"],
                        lat=fac["lat"],
                        lon=fac["lon"],
                        total_capacity=fac.get("total_capacity", 1500),
                        current_occupancy=fac.get("current_occupancy", 0),
                        elevation_meters=fac.get("elevation_meters", 12.0),
                        is_verified=fac.get("is_verified", True)
                    )
                    db.add(s_obj)
                    shelter_entity_list.append(fac)
                elif fac["facility_type"] == "hospital":
                    h_obj = Hospital(
                        id=f"hosp-{fac['id']}",
                        facility_id=fac["id"],
                        name=fac["name"],
                        lat=fac["lat"],
                        lon=fac["lon"],
                        total_beds=fac.get("total_beds", 250),
                        available_icu_beds=fac.get("available_icu_beds", 15),
                        emergency_trauma_unit=fac.get("emergency_trauma_unit", True),
                        helipad=fac.get("helipad", False)
                    )
                    db.add(h_obj)

            # 8. Evacuation Route (from Jakhau Fishery Port to Naliya Shelter)
            if shelter_entity_list:
                target_shelter = shelter_entity_list[0]
                route_res = EvacuationRoutingEngine.generate_evacuation_route(
                    origin_lat=23.2380,
                    origin_lon=68.6180,
                    origin_name="Jakhau Coastal Settlement",
                    shelter=target_shelter,
                    cyclone_center_lat=cyclone.current_lat,
                    cyclone_center_lon=cyclone.current_lon
                )
                evac_route = Route(
                    origin_name=route_res["origin"]["name"],
                    destination_shelter_id=f"sh-{target_shelter['id']}",
                    destination_name=route_res["destination"]["name"],
                    distance_km=route_res["distance_km"],
                    travel_time_minutes=route_res["travel_time_minutes"],
                    route_risk_level=route_res["route_risk_level"],
                    route_geojson=route_res["route_geojson"],
                    source="OSRM / Geodesic Evacuation Engine"
                )
                db.add(evac_route)

            # 9. Multi-Stakeholder Alerts
            alerts = AlertEngine.generate_alerts(
                cyclone_name=cyclone.name,
                category=cyclone.current_category,
                wind_speed_kts=cyclone.current_wind_speed_kts,
                central_pressure_hpa=cyclone.current_pressure_hpa,
                risk_level=cyclone.risk_level,
                target_location=DEMO_BIPARJOY["target_landfall"]["location"],
                landfall_eta_hours=DEMO_BIPARJOY["target_landfall"]["eta_hours"]
            )
            for alt in alerts:
                a_obj = Alert(
                    cyclone_id=cyclone.id,
                    severity=alt["severity"],
                    audience=alt["audience"],
                    headline=alt["headline"],
                    hazard=alt["hazard"],
                    expected_time=datetime.fromisoformat(alt["expected_time"]),
                    location_description=alt["location_description"],
                    explanation=alt["explanation"],
                    recommended_actions=alt["recommended_actions"],
                    confidence_pct=alt["confidence_pct"],
                    official_source=alt["official_source"],
                    is_official_warning=alt["is_official_warning"]
                )
                db.add(a_obj)

            # 10. Data Sources Health Status
            sources = [
                ("NOAA IBTrACS", "https://www.ncei.noaa.gov/products/international-best-track-archive", "Healthy", 95, 1420),
                ("NASA GIBS", "https://gibs.earthdata.nasa.gov", "Healthy", 110, 840),
                ("Open-Meteo", "https://api.open-meteo.com", "Healthy", 85, 3600),
                ("WorldPop", "https://data.worldpop.org", "Healthy", 130, 280),
                ("OpenStreetMap Overpass", "https://overpass-api.de", "Healthy", 140, 520)
            ]
            for s_name, s_url, s_stat, s_lat, s_rec in sources:
                ds = DataSource(
                    source_name=s_name,
                    source_url=s_url,
                    status=s_stat,
                    latency_ms=s_lat,
                    records_count=s_rec
                )
                db.add(ds)

            # 11. Model Versions & Metrics
            mv = ModelVersion(
                name="CycloneX Multimodal Core",
                version="v1.2-ensemble-fusion",
                task_type="Multimodal Detection & Track Projection",
                framework="Scikit-Learn / PyTorch",
                dataset_version="IBTrACS-v04r00-NI-2023",
                parameters={"n_estimators": 100, "uncertainty_scaling": "empirical_nhc_imd"}
            )
            db.add(mv)
            db.flush()

            metrics = [
                ("Track_Error_24h_km", 88.4),
                ("Track_Error_48h_km", 146.2),
                ("Intensity_MAE_kts", 7.8),
                ("Detection_F1_Score", 0.942)
            ]
            for m_name, m_val in metrics:
                db.add(ModelMetric(
                    model_version_id=mv.id,
                    metric_name=m_name,
                    metric_value=m_val
                ))

        db.commit()
        print("[CycloneX] Database successfully seeded with demo and operational models.")
    except Exception as e:
        db.rollback()
        print(f"[CycloneX] Error during database seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()

