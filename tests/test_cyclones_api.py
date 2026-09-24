from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_get_cyclones():
    res = client.get("/api/v1/cyclones")
    assert res.status_code == 200
    cyclones = res.json()
    assert len(cyclones) >= 1
    assert cyclones[0]["name"] == "BIPARJOY"

def test_get_cyclone_details():
    res = client.get("/api/v1/cyclones/demo-biparjoy-2023")
    assert res.status_code == 200
    c = res.json()
    assert c["name"] == "BIPARJOY"
    assert c["current_category"] == "Very Severe Cyclonic Storm"

def test_get_cyclone_forecast():
    res = client.get("/api/v1/cyclones/demo-biparjoy-2023/forecast")
    assert res.status_code == 200
    fc = res.json()
    assert "forecast_points" in fc
    assert len(fc["forecast_points"]) == 5

def test_get_cyclone_risk_and_exposure():
    r_risk = client.get("/api/v1/cyclones/demo-biparjoy-2023/risk")
    assert r_risk.status_code == 200
    assert len(r_risk.json()) >= 1

    r_exp = client.get("/api/v1/cyclones/demo-biparjoy-2023/exposure")
    assert r_exp.status_code == 200
    assert len(r_exp.json()) >= 1

def test_get_facilities_and_shelters():
    res_shelters = client.get("/api/v1/facilities/shelters")
    assert res_shelters.status_code == 200
    assert len(res_shelters.json()) >= 1

def test_get_alerts():
    res_alerts = client.get("/api/v1/alerts")
    assert res_alerts.status_code == 200
    assert len(res_alerts.json()) >= 1

def test_historical_analogs():
    res = client.get("/api/v1/historical/analogs?lat=21.65&lon=66.85&wind_speed_kts=85.0")
    assert res.status_code == 200
    data = res.json()
    assert "analogs" in data
    assert len(data["analogs"]) >= 1

