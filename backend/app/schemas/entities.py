from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, EmailStr, ConfigDict

# Token
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

# User
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True

class UserCreate(UserBase):
    password: str
    role_name: Optional[str] = "citizen"

class UserOut(UserBase):
    id: str
    role_id: Optional[str] = None
    role_name: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Cyclone
class CycloneBase(BaseModel):
    name: str
    basin: str = "North Indian Ocean"
    status: str = "active"
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None
    current_wind_speed_kts: Optional[float] = None
    current_pressure_hpa: Optional[float] = None
    current_category: Optional[str] = None
    current_heading_deg: Optional[float] = None
    current_speed_kmh: Optional[float] = None
    confidence_score: Optional[float] = 0.92
    risk_level: Optional[str] = "High"

class CycloneCreate(CycloneBase):
    pass

class CycloneOut(CycloneBase):
    id: str
    genesis_time: datetime
    dissipation_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Observation
class ObservationOut(BaseModel):
    id: str
    cyclone_id: str
    timestamp: datetime
    lat: float
    lon: float
    wind_speed_kts: float
    central_pressure_hpa: float
    imd_category: Optional[str] = None
    source: str
    is_forecast: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Prediction Point & Prediction
class PredictionPointOut(BaseModel):
    id: str
    forecast_hour: int
    valid_time: datetime
    lat: float
    lon: float
    predicted_wind_speed_kts: float
    predicted_pressure_hpa: float
    category: str
    uncertainty_radius_km: float
    confidence_score: float

    model_config = ConfigDict(from_attributes=True)

class PredictionOut(BaseModel):
    id: str
    cyclone_id: str
    model_version: str
    run_timestamp: datetime
    overall_confidence: float
    detection_status: str
    development_stage: str
    explanation: Optional[str] = None
    prediction_points: List[PredictionPointOut] = []

    model_config = ConfigDict(from_attributes=True)

# Risk Zone & Population Exposure
class PopulationExposureOut(BaseModel):
    id: str
    district: str
    total_population: int
    vulnerable_population: int
    evacuation_needed_count: int
    dataSource: str

    model_config = ConfigDict(from_attributes=True)

class RiskZoneOut(BaseModel):
    id: str
    cyclone_id: str
    forecast_hour: int
    zone_type: str
    severity: str
    hazard_score: float
    exposure_score: float
    vulnerability_score: float
    composite_risk_score: float
    affected_district: Optional[str] = None
    affected_state: Optional[str] = None
    polygon_geojson: Dict[str, Any]
    exposure_records: List[PopulationExposureOut] = []

    model_config = ConfigDict(from_attributes=True)

# Facilities, Shelters, Hospitals
class FacilityOut(BaseModel):
    id: str
    osm_id: Optional[str] = None
    name: str
    facility_type: str
    lat: float
    lon: float
    district: Optional[str] = None
    state: Optional[str] = None
    capacity: Optional[int] = None
    operational_status: str
    is_officially_verified: bool
    contact_phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ShelterOut(BaseModel):
    id: str
    facility_id: Optional[str] = None
    name: str
    lat: float
    lon: float
    total_capacity: int
    current_occupancy: int
    generator_available: bool
    drinking_water_available: bool
    medical_kit_available: bool
    elevation_meters: float
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)

class HospitalOut(BaseModel):
    id: str
    facility_id: Optional[str] = None
    name: str
    lat: float
    lon: float
    total_beds: int
    available_icu_beds: int
    emergency_trauma_unit: bool
    helipad: bool

    model_config = ConfigDict(from_attributes=True)

# Routes
class RouteOut(BaseModel):
    id: str
    origin_name: str
    destination_shelter_id: Optional[str] = None
    destination_name: str
    distance_km: float
    travel_time_minutes: float
    route_risk_level: str
    route_geojson: Dict[str, Any]
    source: str

    model_config = ConfigDict(from_attributes=True)

# Alerts
class AlertDeliveryLogOut(BaseModel):
    id: str
    alert_id: str
    channel: str
    recipient_name: str
    recipient_contact: str
    delivery_status: str
    trigger_type: str
    payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertOut(BaseModel):
    id: str
    cyclone_id: Optional[str] = None
    severity: str
    alert_level: Optional[str] = "Warning"
    status: Optional[str] = "ACTIVE"
    parent_alert_id: Optional[str] = None
    audience: str
    headline: str
    hazard: str
    expected_time: Optional[datetime] = None
    location_description: str
    affected_districts: Optional[List[str]] = []
    risk_score: Optional[float] = None
    trigger_event: Optional[str] = "THRESHOLD_BREACH"
    is_simulation: Optional[bool] = False
    explanation: str
    recommended_actions: List[str]
    confidence_pct: float
    official_source: str
    is_official_warning: bool
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    delivery_summary: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertActionRequest(BaseModel):
    action: str # acknowledge, escalate, resolve
    operator_name: Optional[str] = "Disaster Operations Officer"
    notes: Optional[str] = None
    new_severity: Optional[str] = None

class AlertSimulationRequest(BaseModel):
    cyclone_name: Optional[str] = "BIPARJOY"
    scenario: Optional[str] = "Rapid Intensification & Landfall"
    wind_speed_kts: Optional[float] = 95.0
    central_pressure_hpa: Optional[float] = 955.0
    landfall_eta_hours: Optional[int] = 18
    target_location: Optional[str] = "Kutch & Saurashtra Coast, Gujarat"
    affected_districts: Optional[List[str]] = ["Kutch", "Devbhumi Dwarka", "Jamnagar"]
    confidence_score: Optional[float] = 0.94
    channels: Optional[List[str]] = ["dashboard", "sms", "email"]
    simulate_delivery: Optional[bool] = True

class AlertConfigUpdate(BaseModel):
    live_alerts_enabled: Optional[bool] = None
    sms_provider: Optional[str] = None
    email_provider: Optional[str] = None
    test_notification_phone: Optional[str] = None
    test_notification_email: Optional[str] = None

class AlertTestNotificationRequest(BaseModel):
    channel: Optional[str] = "both" # sms, email, both
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    message: Optional[str] = None

class AlertLiveDeliveryTestRequest(BaseModel):
    confirm_live_test: bool = False
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None

# System Health
class HealthStatus(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    demo_mode: bool
    data_freshness_utc: str
    active_cyclones_count: int

class ReadinessStatus(BaseModel):
    ready: bool
    status: str
    database_connected: bool
    table_counts: Dict[str, int]
    tables_healthy: bool
    map_tile_provider: Dict[str, Any]
    details: List[str]
    timestamp_utc: str

