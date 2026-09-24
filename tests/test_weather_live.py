import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.weather_cache import weather_cache

client = TestClient(app)

def test_weather_live_endpoint_structure():
    response = client.get("/api/v1/weather/live")
    assert response.status_code == 200
    data = response.json()
    assert "data_status" in data
    assert data["data_status"] in ["LIVE", "FALLBACK", "STALE", "INITIALIZING"]
    assert "coordinates" in data
    assert "surface_wind_10m_kts" in data
    assert "sea_level_pressure_hpa" in data
    assert "relative_humidity_pct" in data
    assert "air_temperature_2m_c" in data
    assert "sea_surface_temp_c" in data
    assert "poll_interval_seconds" in data
    assert data["poll_interval_seconds"] == 900.0

def test_weather_live_staleness_logic():
    # Simulate an entry older than 1800s
    weather_cache._cache["data_status"] = "LIVE"
    weather_cache._cache["last_sync_timestamp"] = 1000.0 # very old timestamp
    res = weather_cache.get(max_stale_seconds=10.0)
    assert res["data_status"] == "STALE"
    assert res["age_seconds"] is not None and res["age_seconds"] > 10.0

def test_weather_live_on_demand_refresh():
    response = client.get("/api/v1/weather/live?refresh=true")
    assert response.status_code == 200
    data = response.json()
    assert data["data_status"] in ["LIVE", "FALLBACK"]
    assert data["surface_wind_10m_kts"] is not None
    assert data["sea_level_pressure_hpa"] is not None
    assert data["last_sync_utc"] is not None

