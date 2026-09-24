import pytest
import time
import httpx
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.weather_service import weather_service
from backend.app.core.weather_cache import weather_cache

client = TestClient(app)

MOCK_MUMBAI_RESPONSE = {
    "latitude": 19.076,
    "longitude": 72.8777,
    "generationtime_ms": 0.45,
    "utc_offset_seconds": 0,
    "timezone": "GMT",
    "timezone_abbreviation": "GMT",
    "elevation": 14.0,
    "current": {
        "time": "2026-09-18T05:00:00Z",
        "interval": 900,
        "temperature_2m": 30.5,
        "relative_humidity_2m": 76.0,
        "surface_pressure": 1008.2,
        "pressure_msl": 1010.5,
        "wind_speed_10m": 14.8,
        "wind_direction_10m": 250.0,
        "wind_gusts_10m": 22.0,
        "precipitation": 0.0,
        "rain": 0.0,
        "cloud_cover": 40.0,
        "weather_code": 1
    }
}

MOCK_CHENNAI_RESPONSE = {
    "latitude": 13.0827,
    "longitude": 80.2707,
    "generationtime_ms": 0.5,
    "utc_offset_seconds": 0,
    "timezone": "GMT",
    "timezone_abbreviation": "GMT",
    "elevation": 7.0,
    "current": {
        "time": "2026-09-18T05:00:00Z",
        "interval": 900,
        "temperature_2m": 33.2,
        "relative_humidity_2m": 82.0,
        "surface_pressure": 1006.1,
        "pressure_msl": 1007.8,
        "wind_speed_10m": 18.2,
        "wind_direction_10m": 120.0,
        "wind_gusts_10m": 28.5,
        "precipitation": 1.2,
        "rain": 1.2,
        "cloud_cover": 75.0,
        "weather_code": 61
    }
}


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear in-memory coordinate and global caches before each test."""
    weather_service._coord_cache.clear()
    weather_cache._last_sync_timestamp = 0.0
    weather_cache._last_sync_utc = None
    weather_cache._data_status = "INITIALIZING"
    yield
    weather_service._coord_cache.clear()
    weather_cache._last_sync_timestamp = 0.0
    weather_cache._last_sync_utc = None
    weather_cache._data_status = "INITIALIZING"


# Test 1: Fresh provider response -> status is LIVE, values match provider
def test_fresh_provider_response_is_live():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_MUMBAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        response = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "LIVE"
        assert data["data_status"] == "LIVE"
        assert data["weather"]["temperature_c"] == 30.5
        assert data["weather"]["wind_speed_kts"] == 14.8
        assert data["weather"]["surface_pressure_hpa"] == 1008.2
        assert data["weather"]["sea_level_pressure_hpa"] == 1010.5
        assert data["observation_time"] == "2026-09-18T05:00:00Z"
        assert "fetched_at" in data
        assert "cached_at" in data


# Test 2: refresh=true forces provider query and bypasses cache
def test_refresh_true_forces_provider_query():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_MUMBAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        # First request populates cache
        resp1 = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp1.status_code == 200
        assert mock_get.call_count == 1

        # Second request with refresh=true must call provider again
        resp2 = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp2.status_code == 200
        assert mock_get.call_count == 2


# Test 3: refresh=false with fresh cache returns cached data without calling provider
def test_refresh_false_with_fresh_cache_avoids_provider_call():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_MUMBAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        # First call populates cache
        resp1 = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp1.status_code == 200
        assert mock_get.call_count == 1

        # Second call with refresh=false within 300s must use cache
        resp2 = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=false")
        assert resp2.status_code == 200
        assert mock_get.call_count == 1  # No additional provider call!
        assert resp2.json()["status"] == "LIVE"


# Test 4: refresh=false with expired cache (> 300s) attempts provider refresh
def test_refresh_false_with_expired_cache_attempts_refresh():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_MUMBAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        # Populate cache
        resp1 = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp1.status_code == 200
        assert mock_get.call_count == 1

        # Artificially age the cache entry beyond FRESHNESS_THRESHOLD (300s)
        key = weather_service._coord_key(19.0760, 72.8777)
        weather_service._coord_cache[key]["cached_at_ts"] -= 350.0

        # Call with refresh=false should detect age > 300s and call provider
        resp2 = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=false")
        assert resp2.status_code == 200
        assert mock_get.call_count == 2


# Test 5: Provider failure + cache exists -> returns STALE with previous data
def test_provider_failure_with_existing_cache_returns_stale():
    with patch("httpx.AsyncClient.get") as mock_get:
        # Step 1: Successful initial population
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_MUMBAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        resp1 = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "LIVE"

        # Step 2: Simulate provider failure on subsequent refresh
        mock_get.side_effect = httpx.ConnectError("Open-Meteo connection timeout")

        resp2 = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Must return STALE and preserve previous data
        assert data2["status"] == "STALE"
        assert data2["data_status"] == "STALE"
        assert data2["weather"]["temperature_c"] == 30.5
        assert "cached_at" in data2


# Test 6: Provider failure + no cache -> returns OFFLINE with descriptive error
def test_provider_failure_without_cache_returns_offline():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("DNS resolution failed")

        resp = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "OFFLINE"
        assert data["data_status"] == "OFFLINE"
        assert "Offline Observation Sector" in data.get("name", "") or data.get("location") is not None


# Test 7: Different coordinates do not share cache or return wrong weather
def test_different_coordinates_do_not_share_cache():
    with patch("httpx.AsyncClient.get") as mock_get:
        # First call for Mumbai
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_MUMBAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        resp_mumbai = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp_mumbai.status_code == 200
        assert resp_mumbai.json()["weather"]["temperature_c"] == 30.5

        # Second call for Chennai
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_CHENNAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        resp_chennai = client.get("/api/v1/weather/live?lat=13.0827&lon=80.2707&refresh=false")
        assert resp_chennai.status_code == 200
        data_chennai = resp_chennai.json()

        # Must have Chennai data, not Mumbai data
        assert data_chennai["weather"]["temperature_c"] == 33.2
        assert data_chennai["location"]["latitude"] == pytest.approx(13.0827, abs=0.01)
        assert data_chennai["location"]["longitude"] == pytest.approx(80.2707, abs=0.01)


# Test 8: Provider observation timestamp is preserved, not overwritten with fetch time
def test_observation_timestamp_preserved():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_MUMBAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        resp = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp.status_code == 200
        data = resp.json()

        assert data["observation_time"] == "2026-09-18T05:00:00Z"
        # fetched_at must be current time, separate from observation_time
        assert data["fetched_at"] != data["observation_time"]


# Test 9: Stale data cannot be labelled LIVE
def test_stale_data_cannot_be_labelled_live():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=MOCK_MUMBAI_RESPONSE,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )

        # Initialize cache
        resp = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp.status_code == 200

        # Artificially age the entry beyond STALE_THRESHOLD (600s)
        key = weather_service._coord_key(19.0760, 72.8777)
        weather_service._coord_cache[key]["cached_at_ts"] -= 700.0

        # Force provider failure so it falls back to stale cache
        mock_get.side_effect = httpx.ConnectError("Service unavailable")

        resp_stale = client.get("/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true")
        assert resp_stale.status_code == 200
        data_stale = resp_stale.json()

        assert data_stale["status"] != "LIVE"
        assert data_stale["status"] == "STALE"
