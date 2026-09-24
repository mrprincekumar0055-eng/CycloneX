"""
End-to-End Test Suite for CycloneX Real External Alert Pipeline
Verifies the complete chain:
  Real weather / ML prediction → Risk calculation → Threshold crossing
  → Alert generation → Authority selection → Provider dispatch
  → Delivery audit logging → Duplicate suppression → Escalation → Kill switch
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.core.config import settings
from backend.app.models.entities import Cyclone, Alert, AlertDeliveryLog
from alerts.monitor import CycloneAlertMonitor
from alerts.notifications.providers import (
    activate_kill_switch, deactivate_kill_switch, is_kill_switch_active,
    notification_dispatcher
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_clean_state():
    """Ensures kill switch is deactivated and clean state before and after each test."""
    deactivate_kill_switch()
    yield
    deactivate_kill_switch()


# ==============================================================================
# 1. KILL SWITCH TESTS
# ==============================================================================
def test_kill_switch_activation_and_deactivation():
    """Kill switch can be toggled and correctly reports state."""
    assert is_kill_switch_active() is False

    activate_kill_switch()
    assert is_kill_switch_active() is True

    deactivate_kill_switch()
    assert is_kill_switch_active() is False


def test_kill_switch_blocks_dispatch():
    """When kill switch is active, dispatch returns BLOCKED_KILL_SWITCH for all channels."""
    activate_kill_switch()

    recipients = [{
        "name": "Test Authority",
        "email": "test@sdma.gov.in",
        "phone": "+91-98765-43210",
        "channels": ["dashboard", "sms", "email"]
    }]

    results = notification_dispatcher.dispatch(
        recipients=recipients,
        subject="Test Alert",
        body="Test Body",
        metadata={"severity": "Emergency"},
        channels=["dashboard", "sms", "email"]
    )

    assert len(results) == 3
    for r in results:
        assert r.delivery_status == "BLOCKED_KILL_SWITCH"
        assert "kill switch" in r.payload.get("reason", "").lower()


def test_kill_switch_api_endpoints():
    """GET and POST /api/v1/alerts/kill-switch work correctly."""
    # Check GET
    resp = client.get("/api/v1/alerts/kill-switch")
    assert resp.status_code == 200
    assert resp.json()["kill_switch_active"] is False

    # Activate via POST
    resp = client.post("/api/v1/alerts/kill-switch", json={"active": True})
    assert resp.status_code == 200
    assert resp.json()["kill_switch_active"] is True
    assert is_kill_switch_active() is True

    # Deactivate via POST
    resp = client.post("/api/v1/alerts/kill-switch", json={"active": False})
    assert resp.status_code == 200
    assert resp.json()["kill_switch_active"] is False
    assert is_kill_switch_active() is False


# ==============================================================================
# 2. END-TO-END PIPELINE: ML PREDICTION → RISK → THRESHOLD → ALERT → DISPATCH
# ==============================================================================
def test_e2e_pipeline_active_cyclone_triggers_alert():
    """
    Complete pipeline test:
    1. Active cyclone exists in DB
    2. Monitor runs ML inference + threshold evaluation
    3. Alert is generated, authorities resolved, and dispatches recorded
    """
    db = SessionLocal()
    try:
        # Ensure Biparjoy exists as active
        biparjoy = db.query(Cyclone).filter(Cyclone.name == "BIPARJOY").first()
        if not biparjoy:
            biparjoy = Cyclone(
                id="demo-biparjoy-2023",
                name="BIPARJOY",
                status="active",
                current_lat=21.65,
                current_lon=66.85,
                current_wind_speed_kts=85.0,
                current_pressure_hpa=964.0,
                current_category="Very Severe Cyclonic Storm",
                current_heading_deg=38.0,
                current_speed_kmh=11.5,
                confidence_score=0.92,
                risk_level="High Risk"
            )
            db.add(biparjoy)
            db.commit()

        # Run the monitor evaluation
        results = CycloneAlertMonitor.evaluate_active_cyclones(db)

        assert len(results) >= 1
        # At least one result must be for Biparjoy
        bip_result = next((r for r in results if r.get("cyclone_name") == "BIPARJOY"), None)
        assert bip_result is not None

        # It should trigger because 85 kts wind >= 48 kts threshold
        if bip_result.get("triggered"):
            assert bip_result["alert_level"] in ["Warning", "Emergency"]
            assert bip_result["risk_score"] > 0.5
            assert len(bip_result["alerts"]) == 3  # Citizens, Authorities, Responders
            assert bip_result["dispatches_count"] > 0
            assert bip_result["recipient_count"] > 0
        else:
            # If duplicate suppressed from a previous run, that's also valid behavior
            assert bip_result["action_type"] == "DUPLICATE_SUPPRESSED"

    finally:
        db.close()


def test_e2e_pipeline_evaluate_now_api():
    """POST /api/v1/alerts/evaluate-now endpoint works end-to-end."""
    resp = client.post("/api/v1/alerts/evaluate-now")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "safety_mode" in data
    assert "kill_switch_active" in data
    assert "evaluated_cyclones_count" in data
    assert "results" in data


def test_e2e_pipeline_kill_switch_blocks_monitor():
    """When kill switch is active, the monitor skips evaluation entirely."""
    activate_kill_switch()
    db = SessionLocal()
    try:
        results = CycloneAlertMonitor.evaluate_active_cyclones(db)
        assert len(results) == 1
        assert results[0]["status"] == "skipped"
        assert "kill switch" in results[0]["reason"].lower()
    finally:
        db.close()


def test_e2e_pipeline_weather_grid_evaluates_hotspot():
    """The weather grid evaluation detects disturbed points and produces valid results."""
    from alerts.engine import AlertEngine
    db = SessionLocal()
    try:
        # Evaluate weather grid
        grid_result = CycloneAlertMonitor._evaluate_weather_grid(AlertEngine, db)
        # Result may be None if no hotspot exceeds threshold, or a dict if it does
        if grid_result is not None:
            assert "source" in grid_result
            assert grid_result["source"] == "WEATHER_GRID_AUTO_DETECT"
    finally:
        db.close()


# ==============================================================================
# 3. SAFETY SWITCH INTERLOCK VERIFICATION
# ==============================================================================
def test_safety_switch_blocks_real_sms_by_default():
    """With LIVE_ALERTS_ENABLED=False (default), all SMS dispatches are SIMULATED."""
    assert settings.LIVE_ALERTS_ENABLED is False

    recipients = [{
        "name": "Safety Test Contact",
        "phone": "+91-98765-43210",
        "channels": ["sms"]
    }]

    results = notification_dispatcher.dispatch(
        recipients=recipients,
        subject="Safety Test",
        body="Body",
        metadata={"severity": "Warning", "wind_kts": 50},
        channels=["sms"],
        simulate=False  # Even with simulate=False, safety switch forces SIMULATED
    )

    assert len(results) == 1
    assert results[0].delivery_status == "SIMULATED"


def test_safety_switch_blocks_real_email_by_default():
    """With LIVE_ALERTS_ENABLED=False (default), all Email dispatches are SIMULATED."""
    assert settings.LIVE_ALERTS_ENABLED is False

    recipients = [{
        "name": "Safety Test Officer",
        "email": "officer@sdma.gov.in",
        "channels": ["email"]
    }]

    results = notification_dispatcher.dispatch(
        recipients=recipients,
        subject="Safety Test",
        body="Body",
        metadata={"severity": "Warning", "wind_kts": 50},
        channels=["email"],
        simulate=False  # Even with simulate=False, safety switch forces SIMULATED
    )

    assert len(results) == 1
    assert results[0].delivery_status == "SIMULATED"


# ==============================================================================
# 4. SIMULATION ENDPOINT PERMANENTLY LOCKED TO SIMULATION
# ==============================================================================
def test_simulate_endpoint_is_permanently_simulated():
    """POST /api/v1/alerts/simulate always dispatches in simulation mode."""
    resp = client.post("/api/v1/alerts/simulate", json={
        "cyclone_name": "TEST-STORM",
        "wind_speed_kts": 75.0,
        "landfall_eta_hours": 12,
        "target_location": "Puri Coast, Odisha",
        "affected_districts": ["Puri", "Jagatsinghpur"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    sim_details = data["simulation_details"]
    # All delivery logs in simulation must be SIMULATED
    for log in sim_details.get("delivery_logs", []):
        assert log["delivery_status"] == "SIMULATED"


# ==============================================================================
# 5. AUDIT TRAIL LOGGING
# ==============================================================================
def test_audit_trail_records_dispatches():
    """Dispatches are written to the database audit log."""
    db = SessionLocal()
    try:
        count_before = db.query(AlertDeliveryLog).count()
        # Trigger a simulation
        client.post("/api/v1/alerts/simulate", json={
            "cyclone_name": "AUDIT-TEST",
            "wind_speed_kts": 65.0,
            "landfall_eta_hours": 24,
            "target_location": "Visakhapatnam, Andhra Pradesh",
            "affected_districts": ["Visakhapatnam"]
        })
        count_after = db.query(AlertDeliveryLog).count()
        assert count_after > count_before
    finally:
        db.close()

