import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import httpx
import time

from backend.app.main import app
from backend.app.core.weather_cache import weather_cache
from backend.app.services.weather_service import weather_service
from backend.app.core.india_grid import is_valid_coordinate, is_in_india_region, find_nearest_station

client = TestClient(app)

MOCK_OPEN_METEO_RESPONSE = {
    "latitude": 19.07,
    "longitude": 72.87,
    "generationtime_ms": 0.45,
    "utc_offset_seconds": 0,
    "timezone": "GMT",
    "timezone_abbreviation": "GMT",
    "elevation": 14.0,
    "current": {
        "time": "2026-09-17T14:45:00Z",
        "interval": 900,
        "temperature_2m": 31.2,
        "relative_humidity_2m": 78.0,
        "surface_pressure": 1008.4,
        "pressure_msl": 1010.2,
        "wind_speed_10m": 16.5,
        "wind_direction_10m": 240.0,
        "wind_gusts_10m": 24.2,
        "precipitation": 0.2,
        "rain": 0.2,
        "cloud_cover": 45.0,
        "weather_code": 2
    }
}

# 1. Valid Indian Coordinates
def test_valid_indian_coordinates():
    # Mumbai, Chennai, Kolkata, Delhi, Puri, Jakhau
    coords = [
        (19.07, 72.87), # Mumbai
        (13.08, 80.27), # Chennai
        (22.57, 88.36), # Kolkata
        (28.61, 77.20), # Delhi
        (19.81, 85.83), # Puri
        (23.24, 68.62), # Jakhau
    ]
    for lat, lon in coords:
        assert is_valid_coordinate(lat, lon) is True
        assert is_in_india_region(lat, lon) is True

# 2. Invalid Coordinates Handling
def test_invalid_coordinates_handling():
    # Out of latitude / longitude physical range
    assert is_valid_coordinate(120.0, 77.0) is False
    assert is_valid_coordinate(-95.0, 77.0) is False
    assert is_valid_coordinate(20.0, 200.0) is False
    assert is_valid_coordinate("not_a_number", 77.0) is False

    # Calling API with out-of-range coordinates should return HTTP 400
    res_lat = client.get("/api/v1/weather/live?lat=120.0&lon=77.0")
    assert res_lat.status_code == 400
    assert "Invalid geographic coordinates" in res_lat.json()["detail"]

    res_lon = client.get("/api/v1/weather/live?lat=20.0&lon=200.0")
    assert res_lon.status_code == 400

    # Only one coordinate provided should return HTTP 400
    res_one = client.get("/api/v1/weather/live?lat=20.0")
    assert res_one.status_code == 400

    # Strict India bounds validation check
    res_outside = client.get("/api/v1/weather/live?lat=51.5074&lon=-0.1278&strict_india=true") # London
    assert res_outside.status_code == 400
    assert "outside India monitoring domain" in res_outside.json()["detail"]

# 3. Successful Live API Response with Mock
@patch("httpx.AsyncClient.get")
def test_successful_live_weather_response(mock_get):
    mock_resp = httpx.Response(200, json=MOCK_OPEN_METEO_RESPONSE, request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast"))
    mock_get.return_value = mock_resp

    response = client.get("/api/v1/weather/live?lat=19.07&lon=72.87&refresh=true")
    assert response.status_code == 200
    data = response.json()

    # Verify standardized response format
    assert data["status"] == "LIVE"
    assert "source" in data
    assert "timestamp" in data
    assert "location" in data
    assert "weather" in data
    assert "freshness_seconds" in data

    # Verify location fields
    loc = data["location"]
    assert loc["latitude"] == 19.07
    assert loc["longitude"] == 72.87
    assert loc["in_india_region"] is True
    assert loc["name"] is not None

    # Verify weather fields
    w = data["weather"]
    assert w["temperature_c"] == 31.2
    assert w["relative_humidity_pct"] == 78.0
    assert w["surface_pressure_hpa"] == 1008.4
    assert w["sea_level_pressure_hpa"] == 1010.2
    assert w["wind_speed_kts"] == 16.5
    assert w["wind_direction_deg"] == 240.0
    assert w["wind_gust_kts"] == 24.2
    assert w["precipitation_mm"] == 0.2
    assert w["rain_mm"] == 0.2
    assert w["cloud_cover_pct"] == 45.0
    assert w["weather_code"] == 2
    assert w["weather_condition"] == "Partly cloudy"

    # Verify backward compatibility fields
    assert data["surface_wind_10m_kts"] == 16.5
    assert data["sea_level_pressure_hpa"] == 1010.2

# 4. Timeout Handling
@patch("httpx.AsyncClient.get")
def test_provider_timeout_handling(mock_get):
    mock_get.side_effect = httpx.TimeoutException("Connection timed out")

    response = client.get("/api/v1/weather/live?lat=20.0&lon=73.0&refresh=true")
    assert response.status_code == 200
    data = response.json()

    # When provider times out and no cache exists, return resilient fallback with explicit FALLBACK or OFFLINE status
    assert data["status"] in ["FALLBACK", "OFFLINE"]
    assert data["status"] != "LIVE"
    assert "location" in data
    assert "weather" in data

# 5. Provider Failure (HTTP 500 / Network Error)
@patch("httpx.AsyncClient.get")
def test_provider_failure_handling(mock_get):
    mock_resp = httpx.Response(500, request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast"))
    mock_get.return_value = mock_resp

    response = client.get("/api/v1/weather/live?lat=22.0&lon=69.0&refresh=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["FALLBACK", "OFFLINE"]
    assert data["status"] != "LIVE"

# 6. Malformed Provider Response Handling
@patch("httpx.AsyncClient.get")
def test_malformed_provider_response(mock_get):
    # Missing required current key or invalid data structure
    mock_resp = httpx.Response(200, json={"error": True, "reason": "Malformed"}, request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast"))
    mock_get.return_value = mock_resp

    response = client.get("/api/v1/weather/live?lat=15.0&lon=74.0&refresh=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["FALLBACK", "OFFLINE"]
    assert data["status"] != "LIVE"

# 7. Stale Data Handling & Freshness Calculation
@patch("httpx.AsyncClient.get")
def test_stale_data_lifecycle(mock_get):
    mock_get.side_effect = httpx.ConnectError("Simulated network timeout")
    key = weather_service._coord_key(19.07, 72.87)
    # Inject a cached record timestamped 400 seconds ago (exceeding the 300s freshness threshold)
    now_ts = time.time()
    weather_service._coord_cache[key] = {
        "cached_at_ts": now_ts - 400.0,
        "data": {
            "status": "LIVE",
            "data_status": "LIVE",
            "timestamp": "2026-09-17T14:40:00Z",
            "source": "Open-Meteo NWP",
            "location": {"latitude": 19.07, "longitude": 72.87, "name": "Mumbai Harbour"},
            "weather": {"temperature_c": 30.5, "wind_speed_kts": 14.0}
        }
    }

    # Query without forced refresh
    res = client.get("/api/v1/weather/live?lat=19.07&lon=72.87")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "STALE"
    assert data["freshness_seconds"] is not None
    assert data["freshness_seconds"] >= 400.0

# 8. Multiple Location Support (Station Resolution)
def test_multiple_location_spatial_resolution():
    pts = [
        (23.24, 68.62, "Jakhau Port"),
        (13.08, 80.27, "Chennai Port"),
        (20.31, 86.61, "Paradip Major Port"),
        (11.62, 92.72, "Port Blair"),
    ]
    for lat, lon, expected_name in pts:
        nearest = find_nearest_station(lat, lon)
        assert nearest["name"] == expected_name
        assert nearest["distance_km"] < 1.0 # Exact match

# 9. Pipeline Integrity & Feature Limitation Notice
def test_pipeline_integration_notice():
    res = client.get("/api/v1/weather/live")
    assert res.status_code == 200
    data = res.json()
    assert "pipeline_status" in data
    assert "Live weather ingestion available" in data["pipeline_status"]

