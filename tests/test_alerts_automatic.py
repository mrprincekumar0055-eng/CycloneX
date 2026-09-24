"""
Comprehensive Test Suite for CycloneX Automatic Cyclone Alert System
Verifies:
1. Multi-factor Risk Calculation & Threshold Detection (Advisory -> Watch -> Warning -> Emergency)
2. Authority & Stakeholder Directory Resolution
3. Duplicate Suppression within Cooldown Period
4. Severity-Based Escalation Rules (Cooldown Bypass & Parent Chaining)
5. Multi-Channel Notification Dispatch (Dashboard, SMS, Email) & Fault Tolerance
6. Delivery Audit Logging
7. Simulation Mode for Live Demo Execution
8. Alert Lifecycle State Machine (ACTIVE -> ACKNOWLEDGED -> ESCALATED -> RESOLVED)
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.app.main import app
from alerts.threshold_engine import AlertThresholdEngine
from alerts.authority_directory import AuthorityDirectory
from alerts.escalation_manager import EscalationManager
from alerts.notifications.providers import (
    NotificationDispatcher,
    SMSNotificationProvider,
    EmailNotificationProvider,
    DashboardNotificationProvider
)
from alerts.engine import AlertEngine

client = TestClient(app)

# ==========================================
# 1. THRESHOLD DETECTION TESTS
# ==========================================
def test_threshold_advisory_trigger():
    """Deep depression / mild wind triggers Advisory level."""
    res = AlertThresholdEngine.evaluate_threshold(
        predicted_wind_kts=30.0,
        central_pressure_hpa=1002.0,
        landfall_eta_hours=84.0,
        uncertainty_radius_km=70.0
    )
    assert res["is_alert_triggered"] is True
    assert res["alert_level"] == "Advisory"
    assert res["risk_score"] >= 0.30

def test_threshold_watch_trigger():
    """Cyclonic storm with 72h lead time triggers Watch level."""
    res = AlertThresholdEngine.evaluate_threshold(
        predicted_wind_kts=38.0,
        central_pressure_hpa=992.0,
        landfall_eta_hours=60.0,
        uncertainty_radius_km=80.0
    )
    assert res["is_alert_triggered"] is True
    assert res["alert_level"] == "Watch"

def test_threshold_warning_trigger():
    """Severe cyclonic storm (55 kt, 36h ETA) triggers Warning level."""
    res = AlertThresholdEngine.evaluate_threshold(
        predicted_wind_kts=55.0,
        central_pressure_hpa=978.0,
        landfall_eta_hours=36.0,
        uncertainty_radius_km=60.0
    )
    assert res["is_alert_triggered"] is True
    assert res["alert_level"] == "Warning"
    assert res["risk_score"] >= 0.55

def test_threshold_emergency_trigger():
    """Extremely severe cyclonic threat (85 kt, 18h ETA) triggers Emergency level."""
    res = AlertThresholdEngine.evaluate_threshold(
        predicted_wind_kts=85.0,
        central_pressure_hpa=960.0,
        landfall_eta_hours=18.0,
        uncertainty_radius_km=45.0,
        exposed_population=1_200_000
    )
    assert res["is_alert_triggered"] is True
    assert res["alert_level"] == "Emergency"
    assert res["risk_score"] >= 0.70

def test_threshold_normal_conditions_no_trigger():
    """Ambient conditions (15 kt wind, 1010 hPa) do NOT trigger alerts."""
    res = AlertThresholdEngine.evaluate_threshold(
        predicted_wind_kts=15.0,
        central_pressure_hpa=1010.0,
        landfall_eta_hours=120.0
    )
    assert res["is_alert_triggered"] is False
    assert res["alert_level"] == "Normal"

# ==========================================
# 2. AUTHORITY DIRECTORY TESTS
# ==========================================
def test_authority_directory_resolution():
    """Verifies district to DDMA/SDMA/NDRF/Coast Guard resolution."""
    recipients = AuthorityDirectory.get_recipients_for_districts(["Kutch", "Devbhumi Dwarka"])
    assert len(recipients) >= 4
    
    audiences = {r["audience"] for r in recipients}
    assert "Authorities" in audiences
    assert "Emergency Responders" in audiences
    assert "Citizens" in audiences

    # Check collector and control room emails exist
    emails = [r.get("email") for r in recipients if r.get("email")]
    assert any("kutch" in e.lower() for e in emails)

# ==========================================
# 3. DUPLICATE PREVENTION & COOLDOWN TESTS
# ==========================================
def test_duplicate_prevention_within_cooldown():
    """Repeated alerts at the same severity within cooldown are suppressed."""
    mgr = EscalationManager(cooldown_minutes=60)
    
    # First dispatch
    should1, act1, p1 = mgr.evaluate_dispatch("BIPARJOY", "Kutch", "Warning")
    assert should1 is True
    assert act1 == "NEW"
    mgr.record_dispatched_alert("BIPARJOY", "Kutch", "alt-001", "Warning")

    # Immediate second dispatch at same level -> Suppressed
    should2, act2, p2 = mgr.evaluate_dispatch("BIPARJOY", "Kutch", "Warning")
    assert should2 is False
    assert act2 == "DUPLICATE_SUPPRESSED"
    assert p2 == "alt-001"

    # Lower level also suppressed
    should3, act3, p3 = mgr.evaluate_dispatch("BIPARJOY", "Kutch", "Watch")
    assert should3 is False
    assert act3 == "DUPLICATE_SUPPRESSED"

# ==========================================
# 4. ESCALATION RULES & PARENT CHAINING
# ==========================================
def test_escalation_bypasses_cooldown_and_links_parent():
    """Higher severity trigger bypasses cooldown, records ESCALATED, and links parent alert."""
    mgr = EscalationManager(cooldown_minutes=60)
    
    # 1. Initial Watch alert
    mgr.record_dispatched_alert("BIPARJOY", "Kutch", "alt-initial", "Watch")

    # 2. Upgraded to Emergency -> Bypasses cooldown!
    should_esc, act_esc, parent_id = mgr.evaluate_dispatch("BIPARJOY", "Kutch", "Emergency")
    assert should_esc is True
    assert act_esc == "ESCALATED"
    assert parent_id == "alt-initial"

# ==========================================
# 5. MULTI-CHANNEL DISPATCH & FAULT TOLERANCE
# ==========================================
def test_notification_dispatch_channels():
    """Tests successful dispatch across Dashboard, SMS, and Email."""
    dispatcher = NotificationDispatcher()
    recipients = [
        {
            "name": "Kutch EOC",
            "audience": "Authorities",
            "email": "collector-kutch@gujarat.gov.in",
            "phone": "+91-2832-250020",
            "channels": ["dashboard", "sms", "email"]
        }
    ]
    results = dispatcher.dispatch(
        recipients=recipients,
        subject="[WARNING] Cyclone Threat",
        body="Severe storm expected.",
        metadata={"severity": "Warning", "wind_kts": 85},
        simulate=True
    )
    assert len(results) == 3
    channels = {r.channel for r in results}
    assert channels == {"dashboard", "sms", "email"}
    assert all(r.delivery_status == "SIMULATED" for r in results)

def test_notification_provider_failure_handling():
    """Provider failure does not crash dispatcher; records failure in audit result."""
    dispatcher = NotificationDispatcher()
    recipients = [
        {
            "name": "Fault Test Contact",
            "audience": "Authorities",
            "email": "test@error.gov.in",
            "phone": "+91-99999-00000",
            "channels": ["sms", "email"]
        }
    ]
    # Inject forced provider network failure
    results = dispatcher.dispatch(
        recipients=recipients,
        subject="Test Alert",
        body="Test message",
        metadata={"severity": "Warning", "force_sms_failure": True, "force_email_failure": True},
        simulate=False
    )
    assert len(results) == 2
    for r in results:
        assert r.delivery_status == "FAILED"
        assert r.error_message is not None

# ==========================================
# 6. SIMULATION & API ENDPOINT TESTS
# ==========================================
def test_simulation_endpoint():
    """POST /api/v1/alerts/simulate triggers simulated cyclone alerts safely."""
    payload = {
        "cyclone_name": "BIPARJOY",
        "scenario": "Simulated Grand Finale Jury Demonstration",
        "wind_speed_kts": 95.0,
        "central_pressure_hpa": 954.0,
        "landfall_eta_hours": 18,
        "target_location": "Kutch & Saurashtra Coast, Gujarat",
        "affected_districts": ["Kutch", "Devbhumi Dwarka"],
        "channels": ["dashboard", "sms", "email"],
        "simulate_delivery": True
    }
    res = client.post("/api/v1/alerts/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    sim = data["simulation_details"]
    assert sim["triggered"] is True
    assert sim["alert_level"] in ["Warning", "Emergency"]
    assert len(sim["alerts"]) >= 1
    assert len(sim["delivery_logs"]) >= 1

def test_alert_statistics_endpoint():
    """GET /api/v1/alerts/stats returns active, acknowledged, escalated, resolved counts."""
    res = client.get("/api/v1/alerts/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "statuses" in stats
    assert "severities" in stats
    assert "active" in stats["statuses"]
    assert "acknowledged" in stats["statuses"]
    assert "escalated" in stats["statuses"]
    assert "resolved" in stats["statuses"]

def test_alert_lifecycle_state_machine():
    """Verifies acknowledge -> escalate -> resolve state transitions via API."""
    # First get or trigger an alert
    get_res = client.get("/api/v1/alerts")
    assert get_res.status_code == 200
    alerts = get_res.json()
    assert len(alerts) >= 1
    target_alert = alerts[0]
    alert_id = target_alert["id"]

    # 1. Acknowledge
    ack_res = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={
        "action": "acknowledge",
        "operator_name": "Test Watch Officer",
        "notes": "Acknowledged by Gujarat SDMA"
    })
    assert ack_res.status_code == 200
    assert ack_res.json()["new_status"] == "ACKNOWLEDGED"

    # 2. Escalate
    esc_res = client.post(f"/api/v1/alerts/{alert_id}/escalate", json={
        "action": "escalate",
        "new_severity": "Emergency",
        "operator_name": "State Relief Commissioner"
    })
    assert esc_res.status_code == 200
    assert esc_res.json()["new_status"] == "ESCALATED"
    assert esc_res.json()["severity"] == "Emergency"

    # 3. Resolve
    res_res = client.post(f"/api/v1/alerts/{alert_id}/resolve", json={
        "action": "resolve",
        "operator_name": "EOC Incident Commander",
        "notes": "Storm de-escalated post landfall"
    })
    assert res_res.status_code == 200
    assert res_res.json()["new_status"] == "RESOLVED"

    # 4. Check audit log for this alert
    audit_res = client.get(f"/api/v1/alerts/{alert_id}/audit-log")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 3
    triggers = {l["trigger_type"] for l in logs}
    assert "OPERATOR_ACKNOWLEDGE" in triggers
    assert "MANUAL_ESCALATION" in triggers
    assert "ALERT_RESOLVE" in triggers
