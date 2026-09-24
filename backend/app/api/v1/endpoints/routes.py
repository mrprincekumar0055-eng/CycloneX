from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.entities import Route, Shelter, Cyclone
from backend.app.schemas.entities import RouteOut
from geospatial.routing import EvacuationRoutingEngine
from data.adapters.osm_overpass import OSMOverpassAdapter

router = APIRouter()

@router.get("", response_model=List[RouteOut])
def get_evacuation_routes(db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    return routes

@router.get("/nearest-shelters")
def find_nearest_shelters(
    lat: float = Query(23.2380, description="User or origin latitude"),
    lon: float = Query(68.6180, description="User or origin longitude"),
    top_k: int = 4
):
    all_shelters = [f for f in OSMOverpassAdapter.get_facilities() if f["facility_type"] == "shelter"]
    nearest = EvacuationRoutingEngine.find_nearest_facilities(
        origin_lat=lat,
        origin_lon=lon,
        facilities=all_shelters,
        top_k=top_k
    )
    return {
        "origin": {"lat": lat, "lon": lon},
        "nearest_shelters": nearest
    }

@router.post("/generate-evacuation-route")
def generate_route(
    origin_name: str = Query("Jakhau Coastal Settlement"),
    origin_lat: float = Query(23.2380),
    origin_lon: float = Query(68.6180),
    shelter_id: str = Query("sh-guj-01")
):
    all_shelters = [f for f in OSMOverpassAdapter.get_facilities() if f["facility_type"] == "shelter"]
    shelter = next((s for s in all_shelters if s["id"] == shelter_id), None)
    if not shelter:
        shelter = all_shelters[0] if all_shelters else {
            "id": "sh-default", "name": "Regional Cyclone Shelter", "lat": origin_lat + 0.1, "lon": origin_lon + 0.1
        }

    route_res = EvacuationRoutingEngine.generate_evacuation_route(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        origin_name=origin_name,
        shelter=shelter,
        cyclone_center_lat=21.65,
        cyclone_center_lon=66.85
    )
    return route_res

