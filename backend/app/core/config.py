from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "CycloneX"
    PROJECT_DESCRIPTION: str = "AI-Powered Cyclone Intelligence & Early Warning Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "cyclonex-super-secret-production-key-change-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite:///./cyclonex.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # External APIs
    NASA_GIBS_API_URL: str = "https://gibs.earthdata.nasa.gov"
    OPEN_METEO_API_URL: str = "https://api.open-meteo.com/v1"
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    OSRM_API_URL: str = "http://router.project-osrm.org"
    WORLDPOP_API_URL: str = "https://data.worldpop.org"
    
    # Operation modes
    DEMO_MODE: bool = True
    ALLOW_SYNTHETIC_FALLBACK: bool = True
    
    # Notification & External Alerts Configuration
    LIVE_ALERTS_ENABLED: bool = False
    NOTIFICATION_MAX_HOURLY_SMS: int = 20
    NOTIFICATION_MAX_HOURLY_EMAIL: int = 50
    TEST_NOTIFICATION_PHONE: str = "+91-98765-43210"
    TEST_NOTIFICATION_EMAIL: str = "admin@cyclonex.gov.in"
    
    # SMS Provider (mock, twilio, generic_http)
    SMS_PROVIDER: str = "mock"
    TWILIO_ACCOUNT_SID: Union[str, None] = None
    TWILIO_AUTH_TOKEN: Union[str, None] = None
    TWILIO_FROM_NUMBER: Union[str, None] = None
    SMS_GATEWAY_URL: Union[str, None] = None
    SMS_GATEWAY_API_KEY: Union[str, None] = None
    
    # Email Provider (mock, smtp, sendgrid)
    EMAIL_PROVIDER: str = "mock"
    SMTP_HOST: Union[str, None] = None
    SMTP_PORT: int = 587
    SMTP_USER: Union[str, None] = None
    SMTP_PASSWORD: Union[str, None] = None
    SMTP_FROM_EMAIL: str = "CycloneX Operations <alerts@cyclonex.gov.in>"
    SMTP_USE_TLS: bool = True
    SENDGRID_API_KEY: Union[str, None] = None
    
    # Alert Monitor (automatic ML→alert evaluation loop)
    ALERT_MONITOR_ENABLED: bool = True
    ALERT_MONITOR_INTERVAL_SECONDS: int = 900  # 15 minutes, matches weather poll
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="allow")

settings = Settings()
