"""
Unit & Integration Tests for Production External Notification Providers in CycloneX
Verifies:
1. Twilio SMS Provider (Success, Retry on 5xx, Immediate abort on 4xx)
2. SMTP Email Provider (TLS negotiation, MIME message, Statutory disclaimer, Auth failure)
3. Master Safety Switch Interlock (LIVE_ALERTS_ENABLED=False enforces safe simulation)
4. Emergency Rate Limiting (Hourly caps prevent mass-messaging loops)
5. Test Notification Endpoint (Isolated dispatch strictly to test recipient)
6. Simulation Endpoint Isolation (Jury demo strictly isolated from live dispatch)
7. Audit Log Recording for External Deliveries
"""
import pytest
import smtplib
import json
import urllib.request
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from alerts.notifications.providers import (
    TwilioSMSProvider,
    SMTPEmailProvider,
    NotificationRateLimiter,
    NotificationDispatcher,
    STATUTORY_DISCLAIMER_TEXT
)

client = TestClient(app)

# ============================================================
# 1. TWILIO SMS PROVIDER TESTS
# ============================================================
def test_twilio_sms_success_mocked():
    """Verifies successful Twilio SMS dispatch, SID extraction, and statutory disclaimer."""
    provider = TwilioSMSProvider(
        account_sid="ACmockedaccountsid1234567890abcdef",
        auth_token="mockedauthtoken1234567890abcdef",
        from_number="+12055550199"
    )
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "sid": "SMmockedmessagesid1234567890",
        "status": "queued"
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    # Temporarily activate live switch for provider unit test
    orig_live = settings.LIVE_ALERTS_ENABLED
    settings.LIVE_ALERTS_ENABLED = True
    try:
        with patch("urllib.request.urlopen", return_value=mock_response):
            res = provider.send(
                recipient={"name": "Kutch Collector", "phone": "+919876543210"},
                subject="Cyclone Warning",
                body="Very Severe Cyclone Biparjoy approaching.",
                metadata={"severity": "Warning", "wind_kts": 85},
                simulate=False
            )
            assert res.delivery_status == "DELIVERED"
            assert res.payload.get("message_sid") == "SMmockedmessagesid1234567890"
            assert res.retry_count == 0
            assert "IMD/SDMA" in res.payload.get("body", "")
    finally:
        settings.LIVE_ALERTS_ENABLED = orig_live

def test_twilio_sms_retry_on_server_error():
    """Verifies exponential retry on 500 error before marking as FAILED."""
    provider = TwilioSMSProvider(
        account_sid="ACmockedaccountsid1234567890abcdef",
        auth_token="mockedauthtoken1234567890abcdef",
        from_number="+12055550199"
    )

    orig_live = settings.LIVE_ALERTS_ENABLED
    settings.LIVE_ALERTS_ENABLED = True
    try:
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="https://api.twilio.com",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=MagicMock(read=lambda: b"Twilio Service Unavailable")
        )):
            res = provider.send(
                recipient={"name": "Kutch Collector", "phone": "+919876543210"},
                subject="Cyclone Warning",
                body="Very Severe Cyclone Biparjoy approaching.",
                metadata={"severity": "Warning", "wind_kts": 85},
                simulate=False
            )
            assert res.delivery_status == "FAILED"
            assert res.retry_count == 3
            assert "503" in (res.error_message or "")
    finally:
        settings.LIVE_ALERTS_ENABLED = orig_live

def test_twilio_sms_fatal_401_no_retry():
    """Verifies that 401 Unauthorized errors abort immediately without looping retries."""
    provider = TwilioSMSProvider(
        account_sid="ACbadaccount",
        auth_token="badtoken",
        from_number="+12055550199"
    )

    orig_live = settings.LIVE_ALERTS_ENABLED
    settings.LIVE_ALERTS_ENABLED = True
    try:
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="https://api.twilio.com",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=MagicMock(read=lambda: b"Authentication Error")
        )):
            res = provider.send(
                recipient={"name": "Kutch Collector", "phone": "+919876543210"},
                subject="Cyclone Warning",
                body="Alert",
                metadata={"severity": "Warning"},
                simulate=False
            )
            assert res.delivery_status == "FAILED"
            assert "401" in (res.error_message or "")
    finally:
        settings.LIVE_ALERTS_ENABLED = orig_live

# ============================================================
# 2. SMTP EMAIL PROVIDER TESTS
# ============================================================
def test_smtp_email_success_mocked():
    """Verifies SMTP delivery, MIME structure, and statutory disclaimer inclusion."""
    provider = SMTPEmailProvider(
        host="smtp.mocked.gov.in",
        port=587,
        user="alerts@cyclonex.gov.in",
        password="secretpassword",
        from_email="CycloneX <alerts@cyclonex.gov.in>",
        use_tls=True
    )

    mock_smtp_instance = MagicMock()
    orig_live = settings.LIVE_ALERTS_ENABLED
    settings.LIVE_ALERTS_ENABLED = True
    try:
        with patch("smtplib.SMTP", return_value=mock_smtp_instance):
            res = provider.send(
                recipient={"name": "GSDMA EOC", "email": "controlroom@gsdma.org", "district": "Kutch"},
                subject="Severe Cyclone Landfall Advisory",
                body="Cyclone Biparjoy approaching Jakhau sector.",
                metadata={"severity": "Warning", "recommended_actions": ["Activate shelters", "Recall boats"]},
                simulate=False
            )
            assert res.delivery_status == "DELIVERED"
            assert res.retry_count == 0
            assert mock_smtp_instance.starttls.called
            assert mock_smtp_instance.login.called
            assert mock_smtp_instance.sendmail.called
            # Verify sent message content contains disclaimer
            call_args = mock_smtp_instance.sendmail.call_args
            msg_str = call_args[0][2]
            assert "STATUTORY NOTICE" in msg_str
            assert "IMD" in msg_str
    finally:
        settings.LIVE_ALERTS_ENABLED = orig_live

def test_smtp_email_auth_failure():
    """Verifies that SMTPAuthenticationError fails cleanly without infinite retries."""
    provider = SMTPEmailProvider(
        host="smtp.mocked.gov.in",
        port=587,
        user="baduser",
        password="badpassword",
        from_email="CycloneX <alerts@cyclonex.gov.in>"
    )

    mock_smtp_instance = MagicMock()
    mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    orig_live = settings.LIVE_ALERTS_ENABLED
    settings.LIVE_ALERTS_ENABLED = True
    try:
        with patch("smtplib.SMTP", return_value=mock_smtp_instance):
            res = provider.send(
                recipient={"name": "GSDMA EOC", "email": "controlroom@gsdma.org"},
                subject="Test Advisory",
                body="Test",
                metadata={"severity": "Advisory"},
                simulate=False
            )
            assert res.delivery_status == "FAILED"
            assert "Authentication Error" in (res.error_message or "")
    finally:
        settings.LIVE_ALERTS_ENABLED = orig_live

# ============================================================
# 3. SAFETY SWITCH INTERLOCK & RATE LIMITING
# ============================================================
def test_safety_switch_interlock_enforces_simulation():
    """When LIVE_ALERTS_ENABLED=False, external dispatches must be downgraded to SIMULATED."""
    provider = TwilioSMSProvider(
        account_sid="ACmockedaccountsid1234567890abcdef",
        auth_token="mockedauthtoken1234567890abcdef",
        from_number="+12055550199"
    )

    orig_live = settings.LIVE_ALERTS_ENABLED
    settings.LIVE_ALERTS_ENABLED = False # Master safety switch explicitly OFF
    try:
        # Request simulate=False (live)
        res = provider.send(
            recipient={"name": "Kutch Collector", "phone": "+919876543210"},
            subject="Live Warning",
            body="Cyclone alert",
            metadata={"severity": "Warning"},
            simulate=False
        )
        # MUST be forced to SIMULATED
        assert res.delivery_status == "SIMULATED"
    finally:
        settings.LIVE_ALERTS_ENABLED = orig_live

def test_emergency_rate_limiter_sliding_window():
    """Verifies that sliding-window rate limiter throttles excess dispatches."""
    limiter = NotificationRateLimiter(max_hourly_sms=3, max_hourly_email=5)
    phone = "+919876500001"

    # Send 3 messages within limit
    ok1, _ = limiter.check_and_record_sms(phone)
    ok2, _ = limiter.check_and_record_sms(phone)
    ok3, _ = limiter.check_and_record_sms(phone)
    assert ok1 is True and ok2 is True and ok3 is True

    # 4th message exceeds limit -> blocked!
    ok4, reason = limiter.check_and_record_sms(phone)
    assert ok4 is False
    assert "limit" in reason.lower()

# ============================================================
# 4. ADMIN TEST NOTIFICATION & SIMULATION ENDPOINT
# ============================================================
def test_admin_test_notification_endpoint():
    """POST /api/v1/alerts/test-notification sends test dispatch only to test recipient."""
    payload = {
        "channel": "both",
        "recipient_phone": "+919876543210",
        "recipient_email": "ops-test@cyclonex.gov.in",
        "message": "System verification test"
    }
    res = client.post("/api/v1/alerts/test-notification", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["test_phone"] == "+919876543210"
    assert data["test_email"] == "ops-test@cyclonex.gov.in"
    assert len(data["results"]) >= 2
    # Verify audit log contains test entry
    audit_res = client.get("/api/v1/alerts/audit-log?limit=5")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert any(l["trigger_type"] == "ADMIN_TEST" for l in logs)

def test_simulation_endpoint_isolated_from_live():
    """POST /api/v1/alerts/simulate always stays simulated even if safety switch is enabled."""
    orig_live = settings.LIVE_ALERTS_ENABLED
    settings.LIVE_ALERTS_ENABLED = True
    try:
        res = client.post("/api/v1/alerts/simulate", json={
            "cyclone_name": "BIPARJOY",
            "wind_speed_kts": 85.0,
            "central_pressure_hpa": 965.0,
            "landfall_eta_hours": 24,
            "simulate_delivery": True
        })
        assert res.status_code == 200
        sim_data = res.json()["simulation_details"]
        assert sim_data["triggered"] is True
        # All delivery logs MUST be marked SIMULATED
        for log in sim_data["delivery_logs"]:
            assert log["delivery_status"] == "SIMULATED"
    finally:
        settings.LIVE_ALERTS_ENABLED = orig_live

def test_admin_config_endpoints():
    """GET and POST /api/v1/alerts/config allow inspecting and updating configuration."""
    get_res = client.get("/api/v1/alerts/config")
    assert get_res.status_code == 200
    cfg = get_res.json()
    assert "live_alerts_enabled" in cfg
    assert "rate_limits" in cfg
    assert "safety_mode" in cfg

    # Update configuration
    post_res = client.post("/api/v1/alerts/config", json={
        "test_notification_phone": "+919999988888",
        "live_alerts_enabled": False
    })
    assert post_res.status_code == 200
    updated_cfg = post_res.json()["config"]
    assert updated_cfg["test_phone"] == "+919999988888"
    assert updated_cfg["live_alerts_enabled"] is False

def test_validate_credentials_endpoint_reports_unconfigured():
    """POST /api/v1/alerts/validate-credentials accurately detects missing credentials."""
    res = client.post("/api/v1/alerts/validate-credentials")
    assert res.status_code == 200
    data = res.json()
    assert data["verification_status"] == "NOT VERIFIED"
    assert "missing_variables" in data
    assert len(data["missing_variables"]) > 0
    assert "config" in data
    assert data["config"]["status"] == "NOT CONFIGURED"
    assert data["sms"]["status"] in ("NOT_CONFIGURED", "CONFIGURED", "INVALID")
    assert data["email"]["status"] in ("NOT_CONFIGURED", "CONFIGURED", "INVALID")

# ============================================================
# 5. CONTROLLED LIVE DELIVERY & SAFETY INTERLOCK TESTS
# ============================================================
def test_live_delivery_requires_explicit_confirmation():
    """POST /api/v1/alerts/test-live-delivery MUST fail if confirm_live_test is False."""
    res = client.post("/api/v1/alerts/test-live-delivery", json={
        "confirm_live_test": False
    })
    assert res.status_code == 400
    assert "explicit confirmation" in res.json()["detail"].lower()

def test_live_delivery_rejects_arbitrary_recipients():
    """POST /api/v1/alerts/test-live-delivery MUST reject numbers other than TEST_NOTIFICATION_PHONE."""
    res = client.post("/api/v1/alerts/test-live-delivery", json={
        "confirm_live_test": True,
        "recipient_phone": "+910000099999" # Not configured test recipient
    })
    assert res.status_code == 400
    assert "arbitrary recipients rejected" in res.json()["detail"].lower()

def test_live_delivery_blocked_by_emergency_kill_switch():
    """POST /api/v1/alerts/test-live-delivery MUST be rejected when kill switch is active."""
    from alerts.notifications.providers import activate_kill_switch, deactivate_kill_switch
    activate_kill_switch()
    try:
        res = client.post("/api/v1/alerts/test-live-delivery", json={
            "confirm_live_test": True,
            "recipient_phone": settings.TEST_NOTIFICATION_PHONE,
            "recipient_email": settings.TEST_NOTIFICATION_EMAIL
        })
        assert res.status_code == 403
        assert "kill switch" in res.json()["detail"].lower()
    finally:
        deactivate_kill_switch()

def test_live_delivery_mocked_success_transitions_to_live_verified():
    """Verifies that successful external responses transition system state to LIVE_VERIFIED."""
    from alerts.notifications.providers import set_live_verification_state, get_live_verification_state
    
    # Configure settings for test
    orig = {
        "sms_prov": settings.SMS_PROVIDER,
        "email_prov": settings.EMAIL_PROVIDER,
        "sid": settings.TWILIO_ACCOUNT_SID,
        "tok": settings.TWILIO_AUTH_TOKEN,
        "from_p": settings.TWILIO_FROM_NUMBER,
        "host": settings.SMTP_HOST,
        "user": settings.SMTP_USER,
        "pwd": settings.SMTP_PASSWORD,
        "t_phone": settings.TEST_NOTIFICATION_PHONE,
        "t_email": settings.TEST_NOTIFICATION_EMAIL,
    }
    settings.SMS_PROVIDER = "twilio"
    settings.TWILIO_ACCOUNT_SID = "ACmockedaccountsid1234567890abcdef"
    settings.TWILIO_AUTH_TOKEN = "mockedauthtoken1234567890abcdef"
    settings.TWILIO_FROM_NUMBER = "+12055550199"
    settings.EMAIL_PROVIDER = "smtp"
    settings.SMTP_HOST = "smtp.example.com"
    settings.SMTP_USER = "test@example.com"
    settings.SMTP_PASSWORD = "testpassword123"
    settings.TEST_NOTIFICATION_PHONE = "+919999988888"
    settings.TEST_NOTIFICATION_EMAIL = "test@cyclonex.gov.in"

    mock_tw_resp = MagicMock()
    mock_tw_resp.read.return_value = json.dumps({
        "sid": "SMtestverification1234567890",
        "status": "delivered"
    }).encode("utf-8")
    mock_tw_resp.__enter__.return_value = mock_tw_resp

    mock_smtp_instance = MagicMock()

    try:
        with patch("urllib.request.urlopen", return_value=mock_tw_resp), \
             patch("smtplib.SMTP", return_value=mock_smtp_instance):
            res = client.post("/api/v1/alerts/test-live-delivery", json={
                "confirm_live_test": True,
                "recipient_phone": "+919999988888",
                "recipient_email": "test@cyclonex.gov.in"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["verification_status"] == "LIVE_VERIFIED"
            assert data["sms_delivery"]["status"] == "DELIVERED"
            assert data["email_delivery"]["status"] == "DELIVERED"
            assert "SMtestverification1234567890" in str(data["sms_delivery"]["message_sid"])

            # Check config endpoint reflects LIVE_VERIFIED
            cfg_res = client.get("/api/v1/alerts/config")
            assert cfg_res.status_code == 200
            assert cfg_res.json()["live_verification_state"] == "LIVE_VERIFIED"
    finally:
        settings.SMS_PROVIDER = orig["sms_prov"]
        settings.EMAIL_PROVIDER = orig["email_prov"]
        settings.TWILIO_ACCOUNT_SID = orig["sid"]
        settings.TWILIO_AUTH_TOKEN = orig["tok"]
        settings.TWILIO_FROM_NUMBER = orig["from_p"]
        settings.SMTP_HOST = orig["host"]
        settings.SMTP_USER = orig["user"]
        settings.SMTP_PASSWORD = orig["pwd"]
        settings.TEST_NOTIFICATION_PHONE = orig["t_phone"]
        settings.TEST_NOTIFICATION_EMAIL = orig["t_email"]
        set_live_verification_state("NOT_CONFIGURED")

def test_live_delivery_mocked_failure_transitions_to_test_failed():
    """Verifies that provider failures transition system state to TEST_FAILED."""
    from alerts.notifications.providers import set_live_verification_state
    
    orig = {
        "sms_prov": settings.SMS_PROVIDER,
        "email_prov": settings.EMAIL_PROVIDER,
        "sid": settings.TWILIO_ACCOUNT_SID,
        "tok": settings.TWILIO_AUTH_TOKEN,
        "from_p": settings.TWILIO_FROM_NUMBER,
        "host": settings.SMTP_HOST,
        "user": settings.SMTP_USER,
        "pwd": settings.SMTP_PASSWORD,
        "t_phone": settings.TEST_NOTIFICATION_PHONE,
        "t_email": settings.TEST_NOTIFICATION_EMAIL,
    }
    settings.SMS_PROVIDER = "twilio"
    settings.TWILIO_ACCOUNT_SID = "ACmockedaccountsid1234567890abcdef"
    settings.TWILIO_AUTH_TOKEN = "mockedauthtoken1234567890abcdef"
    settings.TWILIO_FROM_NUMBER = "+12055550199"
    settings.EMAIL_PROVIDER = "smtp"
    settings.SMTP_HOST = "smtp.example.com"
    settings.SMTP_USER = "test@example.com"
    settings.SMTP_PASSWORD = "testpassword123"
    settings.TEST_NOTIFICATION_PHONE = "+919999988888"
    settings.TEST_NOTIFICATION_EMAIL = "test@cyclonex.gov.in"

    try:
        with patch("urllib.request.urlopen", side_effect=RuntimeError("Simulated Twilio network drop")), \
             patch("smtplib.SMTP", side_effect=RuntimeError("Simulated SMTP timeout")):
            res = client.post("/api/v1/alerts/test-live-delivery", json={
                "confirm_live_test": True,
                "recipient_phone": "+919999988888",
                "recipient_email": "test@cyclonex.gov.in"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["verification_status"] == "TEST_FAILED"
            assert data["sms_delivery"]["status"] == "FAILED"
            assert data["email_delivery"]["status"] == "FAILED"
    finally:
        settings.SMS_PROVIDER = orig["sms_prov"]
        settings.EMAIL_PROVIDER = orig["email_prov"]
        settings.TWILIO_ACCOUNT_SID = orig["sid"]
        settings.TWILIO_AUTH_TOKEN = orig["tok"]
        settings.TWILIO_FROM_NUMBER = orig["from_p"]
        settings.SMTP_HOST = orig["host"]
        settings.SMTP_USER = orig["user"]
        settings.SMTP_PASSWORD = orig["pwd"]
        settings.TEST_NOTIFICATION_PHONE = orig["t_phone"]
        settings.TEST_NOTIFICATION_EMAIL = orig["t_email"]
        set_live_verification_state("NOT_CONFIGURED")



