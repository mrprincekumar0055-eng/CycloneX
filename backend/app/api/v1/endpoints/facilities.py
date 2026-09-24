from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.entities import Facility, Shelter, Hospital
from backend.app.schemas.entities import FacilityOut, ShelterOut, HospitalOut
from data.adapters.osm_overpass import OSMOverpassAdapter

router = APIRouter()

@router.get("", response_model=List[FacilityOut])
def list_facilities(
    facility_type: Optional[str] = None,
    verified_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Facility)
    if facility_type:
        query = query.filter(Facility.facility_type == facility_type)
    if verified_only:
        query = query.filter(Facility.is_officially_verified == True)
    
    results = query.all()
    if not results:
        # Fallback to adapter dataset directly
        adapter_facs = OSMOverpassAdapter.get_facilities(facility_type=facility_type, verified_only=verified_only)
        return adapter_facs
    return results

@router.get("/shelters", response_model=List[ShelterOut])
def list_shelters(db: Session = Depends(get_db)):
    shelters = db.query(Shelter).all()
    if not shelters:
        # Return fallback from adapter
        facs = [f for f in OSMOverpassAdapter.get_facilities() if f["facility_type"] == "shelter"]
        return [
            {
                "id": f["id"],
                "facility_id": f["id"],
                "name": f["name"],
                "lat": f["lat"],
                "lon": f["lon"],
                "total_capacity": f.get("total_capacity", 1500),
                "current_occupancy": f.get("current_occupancy", 0),
                "generator_available": f.get("generator_available", True),
                "drinking_water_available": f.get("drinking_water_available", True),
                "medical_kit_available": f.get("medical_kit_available", True),
                "elevation_meters": f.get("elevation_meters", 12.0),
                "is_verified": f.get("is_verified", True)
            }
            for f in facs
        ]
    return shelters

@router.get("/hospitals", response_model=List[HospitalOut])
def list_hospitals(db: Session = Depends(get_db)):
    hospitals = db.query(Hospital).all()
    if not hospitals:
        facs = [f for f in OSMOverpassAdapter.get_facilities() if f["facility_type"] == "hospital"]
        return [
            {
                "id": f["id"],
                "facility_id": f["id"],
                "name": f["name"],
                "lat": f["lat"],
                "lon": f["lon"],
                "total_beds": f.get("total_beds", 250),
                "available_icu_beds": f.get("available_icu_beds", 15),
                "emergency_trauma_unit": f.get("emergency_trauma_unit", True),
                "helipad": f.get("helipad", False)
            }
            for f in facs
        ]
    return hospitals

