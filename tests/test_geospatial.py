import pytest
from geospatial.cones import ConeGenerator
from geospatial.risk_engine import RiskEngine
from geospatial.routing import EvacuationRoutingEngine
from geospatial.exposure import ExposureEngine
from alerts.engine import AlertEngine

def test_risk_engine_calculation():
    res = RiskEngine.calculate_risk(
        wind_speed_kts=85.0,
        central_pressure_hpa=964.0,
        distance_to_coast_km=45.0,
        population_count=1_200_000,
        critical_infrastructure_count=35,
        coastal_elevation_m=4.0
    )
    assert 0.0 <= res["hazard_score"] <= 1.0
    assert 0.0 <= res["exposure_score"] <= 1.0
    assert 0.0 <= res["composite_risk_score"] <= 1.0
    assert res["risk_level"] in ["High Risk", "Extreme Risk"]
    assert "disclaimer" in res

def test_uncertainty_cone_generation():
    forecast_points = [
        {"lat": 21.65, "lon": 66.85, "uncertainty_radius_km": 35.0},
        {"lat": 22.35, "lon": 67.45, "uncertainty_radius_km": 60.0},
        {"lat": 23.20, "lon": 68.40, "uncertainty_radius_km": 95.0},
    ]
    cone = ConeGenerator.generate_uncertainty_cone(forecast_points)
    assert cone["type"] == "Feature"
    assert cone["geometry"]["type"] in ["Polygon", "MultiPolygon"]
    assert len(cone["geometry"]["coordinates"]) > 0

def test_evacuation_routing_and_nearest_shelter():
    shelters = [
        {"id": "s1", "name": "Shelter A", "lat": 23.25, "lon": 68.80, "total_capacity": 1000},
        {"id": "s2", "name": "Shelter B", "lat": 23.50, "lon": 69.10, "total_capacity": 800}
    ]
    nearest = EvacuationRoutingEngine.find_nearest_facilities(
        origin_lat=23.23,
        origin_lon=68.62,
        facilities=shelters,
        top_k=2
    )
    assert len(nearest) == 2
    assert nearest[0]["id"] == "s1"
    assert nearest[0]["distance_km"] < nearest[1]["distance_km"]

def test_alert_engine_generation():
    alerts = AlertEngine.generate_alerts(
        cyclone_name="BIPARJOY",
        category="Very Severe Cyclonic Storm",
        wind_speed_kts=85.0,
        central_pressure_hpa=964.0,
        risk_level="Extreme Risk",
        target_location="Kutch Coast"
    )
    assert len(alerts) == 3 # Citizens, Authorities, Responders
    audiences = [a["audience"] for a in alerts]
    assert "Citizens" in audiences
    assert "Authorities" in audiences
    assert "Emergency Responders" in audiences
    for a in alerts:
        assert len(a["recommended_actions"]) > 0
        assert a["is_official_warning"] is False

