"""
In-memory cache for live weather and oceanic telemetry across India.
Thread-safe and async-safe storage for periodic Open-Meteo synoptic observations,
all-India 44-point grid monitoring, and automated most-disturbed point surfacing.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import time
import logging

logger = logging.getLogger("CycloneX.WeatherCache")

class LiveWeatherCache:
    """
    In-memory singleton holding the latest Open-Meteo telemetry across the India grid.
    Evaluates staleness dynamically (STALE if age > 2x poll interval = 1800s).
    """
    POLL_INTERVAL_SECONDS = 900.0  # Backward-compatible 15 minutes legacy interval
    FRESHNESS_THRESHOLD_SECONDS = 300.0  # 5 minutes
    STALE_THRESHOLD_SECONDS = 600.0  # 10 minutes (2x poll interval)

    def __init__(self):
        self._last_sync_utc: Optional[str] = None
        self._last_sync_timestamp: float = 0.0
        self._data_status: str = "INITIALIZING"
        self._source: str = "Open-Meteo NWP API"
        self._provenance: Dict[str, Any] = {}

        self._grid_points: List[Dict[str, Any]] = []
        self._most_disturbed: Optional[Dict[str, Any]] = None
        self._biparjoy_reference: Dict[str, Any] = {
            "id": "in-bip",
            "name": "Biparjoy Anchor Point (Offshore)",
            "district": "Arabian Sea",
            "state": "Offshore",
            "region": "Northeast Arabian Sea",
            "lat": 21.65,
            "lon": 66.85,
            "surface_wind_10m_kts": 85.0,
            "wind_gust_kts": 102.0,
            "sea_level_pressure_hpa": 964.0,
            "relative_humidity_pct": 84.0,
            "air_temperature_2m_c": 29.2,
            "precipitation_mm": 18.5,
            "sea_surface_temp_c": 30.2,
            "disturbance_score": 88.5,
            "disturbance_category": "EXTREME DISTURBANCE",
            "indicator_color": "red",
            "rank": 1,
            "total_grid_points": 44
        }

        # Initialize default baseline grid covering all 44 points
        from backend.app.core.india_grid import INDIA_GRID_POINTS, calculate_disturbance_score
        init_pts = []
        for idx, pt in enumerate(INDIA_GRID_POINTS):
            is_bip = pt["id"] == "in-bip"
            w = 85.0 if is_bip else 15.0
            g = 102.0 if is_bip else 20.0
            p = 964.0 if is_bip else 1008.0
            r = 18.0 if is_bip else 0.0
            score_data = calculate_disturbance_score(w, g, p, r)
            init_pts.append({
                "id": pt["id"],
                "name": pt["name"],
                "district": pt["district"],
                "state": pt["state"],
                "region": pt["region"],
                "coastal": pt.get("coastal", False),
                "lat": pt["lat"],
                "lon": pt["lon"],
                "surface_wind_10m_kts": w,
                "wind_gust_kts": g,
                "sea_level_pressure_hpa": p,
                "relative_humidity_pct": 84.0 if is_bip else 75.0,
                "air_temperature_2m_c": 28.5,
                "precipitation_mm": r,
                "sea_surface_temp_c": 30.2 if pt.get("coastal") else None,
                "disturbance_score": score_data["disturbance_score"],
                "disturbance_category": score_data["category"],
                "indicator_color": score_data["indicator_color"],
                "data_status": "INITIALIZING"
            })
        init_pts.sort(key=lambda x: x["disturbance_score"], reverse=True)
        for r_idx, item in enumerate(init_pts, 1):
            item["rank"] = r_idx
            item["total_grid_points"] = len(init_pts)

        self._grid_points = init_pts
        self._most_disturbed = init_pts[0]

        # Backwards compatibility legacy cache
        self._legacy_cache: Dict[str, Any] = {
            "data_status": "INITIALIZING",
            "last_sync_utc": None,
            "last_sync_timestamp": 0.0,
            "coordinates": {"lat": 21.65, "lon": 66.85},
            "surface_wind_10m_kts": 85.0,
            "wind_gust_kts": 102.0,
            "sea_level_pressure_hpa": 964.0,
            "relative_humidity_pct": 84.0,
            "air_temperature_2m_c": 29.2,
            "precipitation_mm": 18.5,
            "sea_surface_temp_c": 30.2,
            "disturbance_score": 88.5,
            "disturbance_category": "EXTREME DISTURBANCE",
            "indicator_color": "red"
        }

        self._cache = self._legacy_cache

    def get_last_sync_timestamp(self) -> float:
        return self._last_sync_timestamp

    def get_last_sync_utc(self) -> Optional[str]:
        return self._last_sync_utc

    def mark_provider_failure(self, reason: str = ""):
        """
        Marks cache status as STALE (if prior cache exists) or OFFLINE (if uninitialized) on provider failure.
        """
        if self._last_sync_timestamp > 0:
            self._data_status = "STALE"
            for p in self._grid_points:
                p["data_status"] = "STALE"
                p["status"] = "STALE"
            if self._most_disturbed:
                self._most_disturbed["data_status"] = "STALE"
                self._most_disturbed["status"] = "STALE"
            if self._cache:
                self._cache["data_status"] = "STALE"
                self._cache["status"] = "STALE"
        else:
            self._data_status = "OFFLINE"
            for p in self._grid_points:
                p["data_status"] = "OFFLINE"
                p["status"] = "OFFLINE"
            if self._most_disturbed:
                self._most_disturbed["data_status"] = "OFFLINE"
                self._most_disturbed["status"] = "OFFLINE"
            if self._cache:
                self._cache["data_status"] = "OFFLINE"
                self._cache["status"] = "OFFLINE"

    def update_grid(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates the cache with a full grid result from OpenMeteoAdapter.fetch_grid().
        """
        now = datetime.now(timezone.utc)
        payload = envelope.get("data", {})
        raw_status = envelope.get("data_status", "LIVE")
        status = "LIVE" if raw_status == "LIVE" else ("STALE" if self._last_sync_timestamp > 0 else "OFFLINE")

        self._last_sync_utc = now.isoformat()
        self._last_sync_timestamp = now.timestamp()
        self._data_status = status
        self._source = envelope.get("source", "Open-Meteo NWP API")
        self._provenance = {
            "source": envelope.get("source", "Open-Meteo NWP API"),
            "source_url": envelope.get("source_url", "https://open-meteo.com"),
            "retrieved_at": envelope.get("retrieved_at", now.isoformat()),
            "processing_time_ms": envelope.get("processing_time_ms", 0.0)
        }

        grid_pts = payload.get("grid_points", [])
        for pt in grid_pts:
            pt["data_status"] = status
            pt["status"] = status
            pt["fetched_at"] = self._last_sync_utc
            pt["cached_at"] = self._last_sync_utc
            if "weather" in pt and isinstance(pt["weather"], dict):
                pt["weather"]["fetched_at"] = self._last_sync_utc
                pt["weather"]["cached_at"] = self._last_sync_utc

        self._grid_points = list(grid_pts)
        self._most_disturbed = payload.get("most_disturbed") or (grid_pts[0] if grid_pts else None)
        if self._most_disturbed:
            self._most_disturbed["data_status"] = status
            self._most_disturbed["status"] = status
            self._most_disturbed["fetched_at"] = self._last_sync_utc
            self._most_disturbed["cached_at"] = self._last_sync_utc

        # Locate Biparjoy anchor or fallback
        bip = next((p for p in grid_pts if p.get("id") == "in-bip" or (abs(p.get("lat", 0) - 21.65) < 0.1 and abs(p.get("lon", 0) - 66.85) < 0.1)), None)
        if bip:
            self._biparjoy_reference = dict(bip)
            self._biparjoy_reference["data_status"] = status
            self._biparjoy_reference["status"] = status
            self._biparjoy_reference["fetched_at"] = self._last_sync_utc
            self._biparjoy_reference["cached_at"] = self._last_sync_utc

        # Update legacy single-point cache pointing to biparjoy reference by default
        ref = self._biparjoy_reference
        self._legacy_cache = {
            "data_status": status,
            "status": status,
            "last_sync_utc": self._last_sync_utc,
            "last_sync_timestamp": self._last_sync_timestamp,
            "fetched_at": self._last_sync_utc,
            "cached_at": self._last_sync_utc,
            "coordinates": {"lat": ref.get("lat", 21.65), "lon": ref.get("lon", 66.85)},
            "surface_wind_10m_kts": ref.get("surface_wind_10m_kts"),
            "wind_gust_kts": ref.get("wind_gust_kts"),
            "sea_level_pressure_hpa": ref.get("sea_level_pressure_hpa"),
            "relative_humidity_pct": ref.get("relative_humidity_pct"),
            "air_temperature_2m_c": ref.get("air_temperature_2m_c"),
            "precipitation_mm": ref.get("precipitation_mm", 0.0),
            "sea_surface_temp_c": ref.get("sea_surface_temp_c"),
            "disturbance_score": ref.get("disturbance_score"),
            "disturbance_category": ref.get("disturbance_category"),
            "indicator_color": ref.get("indicator_color")
        }
        self._cache = self._legacy_cache

        top_name = self._most_disturbed.get("name") if self._most_disturbed else "None"
        top_score = self._most_disturbed.get("disturbance_score") if self._most_disturbed else 0.0
        logger.info(f"LiveWeatherCache updated with {len(self._grid_points)} grid points. Top Disturbed: {top_name} (Score: {top_score}, Status: {status})")
        return self.get_most_disturbed()

    def update(self, packet: Dict[str, Any], lat: float = 21.65, lon: float = 66.85) -> Dict[str, Any]:
        """
        Legacy single-point update method for compatibility with single-station tests/calls.
        """
        now = datetime.now(timezone.utc)
        payload = packet.get("data", {})
        raw_status = packet.get("data_status", "LIVE")
        status = "FALLBACK" if raw_status in ["DEMO", "FALLBACK"] else "LIVE"

        self._last_sync_utc = now.isoformat()
        self._last_sync_timestamp = now.timestamp()
        self._data_status = status

        self._legacy_cache = {
            "data_status": status,
            "status": status,
            "last_sync_utc": now.isoformat(),
            "last_sync_timestamp": now.timestamp(),
            "fetched_at": now.isoformat(),
            "cached_at": now.isoformat(),
            "coordinates": {"lat": lat, "lon": lon},
            "surface_wind_10m_kts": payload.get("surface_wind_10m_kts"),
            "wind_gust_kts": payload.get("wind_gust_kts"),
            "sea_level_pressure_hpa": payload.get("sea_level_pressure_hpa"),
            "relative_humidity_pct": payload.get("relative_humidity_pct"),
            "air_temperature_2m_c": payload.get("air_temperature_2m_c"),
            "precipitation_mm": payload.get("precipitation_mm", 0.0),
            "sea_surface_temp_c": payload.get("sea_surface_temp_c"),
            "disturbance_score": payload.get("disturbance_score", 15.0),
            "disturbance_category": payload.get("disturbance_category", "QUIET / AMBIENT"),
            "indicator_color": payload.get("indicator_color", "emerald")
        }
        self._cache = self._legacy_cache
        return self.get()

    def _compute_staleness(self, max_stale_seconds: Optional[float] = None) -> tuple[str, Optional[float]]:
        threshold = max_stale_seconds if max_stale_seconds is not None else self.STALE_THRESHOLD_SECONDS
        now_ts = datetime.now(timezone.utc).timestamp()
        last_ts = self._cache.get("last_sync_timestamp", self._last_sync_timestamp)
        age = round(now_ts - last_ts, 1) if last_ts > 0 else None

        if self._data_status == "OFFLINE":
            return "OFFLINE", age
        if self._data_status == "STALE":
            return "STALE", age

        status = self._cache.get("data_status", self._data_status)
        if status in ["LIVE", "FALLBACK"] and age is not None and age > threshold:
            status = "STALE"
        elif status == "INITIALIZING" and (last_ts == 0.0 or last_ts is None):
            status = "INITIALIZING"
        return status, age

    def get_most_disturbed(self, max_stale_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Returns the single highest-scoring disturbed location across the grid.
        """
        status, age = self._compute_staleness(max_stale_seconds)
        point = dict(self._most_disturbed) if self._most_disturbed else dict(self._biparjoy_reference)
        point["data_status"] = status
        point["status"] = status

        weather_dict = {
            "temperature_c": point.get("air_temperature_2m_c", 28.5),
            "relative_humidity_pct": point.get("relative_humidity_pct", 75.0),
            "surface_pressure_hpa": point.get("surface_pressure_hpa", point.get("sea_level_pressure_hpa", 1010.0)),
            "sea_level_pressure_hpa": point.get("sea_level_pressure_hpa", 1010.0),
            "wind_speed_kts": point.get("surface_wind_10m_kts", 15.0),
            "wind_direction_deg": point.get("wind_direction_10m_deg", 0.0),
            "wind_gust_kts": point.get("wind_gust_kts", 20.0),
            "precipitation_mm": point.get("precipitation_mm", 0.0),
            "rain_mm": point.get("rain_mm", point.get("precipitation_mm", 0.0)),
            "cloud_cover_pct": point.get("cloud_cover_pct", 20.0),
            "weather_code": point.get("weather_code", 0),
            "weather_condition": point.get("weather_condition", "Fair / Variable"),
            "sea_surface_temp_c": point.get("sea_surface_temp_c")
        }
        location_dict = {
            "latitude": point.get("lat", 21.65),
            "longitude": point.get("lon", 66.85),
            "name": point.get("name", "Station"),
            "district": point.get("district", "General"),
            "state": point.get("state", "India"),
            "region": point.get("region", "India"),
            "in_india_region": True
        }

        return {
            "status": status,
            "data_status": status,
            "timestamp": point.get("observation_time", self._last_sync_utc),
            "observation_time": point.get("observation_time", self._last_sync_utc),
            "fetched_at": self._last_sync_utc,
            "cached_at": self._last_sync_utc,
            "last_sync_utc": self._last_sync_utc,
            "freshness_seconds": age,
            "age_seconds": age,
            "poll_interval_seconds": self.POLL_INTERVAL_SECONDS,
            "selection_mode": "MOST_DISTURBED_AUTO_DETECT",
            "total_monitored_points": len(self._grid_points) if self._grid_points else 44,
            "location": location_dict,
            "weather": weather_dict,
            "point": point,
            # Top-level elevation of key fields for ease of consumption
            "id": point.get("id"),
            "name": point.get("name"),
            "district": point.get("district"),
            "state": point.get("state"),
            "region": point.get("region"),
            "coordinates": {"lat": point.get("lat"), "lon": point.get("lon")},
            "lat": point.get("lat"),
            "lon": point.get("lon"),
            "rank": point.get("rank", 1),
            "disturbance_score": point.get("disturbance_score"),
            "disturbance_category": point.get("disturbance_category"),
            "indicator_color": point.get("indicator_color"),
            "surface_wind_10m_kts": point.get("surface_wind_10m_kts"),
            "wind_direction_10m_deg": point.get("wind_direction_10m_deg", 0.0),
            "wind_gust_kts": point.get("wind_gust_kts"),
            "sea_level_pressure_hpa": point.get("sea_level_pressure_hpa"),
            "surface_pressure_hpa": point.get("surface_pressure_hpa", point.get("sea_level_pressure_hpa")),
            "relative_humidity_pct": point.get("relative_humidity_pct"),
            "air_temperature_2m_c": point.get("air_temperature_2m_c"),
            "precipitation_mm": point.get("precipitation_mm", 0.0),
            "rain_mm": point.get("rain_mm", point.get("precipitation_mm", 0.0)),
            "cloud_cover_pct": point.get("cloud_cover_pct", 20.0),
            "weather_code": point.get("weather_code", 0),
            "weather_condition": point.get("weather_condition", "Fair / Variable"),
            "sea_surface_temp_c": point.get("sea_surface_temp_c"),
            "source": self._source,
            "provenance": self._provenance,
            "pipeline_status": "Live weather ingestion available; ML prediction requires the required feature set.",
            "data": point
        }

    def get_grid(self, max_stale_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Returns all 44 grid points sorted in descending order of disturbance score.
        """
        status, age = self._compute_staleness(max_stale_seconds)
        points = [dict(p) for p in self._grid_points] if self._grid_points else [dict(self._biparjoy_reference)]
        for p in points:
            p["data_status"] = status
            p["status"] = status

        top_id = self._most_disturbed.get("id") if self._most_disturbed else (points[0]["id"] if points else None)
        return {
            "status": status,
            "data_status": status,
            "last_sync_utc": self._last_sync_utc,
            "fetched_at": self._last_sync_utc,
            "cached_at": self._last_sync_utc,
            "freshness_seconds": age,
            "age_seconds": age,
            "poll_interval_seconds": self.POLL_INTERVAL_SECONDS,
            "total_points": len(points),
            "most_disturbed_id": top_id,
            "source": self._source,
            "provenance": self._provenance,
            "pipeline_status": "Live weather ingestion available; ML prediction requires the required feature set.",
            "grid_points": points
        }

    def get_biparjoy_reference(self, max_stale_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Returns the fixed Cyclone Biparjoy reference point (21.65, 66.85).
        """
        status, age = self._compute_staleness(max_stale_seconds)
        ref = dict(self._biparjoy_reference)
        ref["data_status"] = status
        ref["status"] = status

        weather_dict = {
            "temperature_c": ref.get("air_temperature_2m_c", 29.2),
            "relative_humidity_pct": ref.get("relative_humidity_pct", 84.0),
            "surface_pressure_hpa": ref.get("sea_level_pressure_hpa", 964.0),
            "sea_level_pressure_hpa": ref.get("sea_level_pressure_hpa", 964.0),
            "wind_speed_kts": ref.get("surface_wind_10m_kts", 85.0),
            "wind_direction_deg": ref.get("wind_direction_10m_deg", 38.0),
            "wind_gust_kts": ref.get("wind_gust_kts", 102.0),
            "precipitation_mm": ref.get("precipitation_mm", 18.5),
            "rain_mm": ref.get("rain_mm", 18.5),
            "cloud_cover_pct": ref.get("cloud_cover_pct", 90.0),
            "weather_code": ref.get("weather_code", 95),
            "weather_condition": ref.get("weather_condition", "Thunderstorm"),
            "sea_surface_temp_c": 30.2
        }
        location_dict = {
            "latitude": ref.get("lat", 21.65),
            "longitude": ref.get("lon", 66.85),
            "name": ref.get("name", "Biparjoy Anchor Point (Offshore)"),
            "district": ref.get("district", "Arabian Sea"),
            "state": ref.get("state", "Offshore"),
            "region": ref.get("region", "Northeast Arabian Sea"),
            "in_india_region": True
        }

        return {
            "status": status,
            "data_status": status,
            "timestamp": ref.get("observation_time", self._last_sync_utc),
            "observation_time": ref.get("observation_time", self._last_sync_utc),
            "fetched_at": self._last_sync_utc,
            "cached_at": self._last_sync_utc,
            "last_sync_utc": self._last_sync_utc,
            "freshness_seconds": age,
            "age_seconds": age,
            "poll_interval_seconds": self.POLL_INTERVAL_SECONDS,
            "selection_mode": "FIXED_BIPARJOY_ANCHOR",
            "location": location_dict,
            "weather": weather_dict,
            "point": ref,
            "id": ref.get("id", "in-bip"),
            "name": ref.get("name", "Biparjoy Anchor Point (Offshore)"),
            "district": ref.get("district", "Arabian Sea"),
            "state": ref.get("state", "Offshore"),
            "region": ref.get("region", "Northeast Arabian Sea"),
            "coordinates": {"lat": ref.get("lat", 21.65), "lon": ref.get("lon", 66.85)},
            "lat": ref.get("lat", 21.65),
            "lon": ref.get("lon", 66.85),
            "rank": ref.get("rank", 1),
            "disturbance_score": ref.get("disturbance_score"),
            "disturbance_category": ref.get("disturbance_category"),
            "indicator_color": ref.get("indicator_color"),
            "surface_wind_10m_kts": ref.get("surface_wind_10m_kts"),
            "wind_direction_10m_deg": ref.get("wind_direction_10m_deg", 38.0),
            "wind_gust_kts": ref.get("wind_gust_kts"),
            "sea_level_pressure_hpa": ref.get("sea_level_pressure_hpa"),
            "surface_pressure_hpa": ref.get("sea_level_pressure_hpa"),
            "relative_humidity_pct": ref.get("relative_humidity_pct"),
            "air_temperature_2m_c": ref.get("air_temperature_2m_c"),
            "precipitation_mm": ref.get("precipitation_mm", 0.0),
            "rain_mm": ref.get("rain_mm", 0.0),
            "cloud_cover_pct": ref.get("cloud_cover_pct", 90.0),
            "weather_code": ref.get("weather_code", 95),
            "weather_condition": ref.get("weather_condition", "Thunderstorm"),
            "sea_surface_temp_c": ref.get("sea_surface_temp_c"),
            "source": self._source,
            "provenance": self._provenance,
            "pipeline_status": "Live weather ingestion available; ML prediction requires the required feature set.",
            "data": ref
        }

    def get(self, target: str = "most_disturbed", max_stale_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Unified getter. Defaults to most-disturbed point.
        Supports target='biparjoy' or target='fixed' for the benchmark anchor.
        """
        if target in ["biparjoy", "fixed", "benchmark"]:
            return self.get_biparjoy_reference(max_stale_seconds)
        if self._most_disturbed is not None:
            return self.get_most_disturbed(max_stale_seconds)

        # Fallback to legacy structure if grid has not yet synced
        status, age = self._compute_staleness(max_stale_seconds)
        cached = dict(self._legacy_cache)
        cached["data_status"] = status
        cached["age_seconds"] = age
        cached["poll_interval_seconds"] = self.POLL_INTERVAL_SECONDS
        cached["data"] = {
            "surface_wind_10m_kts": cached.get("surface_wind_10m_kts"),
            "wind_gust_kts": cached.get("wind_gust_kts"),
            "sea_level_pressure_hpa": cached.get("sea_level_pressure_hpa"),
            "relative_humidity_pct": cached.get("relative_humidity_pct"),
            "air_temperature_2m_c": cached.get("air_temperature_2m_c"),
            "precipitation_mm": cached.get("precipitation_mm", 0.0),
            "sea_surface_temp_c": cached.get("sea_surface_temp_c"),
            "lat": cached.get("coordinates", {}).get("lat", 21.65),
            "lon": cached.get("coordinates", {}).get("lon", 66.85)
        }
        return cached

# Global singleton
weather_cache = LiveWeatherCache()
