"""
Weather Service Layer for CycloneX
Orchestrates numerical weather prediction (NWP) ingestion, spatial coordinate validation,
staleness lifecycle management (LIVE -> STALE -> OFFLINE), and location intelligence.

Architecture:
API (endpoints/weather.py)
  ↓
Weather Service (services/weather_service.py)
  ↓
Weather Cache (core/weather_cache.py) / Weather Adapter (adapters/open_meteo.py)
  ↓
External Provider (Open-Meteo API)
"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import time
import logging

from data.adapters.open_meteo import open_meteo_adapter
from backend.app.core.weather_cache import weather_cache
from backend.app.core.india_grid import (
    INDIA_GRID_POINTS,
    is_valid_coordinate,
    is_in_india_region,
    find_nearest_station
)

logger = logging.getLogger("CycloneX.WeatherService")

class WeatherService:
    # 5 minutes refresh / freshness threshold
    FRESHNESS_THRESHOLD_SECONDS = 300.0  # 5 minutes
    STALE_THRESHOLD_SECONDS = 600.0      # 10 minutes

    def __init__(self):
        # In-memory cache for arbitrary coordinate observations
        self._coord_cache: Dict[str, Dict[str, Any]] = {}

    def _coord_key(self, lat: float, lon: float) -> str:
        return f"{round(float(lat), 4)}_{round(float(lon), 4)}"

    def validate_coordinates(self, lat: Any, lon: Any, strict_india: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validates latitude and longitude format and domain.
        Returns (is_valid, error_message).
        """
        if not is_valid_coordinate(lat, lon):
            return False, "Invalid geographic coordinates: latitude must be in [-90, 90] and longitude in [-180, 180]."
        if strict_india and not is_in_india_region(lat, lon):
            return False, "Coordinates outside India monitoring domain (Latitude: 6.0°N to 38.0°N, Longitude: 68.0°E to 98.0°E)."
        return True, None

    async def get_weather_for_coordinates(
        self,
        lat: float,
        lon: float,
        refresh: bool = False,
        timeout_seconds: float = 4.0
    ) -> Dict[str, Any]:
        """
        Retrieves live or cached weather observations for arbitrary coordinates across India.
        Evaluates staleness dynamically:
        - LIVE: provider successfully contacted and fresh
        - STALE: provider failed but cached data exists, or cached data has aged
        - OFFLINE: provider failed and no usable cached data exists
        """
        now = datetime.now(timezone.utc)
        now_ts = now.timestamp()
        now_iso = now.isoformat()
        key = self._coord_key(lat, lon)
        cached_entry = self._coord_cache.get(key)

        # 1. Return cached observation if still fresh and refresh not explicitly forced
        if not refresh and cached_entry is not None:
            age = round(now_ts - cached_entry["cached_at_ts"], 1)
            if age <= self.FRESHNESS_THRESHOLD_SECONDS:
                result = dict(cached_entry["data"])
                result["status"] = "LIVE"
                result["data_status"] = "LIVE"
                result["freshness_seconds"] = age
                result["age_seconds"] = age
                result["cached_at"] = cached_entry.get("cached_at")
                result["fetched_at"] = cached_entry["data"].get("fetched_at")
                return result

        # 2. Fetch fresh data from provider adapter (forced refresh or expired cache or miss)
        try:
            packet = await open_meteo_adapter.fetch(lat=lat, lon=lon, timeout_seconds=timeout_seconds)
            data_status = packet.get("data_status", "LIVE")

            # Store in cache on genuine LIVE success
            if data_status == "LIVE":
                packet["status"] = "LIVE"
                packet["data_status"] = "LIVE"
                packet["freshness_seconds"] = 0.0
                packet["age_seconds"] = 0.0
                packet["cached_at"] = now_iso
                packet["fetched_at"] = now_iso
                self._coord_cache[key] = {
                    "cached_at_ts": now_ts,
                    "cached_at": now_iso,
                    "data": dict(packet)
                }
                return packet
            elif cached_entry is not None:
                # Provider returned fallback/non-live, preserve last known real observation as STALE
                age = round(now_ts - cached_entry["cached_at_ts"], 1)
                stale_result = dict(cached_entry["data"])
                stale_result["status"] = "STALE"
                stale_result["data_status"] = "STALE"
                stale_result["freshness_seconds"] = age
                stale_result["age_seconds"] = age
                stale_result["cached_at"] = cached_entry.get("cached_at")
                return stale_result
            else:
                # Provider returned non-live and no cache exists -> OFFLINE
                nearest = find_nearest_station(lat, lon)
                return {
                    "status": "OFFLINE",
                    "data_status": "OFFLINE",
                    "source": "Open-Meteo NWP API",
                    "timestamp": None,
                    "observation_time": None,
                    "fetched_at": None,
                    "cached_at": None,
                    "freshness_seconds": None,
                    "age_seconds": None,
                    "coordinates": {"lat": lat, "lon": lon},
                    "lat": lat,
                    "lon": lon,
                    "name": nearest.get("name", "Offline Observation Sector"),
                    "surface_wind_10m_kts": None,
                    "sea_level_pressure_hpa": None,
                    "location": {
                        "latitude": lat,
                        "longitude": lon,
                        "name": nearest.get("name", "Offline Observation Sector"),
                        "district": nearest.get("district", "General"),
                        "state": nearest.get("state", "India"),
                        "in_india_region": is_in_india_region(lat, lon),
                        "nearest_grid_station": nearest.get("name")
                    },
                    "weather": None,
                    "error": "Live weather service currently unreachable",
                    "pipeline_status": "Live weather ingestion available; ML prediction requires the required feature set."
                }
        except Exception as exc:
            logger.warning(f"Error fetching weather for ({lat}, {lon}): {exc}")
            if cached_entry is not None:
                age = round(now_ts - cached_entry["cached_at_ts"], 1)
                stale_result = dict(cached_entry["data"])
                stale_result["status"] = "STALE"
                stale_result["data_status"] = "STALE"
                stale_result["freshness_seconds"] = age
                stale_result["age_seconds"] = age
                stale_result["cached_at"] = cached_entry.get("cached_at")
                stale_result["error"] = f"Provider unreachable: {str(exc)}"
                return stale_result
            else:
                nearest = find_nearest_station(lat, lon)
                return {
                    "status": "OFFLINE",
                    "data_status": "OFFLINE",
                    "source": "Open-Meteo NWP API",
                    "timestamp": None,
                    "observation_time": None,
                    "fetched_at": None,
                    "cached_at": None,
                    "freshness_seconds": None,
                    "age_seconds": None,
                    "coordinates": {"lat": lat, "lon": lon},
                    "lat": lat,
                    "lon": lon,
                    "name": nearest.get("name", "Offline Observation Sector"),
                    "surface_wind_10m_kts": None,
                    "sea_level_pressure_hpa": None,
                    "location": {
                        "latitude": lat,
                        "longitude": lon,
                        "name": nearest.get("name", "Offline Observation Sector"),
                        "district": nearest.get("district", "General"),
                        "state": nearest.get("state", "India"),
                        "in_india_region": is_in_india_region(lat, lon),
                        "nearest_grid_station": nearest.get("name")
                    },
                    "weather": None,
                    "error": f"Live weather service currently unreachable: {str(exc)}",
                    "pipeline_status": "Live weather ingestion available; ML prediction requires the required feature set."
                }

    async def get_live_target(
        self,
        target: str = "most_disturbed",
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Returns live weather for the current monitored target (most_disturbed or biparjoy anchor).
        Automatically refreshes if refresh=True or if the cache is uninitialized/stale (> 300s).
        """
        now_ts = datetime.now(timezone.utc).timestamp()
        last_sync = weather_cache.get_last_sync_timestamp()
        cache_age = (now_ts - last_sync) if last_sync > 0 else 999999.0

        if refresh or (cache_age > self.FRESHNESS_THRESHOLD_SECONDS):
            try:
                envelope = await open_meteo_adapter.fetch_grid(INDIA_GRID_POINTS)
                if envelope.get("data_status") == "LIVE":
                    weather_cache.update_grid(envelope)
                else:
                    weather_cache.mark_provider_failure("Provider returned non-live status")
            except Exception as exc:
                logger.warning(f"Error refreshing live grid from Open-Meteo: {exc}")
                weather_cache.mark_provider_failure(str(exc))

        return weather_cache.get(target=target)

    async def get_grid_weather(self, refresh: bool = False) -> Dict[str, Any]:
        """
        Returns the All-India 44-station synoptic grid.
        Automatically refreshes if refresh=True or if the cache is uninitialized/stale (> 300s).
        """
        now_ts = datetime.now(timezone.utc).timestamp()
        last_sync = weather_cache.get_last_sync_timestamp()
        cache_age = (now_ts - last_sync) if last_sync > 0 else 999999.0

        if refresh or (cache_age > self.FRESHNESS_THRESHOLD_SECONDS):
            try:
                envelope = await open_meteo_adapter.fetch_grid(INDIA_GRID_POINTS)
                if envelope.get("data_status") == "LIVE":
                    weather_cache.update_grid(envelope)
                else:
                    weather_cache.mark_provider_failure("Provider returned non-live status")
            except Exception as exc:
                logger.warning(f"Error refreshing live grid from Open-Meteo: {exc}")
                weather_cache.mark_provider_failure(str(exc))

        return weather_cache.get_grid()

weather_service = WeatherService()

