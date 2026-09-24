import pytest
from geospatial.risk_engine import RiskEngine

def test_risk_boundary_values_zero_population():
    res = RiskEngine.calculate_risk(
        wind_speed_kts=120.0, # Category 4-5
        central_pressure_hpa=930.0,
        distance_to_coast_km=20.0,
        population_count=0, # Zero exposed humans
        critical_infrastructure_count=0,
        coastal_elevation_m=2.0
    )
    # Even with 0 population, atmospheric hazard is extreme
    assert res["hazard_score"] > 0.8
    assert res["exposure_score"] <= 0.35
    assert 0.0 <= res["risk_score"] <= 1.0

def test_risk_boundary_values_extreme_elevation():
    res = RiskEngine.calculate_risk(
        wind_speed_kts=45.0,
        central_pressure_hpa=995.0,
        distance_to_coast_km=250.0,
        population_count=10000,
        critical_infrastructure_count=1,
        coastal_elevation_m=80.0 # High cliff/mountain
    )
    assert res["risk_category"] in ["Low Risk", "Moderate Risk"]
    assert res["risk_score"] < 0.50

def test_risk_lead_time_uncertainty_scaling():
    r_near = RiskEngine.calculate_risk(
        wind_speed_kts=85.0, central_pressure_hpa=964.0, distance_to_coast_km=50.0,
        population_count=500000, critical_infrastructure_count=20,
        forecast_lead_time_hours=6
    )
    r_far = RiskEngine.calculate_risk(
        wind_speed_kts=85.0, central_pressure_hpa=964.0, distance_to_coast_km=50.0,
        population_count=500000, critical_infrastructure_count=20,
        forecast_lead_time_hours=72
    )
    # 72h has higher uncertainty discount than 6h
    assert r_far["uncertainty_score"] > r_near["uncertainty_score"]
    assert "formula_metadata" in r_near

