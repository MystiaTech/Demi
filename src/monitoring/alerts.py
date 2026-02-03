"""Alert system for health anomaly detection.

Provides configurable alert rules with cooldowns, notification channels,
and automatic resolution for monitoring Demi's health.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any

from src.core.logger import get_logger

logger = get_logger()


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """An active or resolved alert."""

    id: str
    rule_name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    value: Optional[float] = None
    acknowledged: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if alert is still active."""
        return self.resolved_at is None

    @property
    def duration_seconds(self) -> float:
        """Get duration of alert in seconds."""
        end = self.resolved_at or datetime.now()
        return (end - self.timestamp).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "acknowledged": self.acknowledged,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_active": self.is_active,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class AlertRule:
    """Rule for triggering alerts."""

    name: str
    condition: Callable[[Dict[str, Any]], bool]
    level: AlertLevel
    message_template: str
    cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=30))
    enabled: bool = True
    auto_resolve: bool = True
    _last_triggered: Optional[datetime] = field(default=None, repr=False)
    _last_alert_id: Optional[str] = field(default=None, repr=False)

    def check_condition(self, data: Dict[str, Any]) -> bool:
        """Check if alert condition is met, respecting cooldown.

        Args:
            data: Current system state data

        Returns:
            True if condition is met and cooldown has passed
        """
        if not self.enabled:
            return False

        # Check cooldown
        if self._last_triggered:
            time_since_last = datetime.now() - self._last_triggered
            if time_since_last < self.cooldown:
                return False

        # Check condition
        try:
            if self.condition(data):
                self._last_triggered = datetime.now()
                return True
        except Exception as e:
            logger.error(f"Alert rule '{self.name}' condition error", error=str(e))

        return False

    def format_message(self, data: Dict[str, Any]) -> str:
        """Format alert message with current data.

        Args:
            data: Current system state data

        Returns:
            Formatted message string
        """
        try:
            return self.message_template.format(**data)
        except Exception:
            return self.message_template


class NotificationChannel:
    """Base class for alert notification channels."""

    async def send(self, alert: Alert):
        """Send alert notification.

        Args:
            alert: The alert to send
        """
        raise NotImplementedError


class LogNotificationChannel(NotificationChannel):
    """Send alerts to log."""

    async def send(self, alert: Alert):
        """Log alert at appropriate level."""
        log_message = f"Alert {alert.id[:8]}: {alert.rule_name} [{alert.level.value}] {alert.message}"

        if alert.level == AlertLevel.CRITICAL:
            logger.critical(log_message)
        elif alert.level == AlertLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)


class WebhookNotificationChannel(NotificationChannel):
    """Send alerts to webhook URL."""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        """Initialize webhook channel.

        Args:
            webhook_url: URL to POST alert data
            headers: Optional headers to include
        """
        self.webhook_url = webhook_url
        self.headers = headers or {}

    async def send(self, alert: Alert):
        """Send alert to webhook."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.webhook_url,
                    json=alert.to_dict(),
                    headers=self.headers,
                )
        except Exception as e:
            logger.error("Webhook notification failed", error=str(e), alert_id=alert.id)


class DiscordNotificationChannel(NotificationChannel):
    """Send alerts to Discord channel via webhook."""

    def __init__(self, webhook_url: str):
        """Initialize Discord channel.

        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url

    async def send(self, alert: Alert):
        """Send alert to Discord as embed."""
        try:
            import aiohttp

            color_map = {
                AlertLevel.INFO: 3447003,  # Blue
                AlertLevel.WARNING: 15158332,  # Yellow/Orange
                AlertLevel.CRITICAL: 15158332,  # Red
            }

            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.CRITICAL: "🚨",
            }

            embed = {
                "title": f"{emoji_map.get(alert.level, '🔔')} Alert: {alert.rule_name}",
                "description": alert.message,
                "color": color_map.get(alert.level, 0),
                "timestamp": alert.timestamp.isoformat(),
                "fields": [
                    {
                        "name": "Severity",
                        "value": alert.level.value.upper(),
                        "inline": True,
                    },
                    {"name": "Alert ID", "value": alert.id[:8], "inline": True},
                ],
            }

            if alert.value is not None:
                embed["fields"].append(
                    {"name": "Value", "value": f"{alert.value:.2f}", "inline": True}
                )

            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.webhook_url,
                    json={"embeds": [embed]},
                )

        except Exception as e:
            logger.error("Discord notification failed", error=str(e), alert_id=alert.id)


# Default alert rules
DEFAULT_ALERT_RULES = [
    # Memory alerts
    AlertRule(
        name="high_memory_usage",
        condition=lambda data: data.get("memory_percent", 0) > 80,
        level=AlertLevel.WARNING,
        message_template="Memory usage is at {memory_percent:.1f}% (>80% threshold)",
        cooldown=timedelta(minutes=10),
    ),
    AlertRule(
        name="critical_memory_usage",
        condition=lambda data: data.get("memory_percent", 0) > 90,
        level=AlertLevel.CRITICAL,
        message_template="CRITICAL: Memory usage is at {memory_percent:.1f}% (>90% threshold)",
        cooldown=timedelta(minutes=5),
    ),
    # CPU alerts
    AlertRule(
        name="high_cpu_usage",
        condition=lambda data: data.get("cpu_percent", 0) > 85,
        level=AlertLevel.WARNING,
        message_template="CPU usage is at {cpu_percent:.1f}% (>85% threshold)",
        cooldown=timedelta(minutes=15),
    ),
    # Response time alerts
    AlertRule(
        name="high_response_time_p90",
        condition=lambda data: data.get("response_time_p90", 0) > 5.0,
        level=AlertLevel.WARNING,
        message_template="P90 response time is {response_time_p90:.2f}s (>5s threshold)",
        cooldown=timedelta(minutes=10),
    ),
    # Platform health alerts
    AlertRule(
        name="platform_unhealthy",
        condition=lambda data: data.get("unhealthy_platforms", 0) > 0,
        level=AlertLevel.WARNING,
        message_template="{unhealthy_platforms} platform(s) are unhealthy",
        cooldown=timedelta(minutes=5),
    ),
    AlertRule(
        name="platform_offline_extended",
        condition=lambda data: data.get("offline_duration_minutes", 0) > 5,
        level=AlertLevel.CRITICAL,
        message_template="Platform {platform_name} has been offline for {offline_duration_minutes:.0f} minutes",
        cooldown=timedelta(minutes=5),
    ),
    # Emotional state alerts (for monitoring)
    AlertRule(
        name="extreme_loneliness",
        condition=lambda data: data.get("emotions", {}).get("loneliness", 0) > 0.9,
        level=AlertLevel.INFO,
        message_template="Demi's loneliness is very high ({emotions[loneliness]:.0%})",
        cooldown=timedelta(minutes=60),
    ),
    AlertRule(
        name="extreme_frustration",
        condition=lambda data: data.get("emotions", {}).get("frustration", 0) > 0.9,
        level=AlertLevel.INFO,
        message_template="Demi's frustration is very high ({emotions[frustration]:.0%})",
        cooldown=timedelta(minutes=60),
    ),
    AlertRule(
        name="emotional_anomaly",
        condition=lambda data: data.get("emotional_anomaly_detected", False),
        level=AlertLevel.WARNING,
        message_template="Emotional state anomaly detected: {emotional_anomaly_reason}",
        cooldown=timedelta(minutes=30),
    ),
]


class AlertManager:
    """Manages alert rules, triggering, and notifications.

    Features:
    - Configurable alert rules with cooldowns
    - Multiple notification channels
    - Alert acknowledgment and resolution
    - Automatic alert evaluation
    """

    def __init__(self, max_alerts: int = 100):
        """Initialize alert manager.

        Args:
            max_alerts: Maximum number of alerts to keep in history
        """
        self.max_alerts = max_alerts
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.active_alerts: Dict[str, Alert] = {}  # rule_name -> alert
        self.notification_channels: List[NotificationChannel] = []

        # Add default log channel
        self.add_notification_channel(LogNotificationChannel())

        logger.info("AlertManager initialized", max_alerts=max_alerts)

    def add_rule(self, rule: AlertRule):
        """Register an alert rule.

        Args:
            rule: AlertRule to register
        """
        self.rules[rule.name] = rule
        logger.debug(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_name: str):
        """Remove an alert rule.

        Args:
            rule_name: Name of rule to remove
        """
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.debug(f"Removed alert rule: {rule_name}")

    def add_notification_channel(self, channel: NotificationChannel):
        """Add a notification channel.

        Args:
            channel: NotificationChannel to add
        """
        self.notification_channels.append(channel)
        logger.debug(f"Added notification channel: {type(channel).__name__}")

    def check_alerts(self, data: Dict[str, Any]) -> List[Alert]:
        """Evaluate all rules against current data and trigger alerts.

        Args:
            data: Current system state data

        Returns:
            List of newly triggered alerts
        """
        triggered = []

        for rule in self.rules.values():
            # Check for auto-resolution
            if rule.auto_resolve and rule._last_alert_id:
                active_alert = self.active_alerts.get(rule.name)
                if active_alert and active_alert.id == rule._last_alert_id:
                    # Check if condition is now clear
                    try:
                        condition_met = rule.condition(data)
                    except Exception:
                        condition_met = False

                    if not condition_met:
                        self.resolve_alert(active_alert.id)
                        continue

            # Check for new trigger
            if rule.check_condition(data):
                # Check if already have active alert for this rule
                if rule.name in self.active_alerts:
                    continue

                alert = self._create_alert(rule, data)
                triggered.append(alert)

        return triggered

    def _create_alert(self, rule: AlertRule, data: Dict[str, Any]) -> Alert:
        """Create and process a new alert.

        Args:
            rule: The triggered rule
            data: Current system data

        Returns:
            Created Alert object
        """
        alert = Alert(
            id=str(uuid.uuid4()),
            rule_name=rule.name,
            level=rule.level,
            message=rule.format_message(data),
            timestamp=datetime.now(),
            value=data.get(f"{rule.name}_value"),
            metadata={"trigger_data": data},
        )

        # Store alert
        self.alerts.append(alert)
        self.active_alerts[rule.name] = alert
        rule._last_alert_id = alert.id

        # Trim history if needed (keep most recent)
        while len(self.alerts) > self.max_alerts:
            self.alerts.pop(0)

        # Send notifications (schedule if event loop is running, otherwise skip)
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self._send_notifications(alert))
        except RuntimeError:
            # No event loop, skip async notification
            pass

        logger.warning(
            "Alert triggered",
            alert_id=alert.id,
            rule=rule.name,
            level=rule.level.value,
        )

        return alert

    async def _send_notifications(self, alert: Alert):
        """Send alert to all notification channels.

        Args:
            alert: Alert to send
        """
        for channel in self.notification_channels:
            try:
                await channel.send(alert)
            except Exception as e:
                logger.error(
                    "Notification failed",
                    channel=type(channel).__name__,
                    error=str(e),
                )

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved.

        Args:
            alert_id: ID of alert to resolve

        Returns:
            True if alert was found and resolved
        """
        for alert in self.alerts:
            if alert.id == alert_id and alert.is_active:
                alert.resolved_at = datetime.now()

                # Remove from active alerts
                for rule_name, active in list(self.active_alerts.items()):
                    if active.id == alert_id:
                        del self.active_alerts[rule_name]
                        break

                logger.info("Alert resolved", alert_id=alert_id, rule=alert.rule_name)
                return True

        return False

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged.

        Args:
            alert_id: ID of alert to acknowledge

        Returns:
            True if alert was found
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                logger.info("Alert acknowledged", alert_id=alert_id)
                return True
        return False

    def get_active_alerts(
        self, level: Optional[AlertLevel] = None, acknowledged: Optional[bool] = None
    ) -> List[Alert]:
        """Get currently active alerts.

        Args:
            level: Optional filter by severity level
            acknowledged: Optional filter by acknowledgment status

        Returns:
            List of active Alert objects
        """
        alerts = [a for a in self.alerts if a.is_active]

        if level:
            alerts = [a for a in alerts if a.level == level]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get historical alerts (including resolved).

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of Alert objects
        """
        # Apply max_alerts limit from config if set
        effective_limit = min(limit, self.max_alerts) if self.max_alerts else limit
        return sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:effective_limit]

    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID.

        Args:
            alert_id: Alert ID to find

        Returns:
            Alert object or None
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                return alert
        return None


# Global alert manager instance
_alert_manager_instance: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance."""
    global _alert_manager_instance
    if _alert_manager_instance is None:
        _alert_manager_instance = AlertManager()
        # Add default rules
        for rule in DEFAULT_ALERT_RULES:
            _alert_manager_instance.add_rule(rule)
    return _alert_manager_instance
