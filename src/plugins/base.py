"""Plugin state management and metadata."""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, Any


class PluginState(Enum):
    """Plugin lifecycle states."""

    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNLOADING = "unloading"


@dataclass
class PluginMetadata:
    """Metadata for a loaded plugin instance."""

    name: str
    state: PluginState
    plugin_class: type
    instance: Any = None
    config: dict = field(default_factory=dict)
    loaded_at: Optional[datetime] = None
    error_message: Optional[str] = None
    health_status: str = "unknown"
    last_health_check: Optional[datetime] = None

    def is_loaded(self) -> bool:
        """Check if plugin is currently loaded."""
        return self.state in (
            PluginState.LOADED,
            PluginState.ACTIVE,
            PluginState.INACTIVE,
        )

    def is_active(self) -> bool:
        """Check if plugin is active and ready."""
        return self.state == PluginState.ACTIVE
