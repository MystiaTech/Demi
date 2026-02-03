"""Tests for the alerting system."""

import pytest
from datetime import datetime, timedelta
from src.monitoring.alerts import (
    AlertLevel,
    Alert,
    AlertRule,
    AlertManager,
    LogNotificationChannel,
)


class TestAlert:
    """Test Alert dataclass."""

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert(
            id="test-123",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test alert message",
            timestamp=datetime.now(),
        )

        assert alert.id == "test-123"
        assert alert.rule_name == "test_rule"
        assert alert.level == AlertLevel.WARNING
        assert alert.message == "Test alert message"
        assert alert.is_active is True
        assert alert.acknowledged is False

    def test_alert_is_active(self):
        """Test alert active status."""
        alert = Alert(
            id="test-123",
            rule_name="test_rule",
            level=AlertLevel.INFO,
            message="Test",
            timestamp=datetime.now(),
        )

        assert alert.is_active is True

        alert.resolved_at = datetime.now()
        assert alert.is_active is False

    def test_alert_duration(self):
        """Test alert duration calculation."""
        alert = Alert(
            id="test-123",
            rule_name="test_rule",
            level=AlertLevel.INFO,
            message="Test",
            timestamp=datetime.now() - timedelta(seconds=60),
        )

        # Should have ~60 seconds duration
        assert 55 < alert.duration_seconds < 65

    def test_alert_to_dict(self):
        """Test alert serialization."""
        alert = Alert(
            id="test-123",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )

        data = alert.to_dict()
        assert data["id"] == "test-123"
        assert data["rule_name"] == "test_rule"
        assert data["level"] == "warning"
        assert data["is_active"] is True
        assert "duration_seconds" in data


class TestAlertRule:
    """Test AlertRule class."""

    def test_rule_creation(self):
        """Test creating an alert rule."""
        rule = AlertRule(
            name="high_cpu",
            condition=lambda d: d.get("cpu", 0) > 80,
            level=AlertLevel.WARNING,
            message_template="CPU is {cpu}%",
        )

        assert rule.name == "high_cpu"
        assert rule.level == AlertLevel.WARNING
        assert rule.enabled is True

    def test_rule_condition_check(self):
        """Test rule condition checking."""
        rule = AlertRule(
            name="high_cpu",
            condition=lambda d: d.get("cpu", 0) > 80,
            level=AlertLevel.WARNING,
            message_template="CPU is high",
            cooldown=timedelta(minutes=0),  # No cooldown for testing
        )

        # Should trigger
        assert rule.check_condition({"cpu": 90}) is True

        # Should not trigger
        assert rule.check_condition({"cpu": 50}) is False

    def test_rule_cooldown(self):
        """Test rule cooldown behavior."""
        rule = AlertRule(
            name="high_cpu",
            condition=lambda d: d.get("cpu", 0) > 80,
            level=AlertLevel.WARNING,
            message_template="CPU is high",
            cooldown=timedelta(minutes=5),
        )

        # First trigger
        assert rule.check_condition({"cpu": 90}) is True

        # Should not trigger due to cooldown
        assert rule.check_condition({"cpu": 95}) is False

    def test_rule_disabled(self):
        """Test disabled rule."""
        rule = AlertRule(
            name="test",
            condition=lambda d: True,
            level=AlertLevel.INFO,
            message_template="Test",
            enabled=False,
        )

        assert rule.check_condition({}) is False

    def test_message_formatting(self):
        """Test message template formatting."""
        rule = AlertRule(
            name="test",
            condition=lambda d: True,
            level=AlertLevel.INFO,
            message_template="Value is {value}",
        )

        message = rule.format_message({"value": 42})
        assert message == "Value is 42"


class TestAlertManager:
    """Test AlertManager class."""

    @pytest.fixture
    def manager(self):
        """Create an alert manager."""
        return AlertManager(max_alerts=100)

    def test_add_rule(self, manager):
        """Test adding a rule."""
        rule = AlertRule(
            name="test_rule",
            condition=lambda d: True,
            level=AlertLevel.INFO,
            message_template="Test",
        )

        manager.add_rule(rule)
        assert "test_rule" in manager.rules

    def test_remove_rule(self, manager):
        """Test removing a rule."""
        rule = AlertRule(
            name="test_rule",
            condition=lambda d: True,
            level=AlertLevel.INFO,
            message_template="Test",
        )

        manager.add_rule(rule)
        manager.remove_rule("test_rule")
        assert "test_rule" not in manager.rules

    def test_check_alerts_triggered(self, manager):
        """Test that alerts are triggered correctly."""
        rule = AlertRule(
            name="high_temp",
            condition=lambda d: d.get("temp", 0) > 100,
            level=AlertLevel.CRITICAL,
            message_template="Temperature is {temp}",
            cooldown=timedelta(minutes=0),
        )

        manager.add_rule(rule)

        # Trigger the rule
        triggered = manager.check_alerts({"temp": 110})

        assert len(triggered) == 1
        assert triggered[0].rule_name == "high_temp"
        assert triggered[0].level == AlertLevel.CRITICAL

    def test_check_alerts_not_triggered(self, manager):
        """Test that conditions below threshold don't trigger."""
        rule = AlertRule(
            name="high_temp",
            condition=lambda d: d.get("temp", 0) > 100,
            level=AlertLevel.CRITICAL,
            message_template="Temperature is {temp}",
        )

        manager.add_rule(rule)

        # Don't trigger
        triggered = manager.check_alerts({"temp": 50})

        assert len(triggered) == 0

    def test_get_active_alerts(self, manager):
        """Test getting active alerts."""
        # Create an alert manually
        alert = Alert(
            id="test-1",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test",
            timestamp=datetime.now(),
        )

        manager.alerts.append(alert)
        manager.active_alerts["test_rule"] = alert

        active = manager.get_active_alerts()
        assert len(active) == 1
        assert active[0].id == "test-1"

    def test_get_active_alerts_by_level(self, manager):
        """Test filtering active alerts by level."""
        for level in [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.CRITICAL]:
            alert = Alert(
                id=f"test-{level.value}",
                rule_name=f"rule_{level.value}",
                level=level,
                message="Test",
                timestamp=datetime.now(),
            )
            manager.alerts.append(alert)
            manager.active_alerts[f"rule_{level.value}"] = alert

        # Filter by WARNING
        warnings = manager.get_active_alerts(level=AlertLevel.WARNING)
        assert len(warnings) == 1
        assert warnings[0].level == AlertLevel.WARNING

    def test_resolve_alert(self, manager):
        """Test resolving an alert."""
        alert = Alert(
            id="test-1",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test",
            timestamp=datetime.now(),
        )

        manager.alerts.append(alert)
        manager.active_alerts["test_rule"] = alert

        # Resolve it
        success = manager.resolve_alert("test-1")
        assert success is True
        assert alert.is_active is False
        assert "test_rule" not in manager.active_alerts

    def test_resolve_nonexistent(self, manager):
        """Test resolving non-existent alert."""
        success = manager.resolve_alert("nonexistent")
        assert success is False

    def test_acknowledge_alert(self, manager):
        """Test acknowledging an alert."""
        alert = Alert(
            id="test-1",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test",
            timestamp=datetime.now(),
        )

        manager.alerts.append(alert)

        success = manager.acknowledge_alert("test-1")
        assert success is True
        assert alert.acknowledged is True

    def test_get_alert_by_id(self, manager):
        """Test getting alert by ID."""
        alert = Alert(
            id="test-1",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test",
            timestamp=datetime.now(),
        )

        manager.alerts.append(alert)

        found = manager.get_alert_by_id("test-1")
        assert found is not None
        assert found.id == "test-1"

        not_found = manager.get_alert_by_id("nonexistent")
        assert not_found is None

    def test_alert_history_limit(self, manager):
        """Test alert history respects max limit."""
        manager.max_alerts = 5

        for i in range(10):
            alert = Alert(
                id=f"test-{i}",
                rule_name="test_rule",
                level=AlertLevel.INFO,
                message=f"Test {i}",
                timestamp=datetime.now(),
            )
            manager.alerts.append(alert)

        history = manager.get_alert_history()
        assert len(history) == 5

    def test_duplicate_alert_prevention(self, manager):
        """Test that duplicate alerts aren't created for same rule."""
        rule = AlertRule(
            name="test_rule",
            condition=lambda d: True,
            level=AlertLevel.WARNING,
            message_template="Test",
            cooldown=timedelta(minutes=0),
        )

        manager.add_rule(rule)

        # First trigger
        triggered1 = manager.check_alerts({})
        assert len(triggered1) == 1

        # Should not trigger again while active
        triggered2 = manager.check_alerts({})
        assert len(triggered2) == 0


class TestAlertLevels:
    """Test alert level enum."""

    def test_info_level(self):
        """Test INFO level."""
        assert AlertLevel.INFO.value == "info"

    def test_warning_level(self):
        """Test WARNING level."""
        assert AlertLevel.WARNING.value == "warning"

    def test_critical_level(self):
        """Test CRITICAL level."""
        assert AlertLevel.CRITICAL.value == "critical"


class TestNotificationChannel:
    """Test notification channels."""

    @pytest.mark.asyncio
    async def test_log_notification_channel(self, caplog):
        """Test log notification channel."""
        channel = LogNotificationChannel()

        alert = Alert(
            id="test-1",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test message",
            timestamp=datetime.now(),
        )

        await channel.send(alert)
        # Should not raise exception
