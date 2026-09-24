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
from datetime import datetime, timezone

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
    allow_origin_regex=r"https://.*\.vercel\.app",
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

# Production Health & Readiness Endpoints
@app.get("/health")
def health_check():
    """Liveness probe: verifies the API process is alive and responsive."""
    return {
        "status": "ok",
        "service": "cyclonex-api",
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health/ready")
async def health_ready():
    """Readiness probe: verifies database connectivity and background cache status."""
    import sqlalchemy
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(sqlalchemy.text("SELECT 1"))
        db.close()
    except Exception:
        db_ok = False

    cached_stations = len(weather_cache._grid_points) if hasattr(weather_cache, "_grid_points") else 0
    cache_ready = cached_stations > 0

    return {
        "status": "ready" if db_ok else "degraded",
        "service": "cyclonex-api",
        "database": "connected" if db_ok else "unreachable",
        "weather_cache_ready": cache_ready,
        "cached_stations": cached_stations,
        "live_alerts_enabled": settings.LIVE_ALERTS_ENABLED,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Root endpoint
@app.get("/")
def root():
    return {
        "platform": settings.PROJECT_NAME,
        "tagline": "AI-Powered Cyclone Intelligence & Early Warning",
        "version": settings.VERSION,
        "api_docs": "/docs",
        "health_check": "/health",
        "readiness_check": "/health/ready",
        "api_v1": settings.API_V1_STR
    }

# Register API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    is_dev = os.environ.get("ENVIRONMENT", "development").lower() == "development"
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=is_dev)
