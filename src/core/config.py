import os
import yaml
from environs import Env
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DemiConfig:
    system: Dict[str, Any]
    emotional_system: Dict[str, Any]
    platforms: Dict[str, Any]

    @classmethod
    def load(cls, config_path="src/core/defaults.yaml"):
        """Load configuration from YAML with environment variable overrides"""
        # Ensure config_path is relative to project root
        if not os.path.isabs(config_path):
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), config_path
            )

        with open(config_path, "r") as f:
            defaults = yaml.safe_load(f)

        env = Env()
        # Override defaults with environment variables
        config = {
            "system": {
                **defaults["system"],
                "debug": env.bool("DEMI_DEBUG", defaults["system"]["debug"]),
                "log_level": env.str("DEMI_LOG_LEVEL", defaults["system"]["log_level"]),
            },
            "emotional_system": {
                **defaults["emotional_system"],
                "decay_rates": {
                    **defaults["emotional_system"]["decay_rates"],
                    "loneliness": env.float(
                        "DEMI_LONELINESS_DECAY",
                        defaults["emotional_system"]["decay_rates"]["loneliness"],
                    ),
                },
            },
            "platforms": {
                **defaults["platforms"],
                "discord": {
                    **defaults["platforms"]["discord"],
                    "enabled": env.bool(
                        "DEMI_DISCORD_ENABLED",
                        defaults["platforms"]["discord"]["enabled"],
                    ),
                },
                "android": {
                    **defaults["platforms"]["android"],
                    "enabled": env.bool(
                        "DEMI_ANDROID_ENABLED",
                        defaults["platforms"]["android"]["enabled"],
                    ),
                },
            },
        }
        return cls(**config)

    def update(self, section: str, key: str, value: Any):
        """Update a specific configuration value at runtime"""
        if section not in ["system", "emotional_system", "platforms"]:
            raise ValueError(f"Invalid configuration section: {section}")

        current_section = getattr(self, section)
        current_section[key] = value
        setattr(self, section, current_section)

    def update_log_level(self, new_level: str):
        """Dynamically update system log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if new_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {new_level}")

        self.system["log_level"] = new_level.upper()
        # Trigger log reconfiguration
        from src.core.logger import configure_logger

        configure_logger(self)
