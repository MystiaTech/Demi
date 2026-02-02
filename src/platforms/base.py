"""Abstract base class for platform integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class PluginHealth:
    """Health status information for a platform plugin."""

    status: str  # "healthy", "degraded", "unhealthy"
    response_time_ms: float
    last_check: datetime
    error_message: Optional[str] = None

    def is_healthy(self) -> bool:
        """Check if plugin is healthy."""
        return self.status == "healthy"


class BasePlatform(ABC):
    """Abstract base class for all platform integrations.

    All platform plugins must inherit from this class and implement
    the required abstract methods for proper lifecycle management.
    """

    def __init__(self):
        """Initialize platform."""
        self._initialized = False
        self._name: str = ""
        self._status: str = "offline"

    @property
    def name(self) -> str:
        """Get platform name."""
        return self._name

    @property
    def status(self) -> str:
        """Get current platform status."""
        return self._status

    @abstractmethod
    def initialize(self, config: dict) -> bool:
        """Initialize platform with configuration.

        Args:
            config: Configuration dictionary for this platform

        Returns:
            True if initialization successful, False otherwise
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Clean shutdown of platform.

        Called when platform is being unloaded or system is shutting down.
        Should clean up resources, connections, etc.
        """

    @abstractmethod
    def health_check(self) -> PluginHealth:
        """Perform health check on this platform.

        Returns:
            PluginHealth object with current status
        """

    @abstractmethod
    def handle_request(self, request: dict) -> dict:
        """Handle a request from this platform.

        Args:
            request: Request dict with 'type' and other parameters

        Returns:
            Response dict with 'status' and result data
        """
