from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings
import os

# Resolve database URL (support serverless writable /tmp directory if running on Vercel/Lambda)
db_url = settings.DATABASE_URL
connect_args = {}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # Guarantee writable /tmp SQLite on serverless / Linux / non-writable environments
    is_serverless = bool(
        os.environ.get("VERCEL")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("VERCEL_ENV")
        or os.name != "nt"
        or not os.access(".", os.W_OK)
    )
    if is_serverless:
        import tempfile
        import shutil
        tmp_db = os.path.join(tempfile.gettempdir(), "cyclonex.db")
        candidate_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cyclonex.db"),
            os.path.join(os.getcwd(), "cyclonex.db"),
            os.path.join(os.getcwd(), "backend", "cyclonex.db"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyclonex.db"),
            "/var/task/cyclonex.db",
            "/var/task/backend/cyclonex.db"
        ]
        for cp in candidate_paths:
            if os.path.exists(cp) and not os.path.exists(tmp_db):
                try:
                    shutil.copy2(cp, tmp_db)
                except Exception:
                    pass
                break
        db_url = f"sqlite:///{tmp_db.replace('\\', '/')}"

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

        pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

