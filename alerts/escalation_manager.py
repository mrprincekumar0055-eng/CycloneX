"""
CycloneX Alert Escalation & Duplicate Prevention Manager
Implements:
1. Cooldown Period Duplicate Prevention
2. Severity-Based Automatic Escalation Rules (Advisory -> Watch -> Warning -> Emergency)
3. Lifecycle State Machine (ACTIVE -> ACKNOWLEDGED -> ESCALATED -> RESOLVED)
4. Escalation Parent Chaining
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import hashlib

# Operational Severity Hierarchy Rank
SEVERITY_RANKS = {
    "Normal": 0,
    "Advisory": 1,
    "Watch": 2,
    "Warning": 3,
    "Emergency": 4
}

class EscalationManager:
    DEFAULT_COOLDOWN_MINUTES = 60

    def __init__(self, cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES):
        self.cooldown_minutes = cooldown_minutes
        # In-memory tracking of recent alerts: key -> {alert_id, alert_level, timestamp, status}
        self._recent_alerts: Dict[str, Dict[str, Any]] = {}

    def _make_key(self, cyclone_name: str, district: str) -> str:
        return f"{cyclone_name.strip().upper()}::{district.strip().upper()}"

    def evaluate_dispatch(
        self,
        cyclone_name: str,
        district: str,
        new_alert_level: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Determines whether a new alert should be dispatched.
        Returns: (should_dispatch, action_type, parent_alert_id)
        action_type can be:
        - "NEW": Initial alert for this cyclone & district
        - "ESCALATED": Higher severity trigger bypassing cooldown
        - "DUPLICATE_SUPPRESSED": Repeated trigger at same/lower level within cooldown
        - "RENEWED": Trigger after cooldown expiration
        """
        key = self._make_key(cyclone_name, district)
        existing = self._recent_alerts.get(key)
        now = datetime.now(timezone.utc)

        if not existing:
            return True, "NEW", None

        existing_level = existing["alert_level"]
        existing_time = existing["timestamp"]
        existing_id = existing["alert_id"]
        existing_status = existing.get("status", "ACTIVE")

        # If previous alert was resolved, allow new alert as fresh
        if existing_status == "RESOLVED":
            return True, "NEW", None

        existing_rank = SEVERITY_RANKS.get(existing_level, 1)
        new_rank = SEVERITY_RANKS.get(new_alert_level, 1)

        # 1. Escalation: Higher severity bypasses cooldown immediately
        if new_rank > existing_rank:
            return True, "ESCALATED", existing_id

        # 2. Cooldown check for same or lower severity
        cooldown_delta = timedelta(minutes=self.cooldown_minutes)
        if now - existing_time < cooldown_delta:
            # Suppress duplicate
            return False, "DUPLICATE_SUPPRESSED", existing_id

        # 3. Cooldown expired -> renew alert
        return True, "RENEWED", existing_id

    def record_dispatched_alert(
        self,
        cyclone_name: str,
        district: str,
        alert_id: str,
        alert_level: str,
        status: str = "ACTIVE"
    ):
        """
        Updates in-memory state tracking to prevent duplicate storms.
        """
        key = self._make_key(cyclone_name, district)
        self._recent_alerts[key] = {
            "alert_id": alert_id,
            "alert_level": alert_level,
            "timestamp": datetime.now(timezone.utc),
            "status": status
        }

    def update_alert_status(
        self,
        cyclone_name: str,
        district: str,
        new_status: str
    ):
        key = self._make_key(cyclone_name, district)
        if key in self._recent_alerts:
            self._recent_alerts[key]["status"] = new_status

    def clear(self):
        """Resets in-memory tracking (useful for tests)."""
        self._recent_alerts.clear()

escalation_manager = EscalationManager()

