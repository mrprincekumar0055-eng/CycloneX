import sys
import os

# Ensure project root and backend directory are in sys.path for seamless deployment imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_current_dir)
_project_root = os.path.dirname(_backend_dir)
for _p in [_project_root, _backend_dir]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import time
import logging

from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal, init_db
from backend.app.api.v1.api import api_router
from backend.app.core.weather_cache import weather_cache
from data.adapters.open_meteo import open_meteo_adapter

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CycloneX")

# Create database tables and ensure columns exist
init_db()

def get_active_storm_coords() -> tuple[float, float]:
    """Retrieve active storm coordinates from database, or fallback to Biparjoy reference point."""
    try:
        db = SessionLocal()
        try:
            from backend.app.models.entities import Cyclone
            storm = db.query(Cyclone).filter(Cyclone.status == "active").first()
            if storm and storm.current_lat is not None and storm.current_lon is not None:
                return float(storm.current_lat), float(storm.current_lon)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not retrieve active storm coordinates from DB ({e}); defaulting to 21.65, 66.85.")
    return 21.65, 66.85

from backend.app.core.india_grid import INDIA_GRID_POINTS

async def poll_open_meteo_loop():
    """
    Background worker that polls Open-Meteo every 15 minutes (900 seconds)
    for all 44 India synoptic grid stations in a single batched query,
    computing disturbance scores and populating the in-memory LiveWeatherCache.
    """
    logger.info(f"[Open-Meteo Poller] Background grid polling initialized for {len(INDIA_GRID_POINTS)} stations.")
    while True:
        try:
            logger.info(f"[Open-Meteo Poller] Ingesting batched synoptic observations for {len(INDIA_GRID_POINTS)} stations...")
            envelope = await open_meteo_adapter.fetch_grid(INDIA_GRID_POINTS)
            weather_cache.update_grid(envelope)
            top = envelope.get("data", {}).get("most_disturbed", {})
            logger.info(
                f"[Open-Meteo Poller] Ingest successful (Status: {envelope.get('data_status', 'LIVE')}). "
                f"Most Disturbed: {top.get('name')} in {top.get('state')} (MDI Score: {top.get('disturbance_score')})"
            )
        except asyncio.CancelledError:
            logger.info("[Open-Meteo Poller] Task cancelled cleanly during shutdown.")
            break
        except Exception as exc:
            logger.error(f"[Open-Meteo Poller] Iteration error: {exc}. Will retry next cycle.", exc_info=True)

        try:
            await asyncio.sleep(900)
        except asyncio.CancelledError:
            logger.info("[Open-Meteo Poller] Sleep interrupted for shutdown.")
            break

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background poller task and alert monitor
    logger.info("[Lifespan] Starting Open-Meteo live weather background poller...")
    polling_task = asyncio.create_task(poll_open_meteo_loop())

    logger.info("[Lifespan] Starting CycloneX automatic alert monitor...")
    from alerts.monitor import alert_monitor_loop
    monitor_task = asyncio.create_task(alert_monitor_loop())

    yield

    # Shutdown: Cleanly cancel background tasks
    logger.info("[Lifespan] Shutting down background tasks...")
    polling_task.cancel()
    monitor_task.cancel()
    try:
        await asyncio.gather(polling_task, monitor_task, return_exceptions=True)
    except Exception:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade AI/ML-Powered Tropical Cyclone Intelligence & Early Warning Platform (SIH26070).",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request processing time header
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Seconds"] = str(round(process_time, 4))
    return response

# Root endpoint
@app.get("/")
def root():
    return {
        "platform": settings.PROJECT_NAME,
        "tagline": "AI-Powered Cyclone Intelligence & Early Warning",
        "version": settings.VERSION,
        "api_docs": "/docs",
        "health_check": f"{settings.API_V1_STR}/system/health"
    }

# Register API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
