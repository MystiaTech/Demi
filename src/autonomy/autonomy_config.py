"""
AutonomyConfig - Configuration management for Demi's self-modification system.

Centralized configuration for all self-modification capabilities including
safety settings, rate limits, and feature toggles.
"""

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional, Any
import json

from src.core.logger import get_logger

logger = get_logger()


@dataclass
class SelfModificationConfig:
    """Configuration for self-modification capabilities."""
    
    # Feature toggles
    enabled: bool = True
    auto_apply_low_risk: bool = False  # Auto-apply low-risk changes
    require_human_approval: bool = True  # Require approval for changes
    enable_git_integration: bool = True
    enable_validation: bool = True
    enable_emergency_healing: bool = True
    
    # Rate limiting
    max_modifications_per_hour: int = 10
    max_modifications_per_day: int = 50
    cooldown_seconds: int = 30
    
    # Safety settings
    safety_level: str = "normal"  # permissive, normal, restrictive, lockdown
    max_consecutive_failures: int = 5
    critical_file_protection: bool = True
    pattern_detection: bool = True
    
    # Git settings
    auto_commit: bool = True
    auto_merge: bool = False  # Auto-merge to main (dangerous)
    branch_prefix: str = "demi/autonomy"
    commit_author_name: str = "Demi"
    commit_author_email: str = "self@demi.ai"
    
    # Validation settings
    run_syntax_check: bool = True
    run_import_check: bool = True
    run_unit_tests: bool = True
    run_smoke_test: bool = True
    test_timeout_seconds: int = 60
    
    # Emergency healing
    auto_heal: bool = True
    max_healing_attempts_per_day: int = 3
    healing_cooldown_minutes: int = 30
    
    # Notification settings
    notify_on_change: bool = True
    notify_on_failure: bool = True
    notify_on_healing: bool = True


class AutonomyConfigManager:
    """
    Manage configuration for Demi's autonomy system.
    
    Loads from:
    1. Default values
    2. Config file (~/.demi/autonomy_config.json)
    3. Environment variables (DEMI_AUTONOMY_*)
    
    Usage:
        config_mgr = AutonomyConfigManager()
        config = config_mgr.get_config()
        
        if config.enabled:
            # Proceed with self-modification
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to config file (default: ~/.demi/autonomy_config.json)
        """
        self.config_path = Path(config_path or self._default_config_path())
        self._config: Optional[SelfModificationConfig] = None
        
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AutonomyConfigManager initialized: {self.config_path}")
    
    def _default_config_path(self) -> str:
        """Get default config file path."""
        return os.path.expanduser("~/.demi/autonomy_config.json")
    
    def get_config(self) -> SelfModificationConfig:
        """
        Get current configuration (loads if not cached).
        
        Returns:
            SelfModificationConfig with merged settings
        """
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> SelfModificationConfig:
        """Load configuration from all sources."""
        # Start with defaults
        config = SelfModificationConfig()
        
        # Load from file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_data = json.load(f)
                config = self._merge_dict_into_config(config, file_data)
                logger.debug("Loaded autonomy config from file")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
        
        # Override with environment variables
        config = self._apply_env_overrides(config)
        
        return config
    
    def _merge_dict_into_config(
        self,
        config: SelfModificationConfig,
        data: Dict
    ) -> SelfModificationConfig:
        """Merge dictionary data into config object."""
        config_dict = asdict(config)
        config_dict.update(data)
        
        # Filter to only valid fields
        valid_fields = {f for f in SelfModificationConfig.__dataclass_fields__}
        filtered = {k: v for k, v in config_dict.items() if k in valid_fields}
        
        return SelfModificationConfig(**filtered)
    
    def _apply_env_overrides(self, config: SelfModificationConfig) -> SelfModificationConfig:
        """Apply environment variable overrides."""
        env_mappings = {
            "DEMI_AUTONOMY_ENABLED": ("enabled", bool),
            "DEMI_AUTONOMY_AUTO_APPLY": ("auto_apply_low_risk", bool),
            "DEMI_AUTONOMY_REQUIRE_APPROVAL": ("require_human_approval", bool),
            "DEMI_AUTONOMY_GIT_ENABLED": ("enable_git_integration", bool),
            "DEMI_AUTONOMY_VALIDATION": ("enable_validation", bool),
            "DEMI_AUTONOMY_HEALING": ("enable_emergency_healing", bool),
            "DEMI_AUTONOMY_SAFETY_LEVEL": ("safety_level", str),
            "DEMI_AUTONOMY_MAX_PER_HOUR": ("max_modifications_per_hour", int),
            "DEMI_AUTONOMY_MAX_PER_DAY": ("max_modifications_per_day", int),
            "DEMI_AUTONOMY_COOLDOWN": ("cooldown_seconds", int),
            "DEMI_AUTONOMY_AUTO_COMMIT": ("auto_commit", bool),
            "DEMI_AUTONOMY_AUTO_MERGE": ("auto_merge", bool),
        }
        
        config_dict = asdict(config)
        
        for env_var, (field_name, field_type) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert type
                if field_type == bool:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif field_type == int:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                
                config_dict[field_name] = value
                logger.debug(f"Config override from env: {field_name}={value}")
        
        return SelfModificationConfig(**config_dict)
    
    def save_config(self, config: Optional[SelfModificationConfig] = None):
        """
        Save configuration to file.
        
        Args:
            config: Config to save (uses current if None)
        """
        if config is None:
            config = self.get_config()
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(asdict(config), f, indent=2)
            logger.info(f"Saved autonomy config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def update_config(self, **kwargs):
        """
        Update specific configuration values.
        
        Args:
            **kwargs: Config fields to update
        """
        config = self.get_config()
        config_dict = asdict(config)
        
        for key, value in kwargs.items():
            if key in config_dict:
                config_dict[key] = value
                logger.info(f"Config updated: {key}={value}")
            else:
                logger.warning(f"Unknown config field: {key}")
        
        self._config = SelfModificationConfig(**config_dict)
        self.save_config(self._config)
    
    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self._config = SelfModificationConfig()
        self.save_config(self._config)
        logger.info("Config reset to defaults")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        config = self.get_config()
        
        return {
            "enabled": config.enabled,
            "safety_level": config.safety_level,
            "auto_apply_low_risk": config.auto_apply_low_risk,
            "require_human_approval": config.require_human_approval,
            "git_integration": config.enable_git_integration,
            "validation_enabled": config.enable_validation,
            "emergency_healing": config.enable_emergency_healing,
            "rate_limits": {
                "per_hour": config.max_modifications_per_hour,
                "per_day": config.max_modifications_per_day,
                "cooldown_seconds": config.cooldown_seconds,
            },
            "config_file": str(self.config_path),
            "file_exists": self.config_path.exists(),
        }


# Global instance
_config_manager: Optional[AutonomyConfigManager] = None


def get_autonomy_config() -> SelfModificationConfig:
    """Get global autonomy configuration."""
    global _config_manager
    if _config_manager is None:
        _config_manager = AutonomyConfigManager()
    return _config_manager.get_config()


def get_autonomy_config_manager() -> AutonomyConfigManager:
    """Get global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = AutonomyConfigManager()
    return _config_manager
