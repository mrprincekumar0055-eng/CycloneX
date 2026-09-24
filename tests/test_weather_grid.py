import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.india_grid import INDIA_GRID_POINTS, calculate_disturbance_score
from backend.app.core.weather_cache import weather_cache

client = TestClient(app)

def test_india_grid_definitions():
    assert len(INDIA_GRID_POINTS) >= 40
    # Confirm key cyclone-prone states and offshore nodes are present
    states = set(p["state"] for p in INDIA_GRID_POINTS)
    for expected in ["Gujarat", "Maharashtra", "Odisha", "West Bengal", "Tamil Nadu", "Andhra Pradesh", "Kerala", "Karnataka"]:
        assert expected in states

def test_disturbance_score_bounds_and_weights():
    # 1. Calm baseline (no wind, standard pressure 1013.25, zero rain)
    calm = calculate_disturbance_score(wind_kts=0.0, gust_kts=0.0, pressure_hpa=1013.25, precip_mm=0.0)
    assert calm["disturbance_score"] == 0.0
    assert calm["category"] == "QUIET / AMBIENT"
    assert calm["indicator_color"] == "emerald"

    # 2. Extreme Cyclonic Hurricane conditions (wind 130 kts, pressure 920 hPa, rain 60 mm/h)
    extreme = calculate_disturbance_score(wind_kts=130.0, gust_kts=160.0, pressure_hpa=920.0, precip_mm=60.0)
    assert extreme["disturbance_score"] == 100.0
    assert extreme["category"] == "EXTREME DISTURBANCE"
    assert extreme["indicator_color"] == "red"

    # 3. Severe cyclonic storm (wind 65 kts, pressure 973.25 hPa [-40 hPa deficit], rain 25 mm/h)
    severe = calculate_disturbance_score(wind_kts=65.0, gust_kts=65.0, pressure_hpa=973.25, precip_mm=25.0)
    assert severe["disturbance_score"] == 100.0

    # 4. Moderate disturbance
    mod = calculate_disturbance_score(wind_kts=30.0, gust_kts=40.0, pressure_hpa=1003.0, precip_mm=5.0)
    assert 25.0 <= mod["disturbance_score"] <= 60.0

def test_weather_grid_endpoint():
    response = client.get("/api/v1/weather/grid")
    assert response.status_code == 200
    data = response.json()
    assert "grid_points" in data
    assert "total_points" in data
    assert len(data["grid_points"]) >= 40
    
    # Confirm sorting: first point has score >= second point >= last point
    scores = [p["disturbance_score"] for p in data["grid_points"]]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1]

def test_weather_most_disturbed_endpoint():
    response = client.get("/api/v1/weather/most-disturbed")
    assert response.status_code == 200
    data = response.json()
    assert data["rank"] == 1
    assert "disturbance_score" in data
    assert "surface_wind_10m_kts" in data
    assert "sea_level_pressure_hpa" in data
    assert "selection_mode" in data
    assert data["selection_mode"] == "MOST_DISTURBED_AUTO_DETECT"

def test_weather_live_toggle_modes():
    # 1. Most disturbed mode
    res_disturbed = client.get("/api/v1/weather/live?target=most_disturbed")
    assert res_disturbed.status_code == 200
    data_dist = res_disturbed.json()
    assert "disturbance_score" in data_dist

    # 2. Biparjoy fixed mode
    res_bip = client.get("/api/v1/weather/live?target=biparjoy")
    assert res_bip.status_code == 200
    data_bip = res_bip.json()
    assert data_bip.get("selection_mode") == "FIXED_BIPARJOY_ANCHOR"
    assert abs(data_bip["coordinates"]["lat"] - 21.65) < 0.1
    assert abs(data_bip["coordinates"]["lon"] - 66.85) < 0.1

