from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings
import os

# Connect args for SQLite support
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    import backend.app.models.entities  # noqa: F401 - Register models with Base
    Base.metadata.create_all(bind=engine)
    if settings.DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                result = conn.exec_driver_sql("PRAGMA table_info(alerts)")
                existing_cols = {row[1] for row in result.fetchall()}
                new_columns = [
                    ("alert_level", "VARCHAR(50) DEFAULT 'Warning'"),
                    ("status", "VARCHAR(50) DEFAULT 'ACTIVE'"),
                    ("parent_alert_id", "VARCHAR(36)"),
                    ("affected_districts", "JSON"),
                    ("risk_score", "FLOAT"),
                    ("trigger_event", "VARCHAR(100) DEFAULT 'THRESHOLD_BREACH'"),
                    ("is_simulation", "BOOLEAN DEFAULT 0"),
                    ("acknowledged_at", "DATETIME"),
                    ("acknowledged_by", "VARCHAR(100)"),
                    ("resolved_at", "DATETIME"),
                    ("delivery_summary", "JSON")
                ]
                for col_name, col_type in new_columns:
                    if col_name not in existing_cols:
                        conn.exec_driver_sql(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}")
                conn.commit()
        except Exception:
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

