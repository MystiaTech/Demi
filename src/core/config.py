import os
import yaml
from dataclasses import dataclass
from typing import Dict, Any, Optional


def _env_bool(key: str, default: bool) -> bool:
    """Get boolean environment variable with default"""
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes")


def _env_str(key: str, default: str) -> str:
    """Get string environment variable with default"""
    return os.getenv(key, default)


def _env_float(key: str, default: float) -> float:
    """Get float environment variable with default"""
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


@dataclass
class DemiConfig:
    system: Dict[str, Any]
    emotional_system: Dict[str, Any]
    platforms: Dict[str, Any]
    lm: Dict[str, Any]
    conductor: Dict[str, Any]
    dashboard: Dict[str, Any]

    @classmethod
    def load(cls, config_path: str = "src/core/defaults.yaml") -> "DemiConfig":
        """Load configuration from YAML with environment variable overrides"""
        # Ensure config_path is relative to project root
        if not os.path.isabs(config_path):
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), config_path
            )

        with open(config_path, "r") as f:
            defaults = yaml.safe_load(f) or {}

        # Override defaults with environment variables
        config = {
            "system": {
                **defaults.get("system", {}),
                "debug": _env_bool(
                    "DEMI_DEBUG", defaults.get("system", {}).get("debug", False)
                ),
                "log_level": _env_str(
                    "DEMI_LOG_LEVEL",
                    defaults.get("system", {}).get("log_level", "INFO"),
                ),
                "ram_threshold": int(
                    os.getenv(
                        "DEMI_RAM_THRESHOLD",
                        defaults.get("system", {}).get("ram_threshold", 80),
                    )
                ),
                "max_errors": int(
                    os.getenv(
                        "DEMI_MAX_ERRORS",
                        defaults.get("system", {}).get("max_errors", 5),
                    )
                ),
                "auto_recover": _env_bool(
                    "DEMI_AUTO_RECOVER",
                    defaults.get("system", {}).get("auto_recover", False),
                ),
                "data_dir": os.path.expanduser(
                    os.getenv(
                        "DEMI_DATA_DIR",
                        defaults.get("system", {}).get("data_dir", "~/.demi"),
                    )
                ),
            },
            "emotional_system": defaults.get("emotional_system", {}),
            "platforms": defaults.get("platforms", {}),
            "lm": defaults.get("lm", {}),
            "conductor": defaults.get("conductor", {}),
            "dashboard": {
                **defaults.get("dashboard", {}),
                "enabled": _env_bool(
                    "DEMI_DASHBOARD_ENABLED",
                    defaults.get("dashboard", {}).get("enabled", True),
                ),
                "host": _env_str(
                    "DEMI_DASHBOARD_HOST",
                    defaults.get("dashboard", {}).get("host", "0.0.0.0"),
                ),
                "port": int(
                    os.getenv(
                        "DEMI_DASHBOARD_PORT",
                        defaults.get("dashboard", {}).get("port", 8080),
                    )
                ),
                "auto_launch_browser": _env_bool(
                    "DEMI_DASHBOARD_AUTO_LAUNCH",
                    defaults.get("dashboard", {}).get("auto_launch_browser", True),
                ),
                "update_interval_sec": int(
                    os.getenv(
                        "DEMI_DASHBOARD_UPDATE_INTERVAL",
                        defaults.get("dashboard", {}).get("update_interval_sec", 5),
                    )
                ),
            },
        }
        return cls(**config)

    def update(self, section: str, key: str, value: Any):
        """Update a specific configuration value at runtime"""
        valid_sections = ["system", "emotional_system", "platforms", "lm", "conductor", "dashboard"]
        if section not in valid_sections:
            raise ValueError(f"Invalid configuration section: {section}")

        current_section = getattr(self, section)
        if isinstance(current_section, dict):
            current_section[key] = value
        else:
            raise TypeError(f"Section '{section}' is not a dictionary")

    def update_log_level(self, new_level: str):
        """Dynamically update system log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if new_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {new_level}")

        self.system["log_level"] = new_level.upper()
        # Trigger log reconfiguration
        try:
            from src.core.logger import reconfigure_logger

            reconfigure_logger(self)
        except ImportError:
            # Logger not yet initialized, skip reconfiguration
            pass
