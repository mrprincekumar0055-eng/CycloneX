import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, 
    Text, JSON, Enum, Index
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), unique=True, nullable=False, index=True) # admin, official, responder, citizen
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    role = relationship("Role", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")


class Cyclone(Base):
    __tablename__ = "cyclones"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    basin = Column(String(50), nullable=False, default="North Indian Ocean") # Bay of Bengal, Arabian Sea, etc.
    status = Column(String(50), nullable=False, default="active") # active, dissipated, historical
    genesis_time = Column(DateTime, nullable=False, default=utc_now)
    dissipation_time = Column(DateTime, nullable=True)
    
    # Current state snapshot
    current_lat = Column(Float, nullable=True)
    current_lon = Column(Float, nullable=True)
    current_wind_speed_kts = Column(Float, nullable=True) # knots
    current_pressure_hpa = Column(Float, nullable=True) # hPa
    current_category = Column(String(50), nullable=True) # Depression, CS, VSCS, Super Cyclone, etc.
    current_heading_deg = Column(Float, nullable=True) # Degrees 0-360
    current_speed_kmh = Column(Float, nullable=True) # Movement speed km/h
    confidence_score = Column(Float, nullable=True, default=0.92)
    risk_level = Column(String(50), nullable=True, default="High") # Low, Moderate, High, Extreme
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    observations = relationship("Observation", back_populates="cyclone", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="cyclone", cascade="all, delete-orphan")
    risk_zones = relationship("RiskZone", back_populates="cyclone", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="cyclone", cascade="all, delete-orphan")


class Observation(Base):
    __tablename__ = "observations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    cyclone_id = Column(String(36), ForeignKey("cyclones.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    wind_speed_kts = Column(Float, nullable=False)
    central_pressure_hpa = Column(Float, nullable=False)
    imd_category = Column(String(50), nullable=True)
    source = Column(String(50), default="IMD / JTWC") # IMD, JTWC, IBTrACS, AI-Fused
    is_forecast = Column(Boolean, default=False)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    cyclone = relationship("Cyclone", back_populates="observations")


class SatelliteObservation(Base):
    __tablename__ = "satellite_observations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    cyclone_id = Column(String(36), ForeignKey("cyclones.id"), nullable=True, index=True)
    sensor = Column(String(50), default="MODIS") # MODIS, VIIRS, INSAT-3D
    band = Column(String(50), default="TrueColor") # TrueColor, ThermalIR, WaterVapor
    timestamp = Column(DateTime, nullable=False, default=utc_now)
    tile_url = Column(String(500), nullable=False)
    min_lat = Column(Float, nullable=False)
    min_lon = Column(Float, nullable=False)
    max_lat = Column(Float, nullable=False)
    max_lon = Column(Float, nullable=False)
    cloud_top_temp_c = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    cyclone_id = Column(String(36), ForeignKey("cyclones.id"), nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=utc_now)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    surface_wind_10m_kts = Column(Float, nullable=True)
    wind_gust_kts = Column(Float, nullable=True)
    sea_surface_temp_c = Column(Float, nullable=True)
    sea_level_pressure_hpa = Column(Float, nullable=True)
    relative_humidity_pct = Column(Float, nullable=True)
    vertical_wind_shear_kts = Column(Float, nullable=True)
    source = Column(String(50), default="Open-Meteo")
    created_at = Column(DateTime, default=utc_now)


class OceanObservation(Base):
    __tablename__ = "ocean_observations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=utc_now)
    sea_surface_temp_c = Column(Float, nullable=False)
    ocean_heat_content_kj = Column(Float, nullable=True)
    salinity_psu = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    cyclone_id = Column(String(36), ForeignKey("cyclones.id"), nullable=False, index=True)
    model_version = Column(String(50), default="v1.0-fusion")
    run_timestamp = Column(DateTime, nullable=False, default=utc_now)
    overall_confidence = Column(Float, default=0.89)
    detection_status = Column(String(50), default="Detected") # Detected, Incipient, Dissipated
    development_stage = Column(String(50), default="Very Severe Cyclonic Storm")
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    cyclone = relationship("Cyclone", back_populates="predictions")
    prediction_points = relationship("PredictionPoint", back_populates="prediction", cascade="all, delete-orphan")


class PredictionPoint(Base):
    __tablename__ = "prediction_points"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    prediction_id = Column(String(36), ForeignKey("predictions.id"), nullable=False, index=True)
    forecast_hour = Column(Integer, nullable=False) # 6, 12, 24, 48, 72
    valid_time = Column(DateTime, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    predicted_wind_speed_kts = Column(Float, nullable=False)
    predicted_pressure_hpa = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    uncertainty_radius_km = Column(Float, nullable=False) # 6h: 30km, 24h: 90km, 72h: 220km
    confidence_score = Column(Float, default=0.9)
    created_at = Column(DateTime, default=utc_now)
    
    prediction = relationship("Prediction", back_populates="prediction_points")


class RiskZone(Base):
    __tablename__ = "risk_zones"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    cyclone_id = Column(String(36), ForeignKey("cyclones.id"), nullable=False, index=True)
    forecast_hour = Column(Integer, default=24)
    zone_type = Column(String(50), default="wind_swath_64kt") # 34kt, 50kt, 64kt, surge, inland_flood
    severity = Column(String(50), default="High") # Low, Moderate, High, Extreme
    hazard_score = Column(Float, default=0.85)
    exposure_score = Column(Float, default=0.78)
    vulnerability_score = Column(Float, default=0.72)
    composite_risk_score = Column(Float, default=0.81)
    affected_district = Column(String(100), nullable=True)
    affected_state = Column(String(100), nullable=True)
    polygon_geojson = Column(JSON, nullable=False) # GeoJSON geometry
    created_at = Column(DateTime, default=utc_now)
    
    cyclone = relationship("Cyclone", back_populates="risk_zones")
    exposure_records = relationship("PopulationExposure", back_populates="risk_zone", cascade="all, delete-orphan")


class PopulationExposure(Base):
    __tablename__ = "population_exposure"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    risk_zone_id = Column(String(36), ForeignKey("risk_zones.id"), nullable=False, index=True)
    district = Column(String(100), nullable=False)
    total_population = Column(Integer, nullable=False)
    vulnerable_population = Column(Integer, nullable=False) # Elderly, children, coastal dwellers
    evacuation_needed_count = Column(Integer, nullable=False)
    dataSource = Column(String(50), default="WorldPop 2024 (100m)")
    created_at = Column(DateTime, default=utc_now)
    
    risk_zone = relationship("RiskZone", back_populates="exposure_records")


class Facility(Base):
    __tablename__ = "facilities"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    osm_id = Column(String(50), nullable=True)
    name = Column(String(200), nullable=False)
    facility_type = Column(String(50), nullable=False, index=True) # shelter, hospital, airport, port, bridge, emergency_hub
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    capacity = Column(Integer, nullable=True)
    operational_status = Column(String(50), default="Ready") # Ready, In-Use, Inundated, Offline
    is_officially_verified = Column(Boolean, default=False)
    contact_phone = Column(String(50), nullable=True)
    extra_attributes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class Shelter(Base):
    __tablename__ = "shelters"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=True)
    name = Column(String(200), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    total_capacity = Column(Integer, default=1500)
    current_occupancy = Column(Integer, default=0)
    generator_available = Column(Boolean, default=True)
    drinking_water_available = Column(Boolean, default=True)
    medical_kit_available = Column(Boolean, default=True)
    elevation_meters = Column(Float, default=12.5)
    is_verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class Hospital(Base):
    __tablename__ = "hospitals"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=True)
    name = Column(String(200), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    total_beds = Column(Integer, default=300)
    available_icu_beds = Column(Integer, default=24)
    emergency_trauma_unit = Column(Boolean, default=True)
    helipad = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)


class Route(Base):
    __tablename__ = "routes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    origin_name = Column(String(150), nullable=False)
    destination_shelter_id = Column(String(36), ForeignKey("shelters.id"), nullable=True)
    destination_name = Column(String(150), nullable=False)
    distance_km = Column(Float, nullable=False)
    travel_time_minutes = Column(Float, nullable=False)
    route_risk_level = Column(String(50), default="Safe") # Safe, Moderate Risk, Hazardous
    route_geojson = Column(JSON, nullable=False) # LineString GeoJSON
    source = Column(String(50), default="OSRM / Geodesic")
    created_at = Column(DateTime, default=utc_now)


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    cyclone_id = Column(String(36), ForeignKey("cyclones.id"), nullable=True, index=True)
    severity = Column(String(50), default="Warning") # Advisory, Watch, Warning, Emergency
    alert_level = Column(String(50), default="Warning") # Advisory, Watch, Warning, Emergency
    status = Column(String(50), default="ACTIVE", index=True) # ACTIVE, ACKNOWLEDGED, ESCALATED, RESOLVED
    parent_alert_id = Column(String(36), ForeignKey("alerts.id"), nullable=True)
    audience = Column(String(50), default="All") # Citizens, Authorities, Emergency Responders, All
    headline = Column(String(255), nullable=False)
    hazard = Column(String(100), nullable=False) # Gale Winds, Storm Surge, Flash Flooding
    expected_time = Column(DateTime, nullable=True)
    location_description = Column(String(255), nullable=False)
    affected_districts = Column(JSON, nullable=True) # List of affected district names
    risk_score = Column(Float, nullable=True)
    trigger_event = Column(String(100), default="THRESHOLD_BREACH")
    is_simulation = Column(Boolean, default=False, index=True)
    explanation = Column(Text, nullable=False)
    recommended_actions = Column(JSON, nullable=False) # List of action strings
    confidence_pct = Column(Float, default=90.0)
    official_source = Column(String(100), default="IMD / CycloneX AI Decision Engine")
    is_official_warning = Column(Boolean, default=False) # False = AI Early Warning Advisory
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    delivery_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    cyclone = relationship("Cyclone", back_populates="alerts")
    delivery_logs = relationship("AlertDeliveryLog", back_populates="alert", cascade="all, delete-orphan")


class AlertDeliveryLog(Base):
    __tablename__ = "alert_delivery_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    alert_id = Column(String(36), ForeignKey("alerts.id"), nullable=False, index=True)
    channel = Column(String(50), nullable=False) # dashboard, sms, email
    recipient_name = Column(String(150), nullable=False)
    recipient_contact = Column(String(200), nullable=False)
    delivery_status = Column(String(50), default="DELIVERED") # DELIVERED, SIMULATED, FAILED, PENDING
    trigger_type = Column(String(50), default="THRESHOLD_BREACH")
    payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=utc_now)
    
    alert = relationship("Alert", back_populates="delivery_logs")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False, unique=True)
    task_type = Column(String(50), nullable=False) # detection, classification, intensity, track
    framework = Column(String(50), default="Scikit-Learn / PyTorch")
    artifact_path = Column(String(255), nullable=True)
    dataset_version = Column(String(100), default="IBTrACS-v04r00-NIO")
    parameters = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class ModelMetric(Base):
    __tablename__ = "model_metrics"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_version_id = Column(String(36), ForeignKey("model_versions.id"), nullable=False)
    metric_name = Column(String(50), nullable=False) # Track_MAE_24h_km, Intensity_MAE_kts, Precision, Recall
    metric_value = Column(Float, nullable=False)
    evaluation_split = Column(String(50), default="test_2015_2023")
    created_at = Column(DateTime, default=utc_now)


class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_name = Column(String(100), unique=True, nullable=False) # NOAA IBTrACS, NASA GIBS, Open-Meteo, WorldPop, OSM
    source_url = Column(String(255), nullable=False)
    status = Column(String(50), default="Healthy") # Healthy, Degraded, Cached Fallback
    last_sync = Column(DateTime, default=utc_now)
    latency_ms = Column(Integer, default=120)
    records_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    user = relationship("User", back_populates="audit_logs")

