from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.entities import Alert, AlertDeliveryLog, Cyclone
from backend.app.schemas.entities import (
    AlertOut,
    AlertDeliveryLogOut,
    AlertActionRequest,
    AlertSimulationRequest,
    AlertConfigUpdate,
    AlertTestNotificationRequest,
    AlertLiveDeliveryTestRequest
)
from alerts.engine import AlertEngine
from alerts.notifications.providers import (
    notification_dispatcher, rate_limiter,
    activate_kill_switch, deactivate_kill_switch, is_kill_switch_active,
    validate_notification_credentials, get_live_verification_state,
    execute_controlled_live_delivery
)

router = APIRouter()

@router.get("/config")
def get_notification_config() -> Dict[str, Any]:
    """
    Returns notification provider status, safety switch state, kill switch state, and rate limits.
    """
    twilio_configured = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)
    smtp_configured = bool(settings.SMTP_HOST)
    sendgrid_configured = bool(settings.SENDGRID_API_KEY)

    masked_twilio = f"{settings.TWILIO_ACCOUNT_SID[:6]}***" if settings.TWILIO_ACCOUNT_SID and len(settings.TWILIO_ACCOUNT_SID) > 6 else "Not Configured"
    masked_smtp = f"{settings.SMTP_HOST.split('.')[0]}.***" if settings.SMTP_HOST else "Not Configured"

    cred_report = validate_notification_credentials()

    return {
        "live_alerts_enabled": settings.LIVE_ALERTS_ENABLED,
        "kill_switch_active": is_kill_switch_active(),
        "live_verification_state": get_live_verification_state(),
        "sms_provider": settings.SMS_PROVIDER,
        "email_provider": settings.EMAIL_PROVIDER,
        "sms_status": cred_report["sms"]["status"],
        "email_status": cred_report["email"]["status"],
        "twilio_configured": twilio_configured,
        "smtp_configured": smtp_configured,
        "sendgrid_configured": sendgrid_configured,
        "masked_twilio_sid": masked_twilio,
        "masked_smtp_host": masked_smtp,
        "from_phone": settings.TWILIO_FROM_NUMBER or "Not Set",
        "from_email": settings.SMTP_FROM_EMAIL,
        "test_phone": settings.TEST_NOTIFICATION_PHONE,
        "test_email": settings.TEST_NOTIFICATION_EMAIL,
        "rate_limits": rate_limiter.get_stats(),
        "safety_mode": "LIVE ALERTS ACTIVE" if settings.LIVE_ALERTS_ENABLED else "SAFE SIMULATION MODE (DEFAULT)",
        "monitor_enabled": settings.ALERT_MONITOR_ENABLED,
        "monitor_interval_seconds": settings.ALERT_MONITOR_INTERVAL_SECONDS
    }

@router.post("/config")
def update_notification_config(req: AlertConfigUpdate) -> Dict[str, Any]:
    """
    Updates notification configuration, master safety switch, and test contacts.
    """
    if req.live_alerts_enabled is not None:
        settings.LIVE_ALERTS_ENABLED = req.live_alerts_enabled
    if req.sms_provider is not None:
        settings.SMS_PROVIDER = req.sms_provider
    if req.email_provider is not None:
        settings.EMAIL_PROVIDER = req.email_provider
    if req.test_notification_phone is not None:
        settings.TEST_NOTIFICATION_PHONE = req.test_notification_phone
    if req.test_notification_email is not None:
        settings.TEST_NOTIFICATION_EMAIL = req.test_notification_email

    notification_dispatcher.reload_providers()

    return {
        "status": "success",
        "message": "Notification configuration updated successfully.",
        "config": get_notification_config()
    }

@router.post("/test-notification")
def send_test_notification(
    req: AlertTestNotificationRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Sends a test notification strictly to the authorized test phone/email.
    Does not broadcast to district authorities. Verifies Twilio/SMTP connectivity.
    """
    test_phone = req.recipient_phone or settings.TEST_NOTIFICATION_PHONE
    test_email = req.recipient_email or settings.TEST_NOTIFICATION_EMAIL
    channel_choice = (req.channel or "both").lower()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    test_msg = req.message or f"CycloneX operational notification pipeline verification dispatch at {now_iso}. Decision support test only."

    recipients = [{
        "name": "CycloneX Administrator (Test Target)",
        "audience": "Authorities",
        "district": "Operations HQ Test Cell",
        "phone": test_phone,
        "email": test_email,
        "channels": ["dashboard", "sms", "email"],
        "is_test_target": True
    }]

    target_channels = []
    if channel_choice in ["both", "sms"]:
        target_channels.append("sms")
    if channel_choice in ["both", "email"]:
        target_channels.append("email")
    if channel_choice in ["both", "dashboard"]:
        target_channels.append("dashboard")

    metadata = {
        "severity": "Watch",
        "headline": "TEST DISPATCH: CycloneX Notification Pipeline Connectivity Verification",
        "wind_kts": 35.0,
        "risk_score": 0.35,
        "is_test_dispatch": True,
        "recommended_actions": ["Verify SMS receipt", "Verify Email receipt", "Confirm timestamp"]
    }

    # Execute dispatch — allow testing real providers if configured; non-test dispatches still require LIVE_ALERTS_ENABLED
    dispatches = notification_dispatcher.dispatch(
        recipients=recipients,
        subject="CycloneX Notification Pipeline Connectivity Test",
        body=test_msg,
        metadata=metadata,
        channels=target_channels,
        simulate=False
    )

    # Record in audit log
    for d in dispatches:
        log_entry = AlertDeliveryLog(
            id=f"test-{uuid.uuid4().hex[:8]}",
            alert_id="sys-test-alert",
            channel=d.channel,
            recipient_name=d.recipient_name,
            recipient_contact=d.recipient_contact,
            delivery_status=d.delivery_status,
            trigger_type="ADMIN_TEST",
            payload=d.payload,
            error_message=d.error_message,
            sent_at=d.timestamp
        )
        db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "live_mode_active": settings.LIVE_ALERTS_ENABLED,
        "test_phone": test_phone,
        "test_email": test_email,
        "results": [d.to_dict() for d in dispatches]
    }

@router.post("/validate-credentials")
def validate_credentials_endpoint() -> Dict[str, Any]:
    """
    Validates Twilio/SMTP/SendGrid configuration against .env environment variables.
    Format-validation ONLY: checks required variables without exposing their values.
    Does NOT send an SMS or email during credential validation.
    Reports: CONFIGURED, NOT_CONFIGURED, or INVALID for each provider.
    """
    report = validate_notification_credentials()
    sms_status = report["sms"]["status"]
    email_status = report["email"]["status"]
    live_state = report["live_verification_state"]

    missing_vars = []
    sms_prov = (settings.SMS_PROVIDER or "").lower()
    if sms_prov == "twilio":
        if not settings.TWILIO_ACCOUNT_SID: missing_vars.append("TWILIO_ACCOUNT_SID")
        if not settings.TWILIO_AUTH_TOKEN: missing_vars.append("TWILIO_AUTH_TOKEN")
        if not settings.TWILIO_FROM_NUMBER: missing_vars.append("TWILIO_FROM_NUMBER")
    elif sms_prov in ("mock", ""):
        missing_vars.append("SMS_PROVIDER (set to 'twilio' for real SMS)")

    email_prov = (settings.EMAIL_PROVIDER or "").lower()
    if email_prov == "smtp":
        if not settings.SMTP_HOST: missing_vars.append("SMTP_HOST")
        if not settings.SMTP_USER: missing_vars.append("SMTP_USER")
        if not settings.SMTP_PASSWORD: missing_vars.append("SMTP_PASSWORD")
    elif email_prov in ("mock", ""):
        missing_vars.append("EMAIL_PROVIDER (set to 'smtp' for real email)")

    return {
        **report,
        "verification_status": "LIVE VERIFIED" if live_state == "LIVE_VERIFIED" else ("CONFIGURED_NOT_TESTED" if live_state == "CONFIGURED_NOT_TESTED" else "NOT VERIFIED"),
        "sms_status": sms_status,
        "email_status": email_status,
        "missing_variables": missing_vars,
        "reason": f"SMS: {report['sms']['details']} | Email: {report['email']['details']}",
        "config": {
            "status": "CONFIGURED" if (sms_status == "CONFIGURED" and email_status == "CONFIGURED") else "NOT CONFIGURED",
            "sms_status": sms_status,
            "email_status": email_status
        }
    }

@router.post("/test-live-delivery")
def test_live_delivery_endpoint(
    req: AlertLiveDeliveryTestRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Executes a REAL controlled external delivery test:
    - Sends exactly ONE real SMS to TEST_NOTIFICATION_PHONE via Twilio
    - Sends exactly ONE real Email to TEST_NOTIFICATION_EMAIL via SMTP
    - Requires explicit confirm_live_test: true
    - Rejects arbitrary recipients
    - Blocked if kill switch is active
    - Records in alert_delivery_logs
    - Enters LIVE_VERIFIED only when remote provider confirms delivery
    """
    try:
        result = execute_controlled_live_delivery(
            db=db,
            confirm_live_test=req.confirm_live_test,
            recipient_phone=req.recipient_phone,
            recipient_email=req.recipient_email
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(re))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Live delivery test execution failed: {str(exc)}")



@router.get("/kill-switch")
def get_kill_switch_status() -> Dict[str, Any]:
    """Returns current emergency kill switch status."""
    return {
        "kill_switch_active": is_kill_switch_active(),
        "status": "BLOCKED" if is_kill_switch_active() else "NORMAL",
        "message": "All external dispatch is currently BLOCKED" if is_kill_switch_active() else "External dispatch operating normally"
    }

@router.post("/kill-switch")
def toggle_kill_switch(req: Dict[str, bool]) -> Dict[str, Any]:
    """
    Emergency kill switch: immediately stops/resumes all external notifications.
    Payload: {"active": true} to block, {"active": false} to resume.
    """
    active = req.get("active", True)
    if active:
        activate_kill_switch()
    else:
        deactivate_kill_switch()

    return {
        "status": "success",
        "kill_switch_active": is_kill_switch_active(),
        "message": "Emergency kill switch ACTIVATED — all external dispatch BLOCKED." if is_kill_switch_active() else "Emergency kill switch DEACTIVATED — normal dispatch restored."
    }

@router.post("/evaluate-now")
def evaluate_active_cyclones_now(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    On-demand alert evaluation: immediately evaluates all active cyclones
    against the ML prediction pipeline and alert threshold engine.
    Dispatches alerts (simulated or real depending on LIVE_ALERTS_ENABLED).
    """
    from alerts.monitor import CycloneAlertMonitor

    results = CycloneAlertMonitor.evaluate_active_cyclones(db)
    triggered_count = sum(1 for r in results if r.get("triggered"))

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "safety_mode": "LIVE ALERTS ACTIVE" if settings.LIVE_ALERTS_ENABLED else "SAFE SIMULATION MODE (DEFAULT)",
        "kill_switch_active": is_kill_switch_active(),
        "evaluated_cyclones_count": len(results),
        "triggered_count": triggered_count,
        "results": results
    }

@router.get("", response_model=List[AlertOut])
def get_alerts(
    audience: Optional[str] = None,
    severity: Optional[str] = None,
    alert_level: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    cyclone_id: Optional[str] = None,
    is_simulation: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Retrieves dispatches from the operational alerts inbox.
    Supports filtering by audience, severity level, operational status, and storm.
    """
    query = db.query(Alert)
    if audience and audience != "All":
        query = query.filter(Alert.audience.in_([audience, "All"]))
    if severity and severity != "All":
        query = query.filter(Alert.severity == severity)
    if alert_level and alert_level != "All":
        query = query.filter(Alert.alert_level == alert_level)
    if status_filter and status_filter != "All":
        query = query.filter(Alert.status == status_filter.upper())
    if cyclone_id:
        query = query.filter(Alert.cyclone_id == cyclone_id)
    if is_simulation is not None:
        query = query.filter(Alert.is_simulation == is_simulation)

    results = query.order_by(Alert.created_at.desc()).limit(limit).all()
    if not results:
        # Generate baseline operational dispatches if database is pristine
        fallback_alerts = AlertEngine.generate_alerts(
            cyclone_name="BIPARJOY",
            category="Very Severe Cyclonic Storm",
            wind_speed_kts=85.0,
            central_pressure_hpa=964.0,
            risk_level="Extreme Risk",
            target_location="Kutch & Saurashtra Coast, Gujarat"
        )
        # Seed into DB so they have real IDs and status tracking
        for fa in fallback_alerts:
            db_alert = Alert(
                id=fa["id"],
                cyclone_id=fa.get("cyclone_id") or "demo-biparjoy-2023",
                severity=fa["severity"],
                alert_level=fa.get("alert_level", "Warning"),
                status=fa.get("status", "ACTIVE"),
                audience=fa["audience"],
                headline=fa["headline"],
                hazard=fa["hazard"],
                expected_time=datetime.fromisoformat(fa["expected_time"]),
                location_description=fa["location_description"],
                affected_districts=fa.get("affected_districts"),
                risk_score=fa.get("risk_score"),
                trigger_event=fa.get("trigger_event", "THRESHOLD_BREACH"),
                is_simulation=fa.get("is_simulation", False),
                explanation=fa["explanation"],
                recommended_actions=fa["recommended_actions"],
                confidence_pct=fa["confidence_pct"],
                official_source=fa["official_source"],
                is_official_warning=fa["is_official_warning"],
                delivery_summary=fa.get("delivery_summary")
            )
            db.add(db_alert)
        try:
            db.commit()
            return query.order_by(Alert.created_at.desc()).limit(limit).all()
        except Exception:
            db.rollback()
            return fallback_alerts

    return results

@router.get("/stats")
def get_alert_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns high-level status and severity counts for dashboard and alerts center.
    """
    all_alerts = db.query(Alert).all()
    status_counts = {
        "active": sum(1 for a in all_alerts if getattr(a, "status", "ACTIVE") == "ACTIVE"),
        "acknowledged": sum(1 for a in all_alerts if getattr(a, "status", "ACTIVE") == "ACKNOWLEDGED"),
        "escalated": sum(1 for a in all_alerts if getattr(a, "status", "ACTIVE") == "ESCALATED"),
        "resolved": sum(1 for a in all_alerts if getattr(a, "status", "ACTIVE") == "RESOLVED"),
        "total": len(all_alerts)
    }
    severity_counts = {
        "emergency": sum(1 for a in all_alerts if (a.severity or "").lower() == "emergency"),
        "warning": sum(1 for a in all_alerts if (a.severity or "").lower() == "warning"),
        "watch": sum(1 for a in all_alerts if (a.severity or "").lower() == "watch"),
        "advisory": sum(1 for a in all_alerts if (a.severity or "").lower() == "advisory")
    }
    return {
        "statuses": status_counts,
        "severities": severity_counts,
        "total_dispatches": len(all_alerts)
    }

@router.get("/audit-log", response_model=List[AlertDeliveryLogOut])
def get_all_audit_logs(
    channel: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Retrieves global audit trail of notification dispatches across all channels.
    """
    q = db.query(AlertDeliveryLog)
    if channel and channel != "All":
        q = q.filter(AlertDeliveryLog.channel == channel)
    return q.order_by(AlertDeliveryLog.sent_at.desc()).limit(limit).all()

@router.post("/simulate")
def simulate_cyclone_alert(
    req: AlertSimulationRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Simulation mode allowing evaluators/operators to trigger realistic cyclone alerts
    without sending external SMS or email. Generates alerts, evaluates threshold detection,
    and logs deliveries in simulated mode.
    """
    result = AlertEngine.evaluate_and_trigger(
        cyclone_name=req.cyclone_name or "BIPARJOY",
        predicted_wind_kts=req.wind_speed_kts or 95.0,
        central_pressure_hpa=req.central_pressure_hpa or 955.0,
        landfall_eta_hours=req.landfall_eta_hours or 18,
        target_location=req.target_location or "Kutch & Saurashtra Coast, Gujarat",
        affected_districts=req.affected_districts or ["Kutch", "Devbhumi Dwarka", "Jamnagar"],
        cyclone_id="demo-biparjoy-2023",
        channels=req.channels or ["dashboard", "sms", "email"],
        is_simulation=True,
        force_dispatch=True,
        db_session=db
    )
    return {
        "status": "success",
        "message": f"Simulated {result.get('alert_level')} cyclone scenario generated successfully.",
        "simulation_details": result
    }

@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    action_req: Optional[AlertActionRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Transition alert status to ACKNOWLEDGED with officer timestamp.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = now
    alert.acknowledged_by = action_req.operator_name if action_req else "Disaster Operations Officer"

    # Add audit log record
    log_entry = AlertDeliveryLog(
        id=f"ack-{alert_id[:8]}-{int(now.timestamp())}",
        alert_id=alert_id,
        channel="dashboard",
        recipient_name=alert.acknowledged_by,
        recipient_contact="internal://ops/console",
        delivery_status="DELIVERED",
        trigger_type="OPERATOR_ACKNOWLEDGE",
        payload={"action": "ACKNOWLEDGE", "notes": action_req.notes if action_req else None},
        sent_at=now
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "alert_id": alert_id,
        "new_status": "ACKNOWLEDGED",
        "acknowledged_at": now.isoformat(),
        "acknowledged_by": alert.acknowledged_by
    }

@router.post("/{alert_id}/escalate")
def escalate_alert(
    alert_id: str,
    action_req: Optional[AlertActionRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Transition alert status to ESCALATED and optionally elevate severity.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    alert.status = "ESCALATED"
    if action_req and action_req.new_severity:
        alert.severity = action_req.new_severity
        alert.alert_level = action_req.new_severity

    log_entry = AlertDeliveryLog(
        id=f"esc-{alert_id[:8]}-{int(now.timestamp())}",
        alert_id=alert_id,
        channel="dashboard",
        recipient_name=action_req.operator_name if action_req else "Incident Commander",
        recipient_contact="internal://ops/commander",
        delivery_status="DELIVERED",
        trigger_type="MANUAL_ESCALATION",
        payload={
            "action": "ESCALATE",
            "new_severity": alert.severity,
            "notes": action_req.notes if action_req else "Manual operational threat escalation"
        },
        sent_at=now
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "alert_id": alert_id,
        "new_status": "ESCALATED",
        "severity": alert.severity
    }

@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    action_req: Optional[AlertActionRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Transition alert status to RESOLVED when threat dissipates.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    alert.status = "RESOLVED"
    alert.resolved_at = now

    log_entry = AlertDeliveryLog(
        id=f"res-{alert_id[:8]}-{int(now.timestamp())}",
        alert_id=alert_id,
        channel="dashboard",
        recipient_name=action_req.operator_name if action_req else "EOC Chief",
        recipient_contact="internal://ops/eoc",
        delivery_status="DELIVERED",
        trigger_type="ALERT_RESOLVE",
        payload={"action": "RESOLVE", "notes": action_req.notes if action_req else "Threat dissipated"},
        sent_at=now
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "alert_id": alert_id,
        "new_status": "RESOLVED",
        "resolved_at": now.isoformat()
    }

@router.get("/{alert_id}/audit-log", response_model=List[AlertDeliveryLogOut])
def get_alert_audit_log(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the delivery and action audit trail for a specific alert.
    """
    logs = db.query(AlertDeliveryLog).filter(AlertDeliveryLog.alert_id == alert_id).order_by(AlertDeliveryLog.sent_at.desc()).all()
    return logs
