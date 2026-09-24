from fastapi import APIRouter
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

