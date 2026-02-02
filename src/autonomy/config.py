"""
Autonomy configuration management.

Provides Pydantic-based configuration with environment variable support.
"""

from typing import Optional


class TriggerThresholds:
    """Emotional trigger threshold settings."""

    def __init__(self, **kwargs):
        self.loneliness = kwargs.get("loneliness", 0.7)
        self.excitement = kwargs.get("excitement", 0.8)
        self.frustration = kwargs.get("frustration", 0.6)
        self.jealousy = kwargs.get("jealousy", 0.7)
        self.vulnerability = kwargs.get("vulnerability", 0.5)

        # Validate bounds
        for attr in [
            "loneliness",
            "excitement",
            "frustration",
            "jealousy",
            "vulnerability",
        ]:
            value = getattr(self, attr)
            setattr(self, attr, max(0.0, min(1.0, value)))


class TimingSettings:
    """Timing and interval settings."""

    def __init__(self, **kwargs):
        self.check_interval = kwargs.get("check_interval", 900)  # seconds
        self.cooldown_minutes = kwargs.get("cooldown_minutes", 60)  # minutes
        self.action_retry_delay = kwargs.get("action_retry_delay", 30)  # seconds

        # Validate bounds
        self.check_interval = max(60, min(3600, self.check_interval))
        self.cooldown_minutes = max(5, min(1440, self.cooldown_minutes))
        self.action_retry_delay = max(5, min(300, self.action_retry_delay))


class PlatformSettings:
    """Platform-specific settings."""

    def __init__(self, **kwargs):
        self.ramble_channel_id = kwargs.get("ramble_channel_id", None)
        self.discord_webhook_url = kwargs.get("discord_webhook_url", None)
        self.android_websocket_url = kwargs.get(
            "android_websocket_url", "ws://localhost:8765"
        )
        self.max_message_length = kwargs.get("max_message_length", 2000)

        # Validate bounds
        self.max_message_length = max(100, min(4000, self.max_message_length))


class SafetyLimits:
    """Safety and rate limiting settings."""

    def __init__(self, **kwargs):
        self.max_autonomous_per_hour = kwargs.get("max_autonomous_per_hour", 5)
        self.max_failed_attempts = kwargs.get("max_failed_attempts", 3)
        self.error_backoff_multiplier = kwargs.get("error_backoff_multiplier", 2.0)

        # Validate bounds
        self.max_autonomous_per_hour = max(1, min(20, self.max_autonomous_per_hour))
        self.max_failed_attempts = max(1, min(10, self.max_failed_attempts))
        self.error_backoff_multiplier = max(
            1.0, min(5.0, self.error_backoff_multiplier)
        )


class AutonomyConfig:
    """
    Configuration for autonomous behavior.

    Supports environment variable overrides and runtime updates.
    """

    def __init__(self, **kwargs):
        self.trigger_thresholds = TriggerThresholds(
            **kwargs.get("trigger_thresholds", {})
        )
        self.timing_settings = TimingSettings(**kwargs.get("timing_settings", {}))
        self.platform_settings = PlatformSettings(**kwargs.get("platform_settings", {}))
        self.safety_limits = SafetyLimits(**kwargs.get("safety_limits", {}))

        # Global settings
        self.enabled = kwargs.get("enabled", True)
        self.debug_mode = kwargs.get("debug_mode", False)

        # Validate configuration after initialization
        self._validate_config()
        # Validate configuration after initialization
        self._validate_config()

    def _validate_config(self):
        """Validate configuration consistency."""
        # Check that cooldown is reasonable for check interval
        if self.timing_settings.cooldown_minutes < (
            self.timing_settings.check_interval / 60
        ):
            # Ensure cooldown is at least one check interval
            self.timing_settings.cooldown_minutes = (
                self.timing_settings.check_interval / 60
            )

    def update_setting(self, path: str, value) -> bool:
        """
        Update a specific setting by path.

        Args:
            path: Dot-separated path to setting (e.g., 'trigger_thresholds.loneliness')
            value: New value

        Returns:
            True if updated successfully
        """
        try:
            parts = path.split(".")
            obj = self

            # Navigate to parent object
            for part in parts[:-1]:
                obj = getattr(obj, part)

            # Set the final value
            setattr(obj, parts[-1], value)

            # Re-validate
            self._validate_config()
            return True

        except Exception:
            return False

    def get_setting(self, path: str):
        """
        Get a specific setting by path.

        Args:
            path: Dot-separated path to setting

        Returns:
            Setting value or None if not found
        """
        try:
            parts = path.split(".")
            obj = self

            for part in parts:
                obj = getattr(obj, part)

            return obj

        except Exception:
            return None
