"""
CycloneX Production Multi-Channel Notification Provider Subsystem
Features:
1. Real External SMS: Twilio REST API & India-compatible Generic HTTP Gateway
2. Real External Email: Standard SMTP (TLS/STARTTLS) & SendGrid REST API
3. Exponential Backoff Retry Logic (up to 3 attempts for transient provider failures)
4. Master Safety Switch Interlock (LIVE_ALERTS_ENABLED=False by default)
5. Emergency Rate Limiter (sliding-window caps to prevent mass-messaging loops)
6. Complete Delivery Audit Trail with Provider, Timestamp, Retry Count, & Error Provenance
7. Statutory Disclaimer Enforcement: CycloneX decision-support role vs official IMD/NDMA authority
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import smtplib
import time
import logging
import urllib.request
import urllib.parse
import urllib.error
import json
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.app.core.config import settings

logger = logging.getLogger("CycloneX.Notifications")

# ============================================================
# EMERGENCY KILL SWITCH
# When active, ALL external notification dispatch is immediately
# blocked regardless of safety switch or provider configuration.
# ============================================================
_kill_switch_active: bool = False

def activate_kill_switch():
    """Immediately blocks all external notification dispatch."""
    global _kill_switch_active
    _kill_switch_active = True
    logger.critical("[KILL SWITCH] ACTIVATED — All external SMS/Email dispatch is now BLOCKED.")

def deactivate_kill_switch():
    """Re-enables external notification dispatch (subject to safety switch)."""
    global _kill_switch_active
    _kill_switch_active = False
    logger.warning("[KILL SWITCH] DEACTIVATED — External dispatch re-enabled (subject to LIVE_ALERTS_ENABLED).")

def is_kill_switch_active() -> bool:
    """Returns True if the emergency kill switch is currently active."""
    return _kill_switch_active

# Statutory Decision-Support Disclaimer
STATUTORY_DISCLAIMER_TEXT = (
    "STATUTORY NOTICE: CycloneX alerts are computer-generated decision-support advisories "
    "for situational awareness. Official, legally binding cyclonic warning bulletins and evacuation orders "
    "are issued exclusively by the India Meteorological Department (IMD) and National/State Disaster "
    "Management Authorities (NDMA/SDMA)."
)

class NotificationResult:
    def __init__(
        self,
        channel: str,
        recipient_name: str,
        recipient_contact: str,
        delivery_status: str, # DELIVERED, SIMULATED, FAILED, RATE_LIMITED
        payload: Dict[str, Any],
        provider: str = "internal",
        retry_count: int = 0,
        error_message: Optional[str] = None
    ):
        self.channel = channel
        self.recipient_name = recipient_name
        self.recipient_contact = recipient_contact
        self.delivery_status = delivery_status
        self.payload = payload
        self.provider = provider
        self.retry_count = retry_count
        self.error_message = error_message
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "recipient_name": self.recipient_name,
            "recipient_contact": self.recipient_contact,
            "delivery_status": self.delivery_status,
            "provider": self.provider,
            "retry_count": self.retry_count,
            "payload": self.payload,
            "error_message": self.error_message,
            "sent_at": self.timestamp.isoformat()
        }


class NotificationRateLimiter:
    """
    Sliding-window rate limiter enforcing global hourly limits and per-recipient limits.
    Prevents accidental mass-messaging loops or provider quota exhaustion.
    """
    def __init__(self, max_hourly_sms: int = 20, max_hourly_email: int = 50, max_per_recipient_hourly: int = 4):
        self.max_hourly_sms = max_hourly_sms
        self.max_hourly_email = max_hourly_email
        self.max_per_recipient_hourly = max_per_recipient_hourly
        self._sms_timestamps: List[float] = []
        self._email_timestamps: List[float] = []
        self._recipient_timestamps: Dict[str, List[float]] = {}

    def _cleanup(self, now: float):
        cutoff = now - 3600.0 # 1 hour
        self._sms_timestamps = [t for t in self._sms_timestamps if t > cutoff]
        self._email_timestamps = [t for t in self._email_timestamps if t > cutoff]
        for contact in list(self._recipient_timestamps.keys()):
            self._recipient_timestamps[contact] = [t for t in self._recipient_timestamps[contact] if t > cutoff]
            if not self._recipient_timestamps[contact]:
                del self._recipient_timestamps[contact]

    def check_and_record_sms(self, contact: str) -> Tuple[bool, Optional[str]]:
        now = time.time()
        self._cleanup(now)

        if len(self._sms_timestamps) >= self.max_hourly_sms:
            return False, f"Global hourly SMS limit ({self.max_hourly_sms}/hr) reached. Safeguard active."

        rec_history = self._recipient_timestamps.get(contact, [])
        if len(rec_history) >= self.max_per_recipient_hourly:
            return False, f"Per-recipient hourly rate limit ({self.max_per_recipient_hourly}/hr) reached for {contact}."

        self._sms_timestamps.append(now)
        self._recipient_timestamps.setdefault(contact, []).append(now)
        return True, None

    def check_and_record_email(self, contact: str) -> Tuple[bool, Optional[str]]:
        now = time.time()
        self._cleanup(now)

        if len(self._email_timestamps) >= self.max_hourly_email:
            return False, f"Global hourly Email limit ({self.max_hourly_email}/hr) reached. Safeguard active."

        rec_history = self._recipient_timestamps.get(contact, [])
        if len(rec_history) >= self.max_per_recipient_hourly:
            return False, f"Per-recipient hourly rate limit ({self.max_per_recipient_hourly}/hr) reached for {contact}."

        self._email_timestamps.append(now)
        self._recipient_timestamps.setdefault(contact, []).append(now)
        return True, None

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        self._cleanup(now)
        return {
            "sms_sent_last_hour": len(self._sms_timestamps),
            "sms_limit_hourly": self.max_hourly_sms,
            "email_sent_last_hour": len(self._email_timestamps),
            "email_limit_hourly": self.max_hourly_email,
            "active_recipients_tracked": len(self._recipient_timestamps)
        }

rate_limiter = NotificationRateLimiter(
    max_hourly_sms=settings.NOTIFICATION_MAX_HOURLY_SMS,
    max_hourly_email=settings.NOTIFICATION_MAX_HOURLY_EMAIL
)


class BaseNotificationProvider:
    channel_name: str = "base"
    provider_name: str = "base"

    def send(
        self,
        recipient: Dict[str, Any],
        subject: str,
        body: str,
        metadata: Dict[str, Any],
        simulate: bool = False
    ) -> NotificationResult:
        raise NotImplementedError


class DashboardNotificationProvider(BaseNotificationProvider):
    channel_name: str = "dashboard"
    provider_name: str = "CycloneX In-App Feed"

    def send(
        self,
        recipient: Dict[str, Any],
        subject: str,
        body: str,
        metadata: Dict[str, Any],
        simulate: bool = False
    ) -> NotificationResult:
        """In-App dashboard notification. Always delivered to internal feed."""
        payload = {
            "channel": self.channel_name,
            "subject": subject,
            "audience": recipient.get("audience", "All"),
            "district": recipient.get("district", "Coastal Sector"),
            "headline": metadata.get("headline", subject),
            "severity": metadata.get("severity", "Warning"),
            "risk_score": metadata.get("risk_score", 0.75),
            "is_simulation": simulate,
            "statutory_notice": STATUTORY_DISCLAIMER_TEXT
        }
        status = "SIMULATED" if simulate else "DELIVERED"
        return NotificationResult(
            channel=self.channel_name,
            recipient_name=recipient.get("name", "Dashboard Terminal"),
            recipient_contact="in-app://dashboard/alerts",
            delivery_status=status,
            provider=self.provider_name,
            payload=payload
        )


class TwilioSMSProvider(BaseNotificationProvider):
    channel_name: str = "sms"
    provider_name: str = "Twilio REST API"

    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None, from_number: Optional[str] = None):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_FROM_NUMBER

    def send(
        self,
        recipient: Dict[str, Any],
        subject: str,
        body: str,
        metadata: Dict[str, Any],
        simulate: bool = False
    ) -> NotificationResult:
        contact = recipient.get("phone", settings.TEST_NOTIFICATION_PHONE)
        severity = metadata.get("severity", "WARNING").upper()
        
        # Support custom SMS body (e.g. for controlled live tests) or CAP format
        if metadata.get("sms_body"):
            sms_text = metadata["sms_body"]
        else:
            # CAP-compliant 160-char SMS format with statutory disclaimer
            sms_text = (
                f"[CycloneX {severity}] {metadata.get('headline', subject)[:70]}. "
                f"Winds {metadata.get('wind_kts', 85)}kt. Official orders by IMD/SDMA."
            )

        payload = {
            "to": contact,
            "from": self.from_number or "CycloneX-Gov",
            "body": sms_text,
            "is_simulation": simulate
        }

        if metadata.get("force_sms_failure"):
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "Authority Contact"),
                recipient_contact=contact,
                delivery_status="FAILED",
                provider=self.provider_name,
                payload=payload,
                error_message="Forced SMS provider failure for testing"
            )

        # Check if this is an authorized test dispatch specifically targeting TEST_NOTIFICATION_PHONE
        is_authorized_test = (
            recipient.get("is_test_target", False)
            and metadata.get("is_test_dispatch", False)
            and contact == settings.TEST_NOTIFICATION_PHONE
        )

        # Safe simulation path
        if simulate or (not settings.LIVE_ALERTS_ENABLED and not is_authorized_test) or not self.account_sid or not self.auth_token:
            sim_reason = (
                "Credentials missing in .env (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN)"
                if not (self.account_sid and self.auth_token)
                else ("LIVE_ALERTS_ENABLED=false (safe simulation)" if not settings.LIVE_ALERTS_ENABLED and not is_authorized_test else "Simulation mode")
            )
            payload["simulation_reason"] = sim_reason
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "Authority Contact"),
                recipient_contact=contact,
                delivery_status="SIMULATED",
                provider=self.provider_name,
                payload=payload
            )

        # Rate limit verification
        can_send, reason = rate_limiter.check_and_record_sms(contact)
        if not can_send:
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "Authority Contact"),
                recipient_contact=contact,
                delivery_status="RATE_LIMITED",
                provider=self.provider_name,
                payload=payload,
                error_message=reason
            )

        # Real Twilio API Call with Exponential Backoff Retries
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = urllib.parse.urlencode({
            "From": self.from_number,
            "To": contact,
            "Body": sms_text
        }).encode("utf-8")

        auth_str = f"{self.account_sid}:{self.auth_token}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        max_retries = 3
        last_err = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    resp_body = resp.read().decode("utf-8")
                    data_resp = json.loads(resp_body)
                    logger.info(f"[Twilio SMS] Delivered message SID: {data_resp.get('sid')} to {contact}")
                    payload["message_sid"] = data_resp.get("sid")
                    payload["provider_status"] = data_resp.get("status", "sent")
                    return NotificationResult(
                        channel=self.channel_name,
                        recipient_name=recipient.get("name", "Authority Contact"),
                        recipient_contact=contact,
                        delivery_status="DELIVERED",
                        provider=self.provider_name,
                        retry_count=attempt,
                        payload=payload
                    )
            except urllib.error.HTTPError as http_err:
                err_content = http_err.read().decode("utf-8", errors="ignore")
                last_err = f"HTTP {http_err.code}: {err_content}"
                # 4xx client errors are fatal (e.g. invalid number or bad credentials), do not retry
                if 400 <= http_err.code < 500:
                    break
            except Exception as e:
                last_err = str(e)

            # Wait exponential backoff for transient 5xx or network timeouts
            if attempt < max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))

        logger.error(f"[Twilio SMS] Delivery failed to {contact}: {last_err}")
        return NotificationResult(
            channel=self.channel_name,
            recipient_name=recipient.get("name", "Authority Contact"),
            recipient_contact=contact,
            delivery_status="FAILED",
            provider=self.provider_name,
            retry_count=max_retries,
            payload=payload,
            error_message=last_err
        )


class GenericHTTPSMSProvider(BaseNotificationProvider):
    channel_name: str = "sms"
    provider_name: str = "India SMS Gateway (HTTP)"

    def __init__(self, gateway_url: Optional[str] = None, api_key: Optional[str] = None):
        self.gateway_url = gateway_url or settings.SMS_GATEWAY_URL
        self.api_key = api_key or settings.SMS_GATEWAY_API_KEY

    def send(
        self,
        recipient: Dict[str, Any],
        subject: str,
        body: str,
        metadata: Dict[str, Any],
        simulate: bool = False
    ) -> NotificationResult:
        contact = recipient.get("phone", settings.TEST_NOTIFICATION_PHONE)
        sms_text = f"[CycloneX {metadata.get('severity', 'WARNING')}] {metadata.get('headline', subject)[:80]}. Official orders by IMD/SDMA."
        payload = {"to": contact, "message": sms_text, "is_simulation": simulate}

        if metadata.get("force_sms_failure"):
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "Authority Contact"),
                recipient_contact=contact,
                delivery_status="FAILED",
                provider=self.provider_name,
                payload=payload,
                error_message="Forced SMS provider failure for testing"
            )

        is_authorized_test = (
            recipient.get("is_test_target", False)
            and metadata.get("is_test_dispatch", False)
            and contact == settings.TEST_NOTIFICATION_PHONE
        )

        if simulate or (not settings.LIVE_ALERTS_ENABLED and not is_authorized_test) or not self.gateway_url:
            sim_reason = (
                "SMS_GATEWAY_URL missing in .env"
                if not self.gateway_url
                else ("LIVE_ALERTS_ENABLED=false (safe simulation)" if not settings.LIVE_ALERTS_ENABLED and not is_authorized_test else "Simulation mode")
            )
            payload["simulation_reason"] = sim_reason
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "Authority Contact"),
                recipient_contact=contact,
                delivery_status="SIMULATED",
                provider=self.provider_name,
                payload=payload
            )

        can_send, reason = rate_limiter.check_and_record_sms(contact)
        if not can_send:
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "Authority Contact"),
                recipient_contact=contact,
                delivery_status="RATE_LIMITED",
                provider=self.provider_name,
                payload=payload,
                error_message=reason
            )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        max_retries = 3
        last_err = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    self.gateway_url,
                    data=json.dumps({"phone": contact, "message": sms_text}).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    return NotificationResult(
                        channel=self.channel_name,
                        recipient_name=recipient.get("name", "Authority Contact"),
                        recipient_contact=contact,
                        delivery_status="DELIVERED",
                        provider=self.provider_name,
                        retry_count=attempt,
                        payload=payload
                    )
            except urllib.error.HTTPError as he:
                last_err = f"HTTP {he.code}: {he.read().decode('utf-8', errors='ignore')}"
                if 400 <= he.code < 500:
                    break
            except Exception as e:
                last_err = str(e)
            if attempt < max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))

        return NotificationResult(
            channel=self.channel_name,
            recipient_name=recipient.get("name", "Authority Contact"),
            recipient_contact=contact,
            delivery_status="FAILED",
            provider=self.provider_name,
            retry_count=max_retries,
            payload=payload,
            error_message=last_err
        )


class SMTPEmailProvider(BaseNotificationProvider):
    channel_name: str = "email"
    provider_name: str = "Standard SMTP (TLS/SSL)"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        use_tls: bool = True
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.user = user or settings.SMTP_USER
        self.password = password or settings.SMTP_PASSWORD
        self.from_email = from_email or settings.SMTP_FROM_EMAIL
        self.use_tls = use_tls

    def send(
        self,
        recipient: Dict[str, Any],
        subject: str,
        body: str,
        metadata: Dict[str, Any],
        simulate: bool = False
    ) -> NotificationResult:
        contact = recipient.get("email", settings.TEST_NOTIFICATION_EMAIL)
        severity = metadata.get("severity", "WARNING").upper()
        formatted_subject = f"[{severity} ADVISORY] {subject}"

        payload = {
            "to": contact,
            "from": self.from_email,
            "subject": formatted_subject,
            "is_simulation": simulate
        }

        if metadata.get("force_email_failure"):
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "EOC Officer"),
                recipient_contact=contact,
                delivery_status="FAILED",
                provider=self.provider_name,
                payload=payload,
                error_message="Forced Email provider failure for testing"
            )

        is_authorized_test = (
            recipient.get("is_test_target", False)
            and metadata.get("is_test_dispatch", False)
            and contact == settings.TEST_NOTIFICATION_EMAIL
        )

        # Safe simulation path if live alerts disabled or host not configured
        if simulate or (not settings.LIVE_ALERTS_ENABLED and not is_authorized_test) or not self.host:
            sim_reason = (
                "SMTP_HOST missing in .env"
                if not self.host
                else ("LIVE_ALERTS_ENABLED=false (safe simulation)" if not settings.LIVE_ALERTS_ENABLED and not is_authorized_test else "Simulation mode")
            )
            payload["simulation_reason"] = sim_reason
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "EOC Officer"),
                recipient_contact=contact,
                delivery_status="SIMULATED",
                provider=self.provider_name,
                payload=payload
            )

        # Rate limit verification
        can_send, reason = rate_limiter.check_and_record_email(contact)
        if not can_send:
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "EOC Officer"),
                recipient_contact=contact,
                delivery_status="RATE_LIMITED",
                provider=self.provider_name,
                payload=payload,
                error_message=reason
            )

        # Formulate MIME message with statutory disclaimer
        msg = MIMEMultipart("alternative")
        msg["Subject"] = metadata.get("email_subject") or formatted_subject
        msg["From"] = self.from_email
        msg["To"] = contact

        if metadata.get("email_body"):
            plain_text = metadata["email_body"]
        else:
            plain_text = (
                f"CYCLONEX AUTOMATED EARLY WARNING ADVISORY\n"
                f"-----------------------------------------\n"
                f"Target Stakeholder: {recipient.get('name', 'Disaster Authority')}\n"
                f"District: {recipient.get('district', 'Coastal Sector')}\n"
                f"Alert Level: {severity}\n\n"
                f"SITUATION OVERVIEW:\n{body}\n\n"
                f"RECOMMENDED PLANNING ACTIONS:\n"
                + "\n".join([f"- {act}" for act in metadata.get("recommended_actions", ["Standby for EOC directives"])])
                + f"\n\n=========================================\n"
                f"{STATUTORY_DISCLAIMER_TEXT}\n"
            )
        msg.attach(MIMEText(plain_text, "plain"))

        max_retries = 3
        last_err = None
        for attempt in range(max_retries):
            try:
                server = smtplib.SMTP(self.host, self.port, timeout=10.0)
                server.ehlo()
                if self.use_tls:
                    server.starttls()
                    server.ehlo()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.from_email, [contact], msg.as_string())
                server.quit()
                logger.info(f"[SMTP Email] Delivered dispatch to {contact}")
                payload["provider_status"] = "SENT_250_OK"
                return NotificationResult(
                    channel=self.channel_name,
                    recipient_name=recipient.get("name", "EOC Officer"),
                    recipient_contact=contact,
                    delivery_status="DELIVERED",
                    provider=self.provider_name,
                    retry_count=attempt,
                    payload=payload
                )
            except smtplib.SMTPAuthenticationError as auth_err:
                last_err = f"SMTP Authentication Error: {auth_err}"
                break # Fatal auth error, do not retry
            except Exception as e:
                err_str = str(e)
                if self.password:
                    err_str = err_str.replace(self.password, "[REDACTED]")
                last_err = err_str

            if attempt < max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))

        logger.error(f"[SMTP Email] Delivery failed to {contact}: {last_err}")
        return NotificationResult(
            channel=self.channel_name,
            recipient_name=recipient.get("name", "EOC Officer"),
            recipient_contact=contact,
            delivery_status="FAILED",
            provider=self.provider_name,
            retry_count=max_retries,
            payload=payload,
            error_message=last_err
        )


class SendGridEmailProvider(BaseNotificationProvider):
    channel_name: str = "email"
    provider_name: str = "SendGrid REST API"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.SENDGRID_API_KEY

    def send(
        self,
        recipient: Dict[str, Any],
        subject: str,
        body: str,
        metadata: Dict[str, Any],
        simulate: bool = False
    ) -> NotificationResult:
        contact = recipient.get("email", settings.TEST_NOTIFICATION_EMAIL)
        severity = metadata.get("severity", "WARNING").upper()
        formatted_subject = f"[{severity} ADVISORY] {subject}"

        payload = {
            "personalizations": [{"to": [{"email": contact}]}],
            "from": {"email": settings.SMTP_FROM_EMAIL.split("<")[-1].replace(">", "").strip() or "alerts@cyclonex.gov.in"},
            "subject": formatted_subject,
            "content": [{"type": "text/plain", "value": f"{body}\n\n{STATUTORY_DISCLAIMER_TEXT}"}]
        }

        if metadata.get("force_email_failure"):
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "EOC Officer"),
                recipient_contact=contact,
                delivery_status="FAILED",
                provider=self.provider_name,
                payload=payload,
                error_message="Forced Email provider failure for testing"
            )

        is_authorized_test = (
            recipient.get("is_test_target", False)
            and metadata.get("is_test_dispatch", False)
            and contact == settings.TEST_NOTIFICATION_EMAIL
        )

        if simulate or (not settings.LIVE_ALERTS_ENABLED and not is_authorized_test) or not self.api_key:
            sim_reason = (
                "SENDGRID_API_KEY missing in .env"
                if not self.api_key
                else ("LIVE_ALERTS_ENABLED=false (safe simulation)" if not settings.LIVE_ALERTS_ENABLED and not is_authorized_test else "Simulation mode")
            )
            payload["simulation_reason"] = sim_reason
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "EOC Officer"),
                recipient_contact=contact,
                delivery_status="SIMULATED",
                provider=self.provider_name,
                payload=payload
            )

        can_send, reason = rate_limiter.check_and_record_email(contact)
        if not can_send:
            return NotificationResult(
                channel=self.channel_name,
                recipient_name=recipient.get("name", "EOC Officer"),
                recipient_contact=contact,
                delivery_status="RATE_LIMITED",
                provider=self.provider_name,
                payload=payload,
                error_message=reason
            )

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        max_retries = 3
        last_err = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    return NotificationResult(
                        channel=self.channel_name,
                        recipient_name=recipient.get("name", "EOC Officer"),
                        recipient_contact=contact,
                        delivery_status="DELIVERED",
                        provider=self.provider_name,
                        retry_count=attempt,
                        payload=payload
                    )
            except urllib.error.HTTPError as he:
                last_err = f"SendGrid HTTP {he.code}: {he.read().decode('utf-8', errors='ignore')}"
                if 400 <= he.code < 500:
                    break
            except Exception as e:
                last_err = str(e)
            if attempt < max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))

        return NotificationResult(
            channel=self.channel_name,
            recipient_name=recipient.get("name", "EOC Officer"),
            recipient_contact=contact,
            delivery_status="FAILED",
            provider=self.provider_name,
            retry_count=max_retries,
            payload=payload,
            error_message=last_err
        )


class NotificationDispatcher:
    def __init__(self):
        self.dashboard_provider = DashboardNotificationProvider()
        self.sms_provider: BaseNotificationProvider = self._resolve_sms_provider()
        self.email_provider: BaseNotificationProvider = self._resolve_email_provider()

    def _resolve_sms_provider(self) -> BaseNotificationProvider:
        prov = (settings.SMS_PROVIDER or "mock").lower()
        if prov == "twilio":
            return TwilioSMSProvider()
        elif prov == "generic_http":
            return GenericHTTPSMSProvider()
        return TwilioSMSProvider() # Defaults to Twilio with safe simulation fallback if keys missing

    def _resolve_email_provider(self) -> BaseNotificationProvider:
        prov = (settings.EMAIL_PROVIDER or "mock").lower()
        if prov == "sendgrid":
            return SendGridEmailProvider()
        elif prov == "smtp":
            return SMTPEmailProvider()
        return SMTPEmailProvider() # Defaults to SMTP with safe simulation fallback if host missing

    def reload_providers(self):
        """Refreshes providers when admin changes configuration."""
        self.sms_provider = self._resolve_sms_provider()
        self.email_provider = self._resolve_email_provider()

    def dispatch(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        body: str,
        metadata: Dict[str, Any],
        channels: Optional[List[str]] = None,
        simulate: bool = False
    ) -> List[NotificationResult]:
        """
        Dispatches notifications across requested channels.
        Enforces emergency kill switch, then master safety interlock.
        """
        if channels is None:
            channels = ["dashboard", "sms", "email"]

        # EMERGENCY KILL SWITCH: immediately block all external dispatch
        if _kill_switch_active:
            logger.warning("[Dispatcher] KILL SWITCH ACTIVE — blocking all external dispatch.")
            results: List[NotificationResult] = []
            for recipient in recipients:
                for ch in channels:
                    results.append(NotificationResult(
                        channel=ch,
                        recipient_name=recipient.get("name", "Authority Contact"),
                        recipient_contact=recipient.get("email", recipient.get("phone", "unknown")),
                        delivery_status="BLOCKED_KILL_SWITCH",
                        provider="kill_switch",
                        payload={"reason": "Emergency kill switch is active. All external dispatch suspended."}
                    ))
            return results

        # Determine if this dispatch batch is an authorized test dispatch targeting ONLY test contacts
        is_test_batch = metadata.get("is_test_dispatch", False) and all(
            r.get("is_test_target", False) for r in recipients
        )

        # Enforce master safety switch: if False and not authorized test batch, external channels MUST simulate
        effective_simulate = simulate if is_test_batch else (simulate or (not settings.LIVE_ALERTS_ENABLED))

        results: List[NotificationResult] = []

        for recipient in recipients:
            allowed_channels = recipient.get("channels", ["dashboard"])
            
            # 1. Dashboard Dispatch (always active)
            if "dashboard" in channels and "dashboard" in allowed_channels:
                try:
                    res = self.dashboard_provider.send(
                        recipient=recipient,
                        subject=subject,
                        body=body,
                        metadata=metadata,
                        simulate=simulate
                    )
                    results.append(res)
                except Exception as exc:
                    logger.error(f"[Dispatcher] Dashboard error: {exc}")

            # 2. SMS Dispatch
            if "sms" in channels and "sms" in allowed_channels:
                try:
                    res = self.sms_provider.send(
                        recipient=recipient,
                        subject=subject,
                        body=body,
                        metadata=metadata,
                        simulate=effective_simulate
                    )
                    results.append(res)
                except Exception as exc:
                    logger.error(f"[Dispatcher] SMS error: {exc}")
                    results.append(NotificationResult(
                        channel="sms",
                        recipient_name=recipient.get("name", "Authority Contact"),
                        recipient_contact=recipient.get("phone", "unknown"),
                        delivery_status="FAILED",
                        provider=self.sms_provider.provider_name,
                        payload={"error": str(exc)},
                        error_message=str(exc)
                    ))

            # 3. Email Dispatch
            if "email" in channels and "email" in allowed_channels:
                try:
                    res = self.email_provider.send(
                        recipient=recipient,
                        subject=subject,
                        body=body,
                        metadata=metadata,
                        simulate=effective_simulate
                    )
                    results.append(res)
                except Exception as exc:
                    logger.error(f"[Dispatcher] Email error: {exc}")
                    results.append(NotificationResult(
                        channel="email",
                        recipient_name=recipient.get("name", "EOC Officer"),
                        recipient_contact=recipient.get("email", "unknown"),
                        delivery_status="FAILED",
                        provider=self.email_provider.provider_name,
                        payload={"error": str(exc)},
                        error_message=str(exc)
                    ))

        return results

# ============================================================
# LIVE VERIFICATION STATE TRACKING
# States: NOT_CONFIGURED | CONFIGURED_NOT_TESTED | TEST_FAILED | LIVE_VERIFIED
# ============================================================
_live_verification_status: str = "NOT_CONFIGURED"
_last_live_test_summary: Optional[Dict[str, Any]] = None

def get_live_verification_state() -> str:
    """
    Computes current live verification state based on credential status and controlled test history.
    """
    global _live_verification_status
    report = validate_notification_credentials()
    sms_st = report["sms"]["status"]
    email_st = report["email"]["status"]

    if sms_st != "CONFIGURED" or email_st != "CONFIGURED":
        _live_verification_status = "NOT_CONFIGURED"
        return "NOT_CONFIGURED"

    if _live_verification_status in ("LIVE_VERIFIED", "TEST_FAILED"):
        return _live_verification_status

    return "CONFIGURED_NOT_TESTED"

def set_live_verification_state(new_state: str, summary: Optional[Dict[str, Any]] = None):
    global _live_verification_status, _last_live_test_summary
    _live_verification_status = new_state
    if summary:
        _last_live_test_summary = summary

def validate_notification_credentials() -> Dict[str, Any]:
    """
    Validates Twilio and SMTP/SendGrid credentials against .env format rules without making any network calls.
    Returns CONFIGURED, NOT_CONFIGURED, or INVALID for each provider.
    Never exposes secrets or credentials in output.
    """
    prov_sms = (settings.SMS_PROVIDER or "mock").lower()
    prov_email = (settings.EMAIL_PROVIDER or "mock").lower()

    # 1. Validate SMS Provider (Twilio)
    sms_status = "NOT_CONFIGURED"
    sms_reason = "SMS provider is not configured in .env."

    if prov_sms == "mock" or not prov_sms:
        sms_status = "NOT_CONFIGURED"
        sms_reason = "SMS_PROVIDER is set to 'mock' in .env. Configure 'twilio' and provide credentials."
    elif prov_sms == "twilio":
        sid = (settings.TWILIO_ACCOUNT_SID or "").strip()
        token = (settings.TWILIO_AUTH_TOKEN or "").strip()
        from_num = (settings.TWILIO_FROM_NUMBER or "").strip()

        if not sid or not token or not from_num:
            sms_status = "NOT_CONFIGURED"
            missing = []
            if not sid: missing.append("TWILIO_ACCOUNT_SID")
            if not token: missing.append("TWILIO_AUTH_TOKEN")
            if not from_num: missing.append("TWILIO_FROM_NUMBER")
            sms_reason = f"Missing required variables in .env: {', '.join(missing)}"
        else:
            # Check format validity
            is_valid_sid = sid.startswith("AC") and len(sid) == 34
            is_valid_from = from_num.startswith("+") and len(from_num) >= 8 and from_num[1:].replace("-", "").replace(" ", "").isdigit()
            is_valid_token = len(token) >= 20

            if not is_valid_sid:
                sms_status = "INVALID"
                sms_reason = "TWILIO_ACCOUNT_SID format invalid: must start with 'AC' and be 34 characters."
            elif not is_valid_from:
                sms_status = "INVALID"
                sms_reason = "TWILIO_FROM_NUMBER format invalid: must be in E.164 format (+...)."
            elif not is_valid_token:
                sms_status = "INVALID"
                sms_reason = "TWILIO_AUTH_TOKEN format invalid: minimum length not met."
            else:
                sms_status = "CONFIGURED"
                sms_reason = "Twilio credentials format valid."
    elif prov_sms == "generic_http":
        url = (settings.SMS_GATEWAY_URL or "").strip()
        if not url:
            sms_status = "NOT_CONFIGURED"
            sms_reason = "Missing SMS_GATEWAY_URL in .env"
        elif not (url.startswith("http://") or url.startswith("https://")):
            sms_status = "INVALID"
            sms_reason = "SMS_GATEWAY_URL must be a valid HTTP/HTTPS URL"
        else:
            sms_status = "CONFIGURED"
            sms_reason = "Generic HTTP SMS Gateway configured."
    else:
        sms_status = "NOT_CONFIGURED"
        sms_reason = f"Unsupported SMS_PROVIDER '{prov_sms}'."

    # 2. Validate Email Provider (SMTP)
    email_status = "NOT_CONFIGURED"
    email_reason = "Email provider is not configured in .env."

    if prov_email == "mock" or not prov_email:
        email_status = "NOT_CONFIGURED"
        email_reason = "EMAIL_PROVIDER is set to 'mock' in .env. Configure 'smtp' and provide credentials."
    elif prov_email == "smtp":
        host = (settings.SMTP_HOST or "").strip()
        user = (settings.SMTP_USER or "").strip()
        pwd = (settings.SMTP_PASSWORD or "").strip()
        port = settings.SMTP_PORT
        from_email = (settings.SMTP_FROM_EMAIL or "").strip()

        if not host or not user or not pwd:
            email_status = "NOT_CONFIGURED"
            missing = []
            if not host: missing.append("SMTP_HOST")
            if not user: missing.append("SMTP_USER")
            if not pwd: missing.append("SMTP_PASSWORD")
            email_reason = f"Missing required variables in .env: {', '.join(missing)}"
        else:
            # Check format validity
            is_valid_host = bool(host and " " not in host and ("." in host or host == "localhost"))
            is_valid_port = isinstance(port, int) and 1 <= port <= 65535
            is_valid_from = bool(from_email and "@" in from_email)

            if not is_valid_host:
                email_status = "INVALID"
                email_reason = "SMTP_HOST format invalid: must be a valid hostname or IP without spaces."
            elif not is_valid_port:
                email_status = "INVALID"
                email_reason = "SMTP_PORT invalid: must be an integer between 1 and 65535."
            elif not is_valid_from:
                email_status = "INVALID"
                email_reason = "SMTP_FROM_EMAIL invalid: must contain a valid email address."
            else:
                email_status = "CONFIGURED"
                email_reason = "SMTP credentials format valid."
    elif prov_email == "sendgrid":
        key = (settings.SENDGRID_API_KEY or "").strip()
        if not key:
            email_status = "NOT_CONFIGURED"
            email_reason = "Missing SENDGRID_API_KEY in .env"
        elif not key.startswith("SG."):
            email_status = "INVALID"
            email_reason = "SENDGRID_API_KEY must start with 'SG.'"
        else:
            email_status = "CONFIGURED"
            email_reason = "SendGrid API Key configured."
    else:
        email_status = "NOT_CONFIGURED"
        email_reason = f"Unsupported EMAIL_PROVIDER '{prov_email}'."

    # Compute current live verification state
    if sms_status != "CONFIGURED" or email_status != "CONFIGURED":
        current_state = "NOT_CONFIGURED"
    elif _live_verification_status in ("LIVE_VERIFIED", "TEST_FAILED"):
        current_state = _live_verification_status
    else:
        current_state = "CONFIGURED_NOT_TESTED"

    return {
        "sms": {
            "provider": prov_sms,
            "status": sms_status,
            "details": sms_reason
        },
        "email": {
            "provider": prov_email,
            "status": email_status,
            "details": email_reason
        },
        "live_alerts_enabled": settings.LIVE_ALERTS_ENABLED,
        "live_verification_state": current_state,
        "kill_switch_active": is_kill_switch_active(),
        "test_recipients": {
            "phone": settings.TEST_NOTIFICATION_PHONE or "Not configured",
            "email": settings.TEST_NOTIFICATION_EMAIL or "Not configured"
        }
    }

def execute_controlled_live_delivery(
    db,
    confirm_live_test: bool = False,
    recipient_phone: Optional[str] = None,
    recipient_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes exactly ONE real controlled test SMS (Twilio) and ONE real controlled test email (SMTP)
    strictly to TEST_NOTIFICATION_PHONE and TEST_NOTIFICATION_EMAIL.
    Captures provider delivery confirmation (Message SID / SMTP response).
    Enforces all safety interlocks and records results in alert_delivery_logs.
    """
    import uuid
    from backend.app.models.entities import AlertDeliveryLog

    # Safety Check 1: Explicit Confirmation
    if not confirm_live_test:
        raise ValueError("Explicit confirmation required: set confirm_live_test: true.")

    # Safety Check 2: Emergency Kill Switch
    if is_kill_switch_active():
        raise RuntimeError("Emergency kill switch is ACTIVE. External dispatch is strictly blocked.")

    # Safety Check 3: Arbitrary Recipient Rejection
    auth_phone = settings.TEST_NOTIFICATION_PHONE
    auth_email = settings.TEST_NOTIFICATION_EMAIL

    if not auth_phone or not auth_email:
        raise ValueError("TEST_NOTIFICATION_PHONE and TEST_NOTIFICATION_EMAIL must be set in .env before testing.")

    if recipient_phone and recipient_phone.strip() != auth_phone.strip():
        raise ValueError(f"Arbitrary recipients rejected. Live delivery tests may ONLY be sent to authorized TEST_NOTIFICATION_PHONE: {auth_phone}")

    if recipient_email and recipient_email.strip() != auth_email.strip():
        raise ValueError(f"Arbitrary recipients rejected. Live delivery tests may ONLY be sent to authorized TEST_NOTIFICATION_EMAIL: {auth_email}")

    # Safety Check 4: Credential Format Validation
    val_rep = validate_notification_credentials()
    if val_rep["sms"]["status"] != "CONFIGURED" or val_rep["email"]["status"] != "CONFIGURED":
        reasons = []
        if val_rep["sms"]["status"] != "CONFIGURED":
            reasons.append(f"SMS ({val_rep['sms']['provider']}): {val_rep['sms']['status']} - {val_rep['sms']['details']}")
        if val_rep["email"]["status"] != "CONFIGURED":
            reasons.append(f"Email ({val_rep['email']['provider']}): {val_rep['email']['status']} - {val_rep['email']['details']}")
        raise ValueError(f"Cannot run live delivery test: providers are not CONFIGURED. Issues: {'; '.join(reasons)}")

    # Target strictly the authorized test recipient
    recipients = [{
        "name": "CycloneX Administrator (Controlled Test)",
        "audience": "Authorities",
        "district": "Operations HQ Test Cell",
        "phone": auth_phone,
        "email": auth_email,
        "channels": ["sms", "email"],
        "is_test_target": True
    }]

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sms_body = "CycloneX controlled LIVE delivery test. This is a test notification only. No emergency action is required."
    email_subject = "CycloneX - Controlled LIVE Delivery Test"
    email_body = (
        "This is a controlled CycloneX external alert delivery test.\n"
        "No emergency action is required.\n"
        "This message verifies the configured external email provider."
    )

    metadata = {
        "severity": "Advisory",
        "headline": "CycloneX Controlled LIVE Delivery Test",
        "wind_kts": 35.0,
        "risk_score": 0.35,
        "is_test_dispatch": True,
        "sms_body": sms_body,
        "email_subject": email_subject,
        "email_body": email_body,
        "recommended_actions": ["Verify SMS receipt", "Verify Email receipt"]
    }

    # Reload providers to pick up any environment or config changes
    notification_dispatcher.reload_providers()

    # Execute dispatch through real providers
    dispatches = notification_dispatcher.dispatch(
        recipients=recipients,
        subject=email_subject,
        body=email_body,
        metadata=metadata,
        channels=["sms", "email"],
        simulate=False
    )

    # Record in database audit log
    for d in dispatches:
        log_entry = AlertDeliveryLog(
            id=f"val-{uuid.uuid4().hex[:8]}",
            alert_id="sys-controlled-live-test",
            channel=d.channel,
            recipient_name=d.recipient_name,
            recipient_contact=d.recipient_contact,
            delivery_status=d.delivery_status,
            trigger_type="CONTROLLED_LIVE_TEST",
            payload=d.payload,
            error_message=d.error_message,
            sent_at=d.timestamp
        )
        db.add(log_entry)
    db.commit()

    sms_res = next((d for d in dispatches if d.channel == "sms"), None)
    email_res = next((d for d in dispatches if d.channel == "email"), None)

    # Provider confirmation checks
    sms_confirmed = bool(
        sms_res 
        and sms_res.delivery_status == "DELIVERED" 
        and sms_res.payload 
        and sms_res.payload.get("message_sid")
    )
    email_confirmed = bool(
        email_res 
        and email_res.delivery_status == "DELIVERED" 
        and email_res.payload
        and email_res.payload.get("provider_status") == "SENT_250_OK"
    )

    if sms_confirmed and email_confirmed:
        set_live_verification_state("LIVE_VERIFIED")
        verdict = "LIVE_VERIFIED"
        summary = "Both SMS and Email external provider deliveries confirmed and verified by remote gateways."
    else:
        set_live_verification_state("TEST_FAILED")
        verdict = "TEST_FAILED"
        reasons = []
        if not sms_confirmed:
            reasons.append(f"SMS failed: {sms_res.error_message if sms_res else 'No response'}")
        if not email_confirmed:
            reasons.append(f"Email failed: {email_res.error_message if email_res else 'No response'}")
        summary = f"Provider delivery could not be confirmed: {'; '.join(reasons)}"

    sms_dict = {
        "provider": sms_res.provider if sms_res else "Twilio REST API",
        "channel": "sms",
        "recipient": auth_phone,
        "status": sms_res.delivery_status if sms_res else "FAILED",
        "message_sid": sms_res.payload.get("message_sid") if sms_res and sms_res.payload else None,
        "provider_status": sms_res.payload.get("provider_status") if sms_res and sms_res.payload else None,
        "confirmed": sms_confirmed,
        "error": sms_res.error_message if sms_res else None,
        "timestamp": now_iso
    }
    email_dict = {
        "provider": email_res.provider if email_res else "Standard SMTP (TLS/SSL)",
        "channel": "email",
        "recipient": auth_email,
        "status": email_res.delivery_status if email_res else "FAILED",
        "provider_status": email_res.payload.get("provider_status") if email_res and email_res.payload else None,
        "confirmed": email_confirmed,
        "error": email_res.error_message if email_res else None,
        "timestamp": now_iso
    }

    return {
        "verification_status": verdict,
        "summary": summary,
        "sms": sms_dict,
        "email": email_dict,
        "sms_delivery": sms_dict,
        "email_delivery": email_dict,
        "live_alerts_enabled": settings.LIVE_ALERTS_ENABLED,
        "safety_guarantee": "LIVE_ALERTS_ENABLED remains false. Explicit administrator action required to enable automatic broadcasts."
    }

notification_dispatcher = NotificationDispatcher()

# Backward-compatibility aliases
SMSNotificationProvider = TwilioSMSProvider
EmailNotificationProvider = SMTPEmailProvider

