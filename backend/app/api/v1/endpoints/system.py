from datetime import datetime, timezone
import urllib.request
import time
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.entities import Cyclone, DataSource, Alert, Shelter, Hospital
from backend.app.schemas.entities import HealthStatus, ReadinessStatus

router = APIRouter()

@router.get("/health", response_model=HealthStatus)
def get_system_health(db: Session = Depends(get_db)):
    db_status = "connected"
    active_count = 0
    try:
        db.execute(text("SELECT 1"))
        active_count = db.query(Cyclone).filter(Cyclone.status == "active").count()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthStatus(
        status="ok" if db_status == "connected" else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        demo_mode=settings.DEMO_MODE,
        data_freshness_utc=datetime.now(timezone.utc).isoformat(),
        active_cyclones_count=active_count
    )

@router.get("/data-sources")
def get_data_sources(db: Session = Depends(get_db)):
    sources = db.query(DataSource).all()
    return [
        {
            "id": s.id,
            "source_name": s.source_name,
            "source_url": s.source_url,
            "status": s.status,
            "latency_ms": s.latency_ms,
            "last_sync": s.last_sync.isoformat() if s.last_sync else None,
            "records_count": s.records_count
        }
        for s in sources
    ]

@router.get("/readiness", response_model=ReadinessStatus)
def get_system_readiness(response: Response, db: Session = Depends(get_db)):
    """
    Comprehensive startup readiness check:
    1. Database connectivity
    2. Non-zero row counts in cyclones, alerts, shelters, hospitals
    3. Map tile provider connectivity and clean tile verification
    Fails loudly (HTTP 503) if any check is unsatisfied.
    """
    details = []
    db_connected = False
    table_counts = {"cyclones": 0, "alerts": 0, "shelters": 0, "hospitals": 0}

    # 1. Database & Table Counts Check
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
        table_counts["cyclones"] = db.query(Cyclone).count()
        table_counts["alerts"] = db.query(Alert).count()
        table_counts["shelters"] = db.query(Shelter).count()
        table_counts["hospitals"] = db.query(Hospital).count()
    except Exception as e:
        details.append(f"Database query error: {str(e)}")

    tables_healthy = db_connected and all(cnt > 0 for cnt in table_counts.values())
    for tbl, count in table_counts.items():
        if count == 0:
            details.append(f"Table '{tbl}' is empty (0 rows). Non-zero rows required.")

    # 2. Map Tile Provider Check
    tile_meta = {"provider": "OpenStreetMap", "verified": False}
    tile_url = "https://tile.openstreetmap.org/1/1/0.png"
    try:
        req = urllib.request.Request(
            tile_url,
            headers={"User-Agent": "CycloneX-BackendReadiness/1.0", "Accept": "image/png,image/*"}
        )
        start_t = time.time()
        with urllib.request.urlopen(req, timeout=4.0) as res:
            latency_ms = (time.time() - start_t) * 1000.0
            content = res.read()
            if res.status == 200 and len(content) > 500 and b"API KEY REQUIRED" not in content:
                tile_meta = {
                    "provider": "OpenStreetMap",
                    "url": tile_url,
                    "verified": True,
                    "latency_ms": round(latency_ms, 1),
                    "bytes": len(content)
                }
            else:
                details.append(f"Map tile provider returned invalid or watermarked tile from {tile_url}")
    except Exception as e:
        details.append(f"Map tile provider probe error: {str(e)}")

    is_ready = tables_healthy and tile_meta.get("verified", False)

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessStatus(
        ready=is_ready,
        status="ready" if is_ready else "not_ready",
        database_connected=db_connected,
        table_counts=table_counts,
        tables_healthy=tables_healthy,
        map_tile_provider=tile_meta,
        details=details,
        timestamp_utc=datetime.now(timezone.utc).isoformat()
    )


