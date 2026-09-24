from typing import List, Optional
from fastapi import APIRouter, Query
from data.adapters.ibtracs import IBTrACSAdapter

router = APIRouter()

@router.get("/analogs")
def get_historical_analogs(
    lat: float = Query(21.65, description="Current cyclone latitude"),
    lon: float = Query(66.85, description="Current cyclone longitude"),
    wind_speed_kts: float = Query(85.0, description="Current maximum sustained wind speed (kts)"),
    top_k: int = Query(3, description="Number of top analog matches")
):
    analogs = IBTrACSAdapter.find_analogous_cyclones(
        current_lat=lat,
        current_lon=lon,
        current_wind_kts=wind_speed_kts,
        top_k=top_k
    )
    return {
        "query": {"lat": lat, "lon": lon, "wind_speed_kts": wind_speed_kts},
        "analogs": analogs,
        "database": "NOAA IBTrACS v04r00",
        "disclaimer": "Historical similarity is an observational reference and must not be used as an operational guarantee of track or intensity."
    }

@router.get("/catalog")
def get_historical_catalog():
    return {
        "count": len(IBTrACSAdapter.HISTORICAL_CATALOG),
        "cyclones": IBTrACSAdapter.HISTORICAL_CATALOG
    }

