from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings
import os

# Resolve database URL (support serverless writable /tmp directory if running on Vercel/Lambda)
db_url = settings.DATABASE_URL
connect_args = {}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        try:
            import shutil
            tmp_db = "/tmp/cyclonex.db"
            root_db = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cyclonex.db")
            if not os.path.exists(tmp_db) and os.path.exists(root_db):
                shutil.copy2(root_db, tmp_db)
            if os.path.exists(tmp_db):
                db_url = f"sqlite:///{tmp_db}"
        except Exception:
            pass

engine = create_engine(
    db_url,
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

