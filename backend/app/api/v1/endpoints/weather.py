from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status, Response
import time
import logging
from datetime import datetime, timezone

from backend.app.services.weather_service import weather_service
from backend.app.core.india_grid import is_valid_coordinate, is_in_india_region

logger = logging.getLogger("CycloneX.WeatherAPI")

router = APIRouter()

@router.get("/most-disturbed")
async def get_most_disturbed_weather(
    refresh: bool = Query(False, description="Force on-demand refresh of the full India grid"),
    _ts: Optional[int] = Query(None, description="Cache-busting timestamp parameter")
):
    """
    Returns the single most weather-disturbed location across India
    auto-selected based on live wind, pressure deficit, and precipitation.
    """
    return await weather_service.get_live_target(target="most_disturbed", refresh=refresh)

@router.get("/grid")
async def get_all_grid_weather(
    refresh: bool = Query(False, description="Force on-demand refresh of the full India grid"),
    _ts: Optional[int] = Query(None, description="Cache-busting timestamp parameter")
):
    """
    Returns live meteorological observations and disturbance scores
    for all 44 grid points across India, sorted by disturbance severity.
    """
    return await weather_service.get_grid_weather(refresh=refresh)

@router.get("/live")
async def get_live_weather(
    response: Response,
    target: str = Query("most_disturbed", description="Selection target: 'most_disturbed' (default) or 'biparjoy'"),
    lat: Optional[float] = Query(None, description="Target latitude for coordinate-specific fetch"),
    lon: Optional[float] = Query(None, description="Target longitude for coordinate-specific fetch"),
    refresh: bool = Query(False, description="Force on-demand refresh from Open-Meteo API"),
    strict_india: bool = Query(False, description="Enforce strict bounding-box validation for Indian territory"),
    _ts: Optional[int] = Query(None, description="Cache-busting timestamp parameter")
):
    """
    Returns real-time meteorological observations for any location in India.
    Standardized payload includes live/stale/offline status, source, observation timestamp,
    detailed weather metrics, and spatial location metadata.
    """
    t_start = time.time()
    req_timestamp_iso = datetime.now(timezone.utc).isoformat()

    # Prevent browser / intermediary caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    # If one coordinate is provided without the other, raise 400
    if (lat is not None and lon is None) or (lat is None and lon is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'lat' and 'lon' query parameters must be provided together."
        )

    # Coordinate-specific query
    if lat is not None and lon is not None:
        if not is_valid_coordinate(lat, lon):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid geographic coordinates: latitude must be between -90 and 90, longitude between -180 and 180."
            )
        if strict_india and not is_in_india_region(lat, lon):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coordinates outside India monitoring domain (Latitude: 6.0°N to 38.0°N, Longitude: 68.0°E to 98.0°E)."
            )
        result = await weather_service.get_weather_for_coordinates(lat=lat, lon=lon, refresh=refresh)
    else:
        # Default to monitored target (most_disturbed or biparjoy reference)
        result = await weather_service.get_live_target(target=target, refresh=refresh)

    # Server-side structured diagnostic logging
    duration_ms = round((time.time() - t_start) * 1000, 1)
    status_label = result.get("status") or result.get("data_status") or "UNKNOWN"
    obs_time = result.get("timestamp") or result.get("observation_time")
    freshness = result.get("freshness_seconds")
    cache_hit = (freshness is not None and freshness > 0.1 and not refresh)
    provider_name = result.get("source") or "Open-Meteo NWP API"

    logger.info(
        f"[Weather Live Request] timestamp='{req_timestamp_iso}' "
        f"lat={lat} lon={lon} target='{target}' refresh={refresh} "
        f"provider='{provider_name}' cache={'HIT' if cache_hit else 'MISS'} "
        f"req_started='{req_timestamp_iso}' duration_ms={duration_ms} "
        f"obs_time='{obs_time}' http_status=200 state='{status_label}'"
    )

    return result

@router.get("/current")
async def get_current_weather(
    lat: float = Query(21.65, description="Latitude"),
    lon: float = Query(66.85, description="Longitude")
):
    """
    Direct endpoint querying Open-Meteo adapter for given coordinates.
    """
    if not is_valid_coordinate(lat, lon):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid geographic coordinates: latitude must be between -90 and 90, longitude between -180 and 180."
        )
    return await weather_service.get_weather_for_coordinates(lat=lat, lon=lon, refresh=True)
