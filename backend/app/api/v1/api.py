from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.api.v1.endpoints import (
    cyclones, satellite, weather, facilities,
    routes, alerts, historical, system, auth
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(system.router, prefix="/system", tags=["System & Health"])
api_router.include_router(cyclones.router, prefix="/cyclones", tags=["Cyclones & ML Prediction"])
api_router.include_router(satellite.router, prefix="/satellite", tags=["Satellite Imagery (NASA GIBS)"])
api_router.include_router(weather.router, prefix="/weather", tags=["Weather & Ocean Observations"])
api_router.include_router(facilities.router, prefix="/facilities", tags=["Infrastructure & Facilities"])
api_router.include_router(routes.router, prefix="/routes", tags=["Evacuation & Routes"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Early Warning Alerts"])
api_router.include_router(historical.router, prefix="/historical", tags=["Historical Analogs (NOAA IBTrACS)"])

@api_router.get("/risk", tags=["Risk"])
def get_general_risk(cyclone_id: str = "demo-biparjoy-2023", db: Session = Depends(get_db)):
    """Convenience endpoint returning calculated risk profile and zones for the active cyclone."""
    return cyclones.get_cyclone_risk_zones(cyclone_id=cyclone_id, db=db)

@api_router.get("/evacuation", tags=["Evacuation"])
def get_general_evacuation(db: Session = Depends(get_db)):
    """Convenience endpoint returning consolidated evacuation logistics: shelters, hospitals, and corridors."""
    shelters = facilities.list_shelters(db=db)
    hospitals = facilities.list_hospitals(db=db)
    evac_routes = routes.get_evacuation_routes(db=db)
    return {
        "status": "OPERATIONAL",
        "shelters_count": len(shelters),
        "hospitals_count": len(hospitals),
        "routes_count": len(evac_routes),
        "shelters": shelters,
        "hospitals": hospitals,
        "routes": evac_routes
    }
