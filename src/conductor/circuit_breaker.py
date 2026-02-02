"""
Circuit breaker protection system for platform integrations.
Prevents cascading failures by detecting unhealthy platforms and opening circuit.
"""

from enum import IntEnum
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    from aiobreaker import CircuitBreaker as AioBreakerCircuitBreaker

    HAS_AIOBREAKER = True
except ImportError:
    HAS_AIOBREAKER = False

from src.core.logger import logger


class CircuitBreakerState(IntEnum):
    """Circuit breaker states."""

    CLOSED = 0  # Normal operation, requests pass through
    OPEN = 1  # Too many failures, block requests
    HALF_OPEN = 2  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    fail_max: int = 3  # Failures to trigger open
    reset_timeout: float = 30.0  # Seconds before attempting recovery
    name: str = "unknown"


class PlatformCircuitBreaker:
    """
    Circuit breaker for individual platform integrations.
    Protects against cascading failures by blocking requests to failing services.
    """

    def __init__(self, platform: str, fail_max: int = 3, reset_timeout: float = 30.0):
        """
        Initialize circuit breaker for a platform.

        Args:
            platform: Platform name (e.g., 'discord', 'twitch')
            fail_max: Number of consecutive failures to trigger OPEN state
            reset_timeout: Seconds to wait before trying HALF_OPEN state
        """
        self.platform = platform
        self.config = CircuitBreakerConfig(
            fail_max=fail_max, reset_timeout=reset_timeout, name=platform
        )

        # State tracking
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._opened_at: Optional[float] = None

        logger.info(
            "circuit_breaker_created",
            platform=platform,
            fail_max=fail_max,
            reset_timeout=reset_timeout,
        )

    def record_success(self):
        """Record a successful request through the circuit breaker."""
        self._success_count += 1
        self._last_success_time = time.time()

        # If half-open and success, close the circuit
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._close()
            logger.info(
                "circuit_breaker_recovered",
                platform=self.platform,
                success_count=self._success_count,
            )
        elif self._state == CircuitBreakerState.CLOSED:
            # Reset failure count on success during normal operation
            self._failure_count = 0

    def record_failure(self):
        """Record a failed request through the circuit breaker."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        logger.warning(
            "circuit_breaker_failure_recorded",
            platform=self.platform,
            failure_count=self._failure_count,
            threshold=self.config.fail_max,
        )

        # If failures exceed threshold, open the circuit
        if self._failure_count >= self.config.fail_max:
            self._open()

    def can_execute(self) -> bool:
        """Check if request can pass through circuit breaker."""
        if self._state == CircuitBreakerState.CLOSED:
            return True

        if self._state == CircuitBreakerState.OPEN:
            # Check if reset timeout has elapsed
            if (
                self._opened_at
                and time.time() - self._opened_at >= self.config.reset_timeout
            ):
                self._enter_half_open()
                return True
            return False

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Allow request in half-open state to test recovery
            return True

        return False

    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "platform": self.platform,
            "state": self._state.name,
            "state_code": int(self._state),
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
            "opened_at": self._opened_at,
            "can_execute": self.can_execute(),
        }

    def _open(self):
        """Transition to OPEN state."""
        self._state = CircuitBreakerState.OPEN
        self._opened_at = time.time()
        logger.error(
            "circuit_breaker_opened",
            platform=self.platform,
            failure_count=self._failure_count,
        )

    def _close(self):
        """Transition to CLOSED state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None
        logger.info("circuit_breaker_closed", platform=self.platform)

    def _enter_half_open(self):
        """Transition to HALF_OPEN state."""
        self._state = CircuitBreakerState.HALF_OPEN
        self._failure_count = 0  # Reset failure count for testing
        logger.warning(
            "circuit_breaker_half_open",
            platform=self.platform,
            testing_recovery=True,
        )


class CircuitBreakerManager:
    """Manages circuit breakers for all platforms."""

    def __init__(self):
        """Initialize circuit breaker manager."""
        self._breakers: dict[str, PlatformCircuitBreaker] = {}

    def get_breaker(self, platform: str) -> PlatformCircuitBreaker:
        """Get or create circuit breaker for a platform."""
        if platform not in self._breakers:
            self._breakers[platform] = PlatformCircuitBreaker(platform)
        return self._breakers[platform]

    def record_success(self, platform: str):
        """Record successful request for a platform."""
        self.get_breaker(platform).record_success()

    def record_failure(self, platform: str):
        """Record failed request for a platform."""
        self.get_breaker(platform).record_failure()

    def can_execute(self, platform: str) -> bool:
        """Check if request can execute for a platform."""
        return self.get_breaker(platform).can_execute()

    def get_state(self, platform: str) -> dict:
        """Get circuit breaker state for a platform."""
        return self.get_breaker(platform).get_state()

    def get_all_states(self) -> dict[str, dict]:
        """Get all circuit breaker states."""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}

    def reset_breaker(self, platform: str):
        """Force reset a circuit breaker to CLOSED state."""
        if platform in self._breakers:
            self._breakers[platform]._close()
            logger.info("circuit_breaker_reset", platform=platform)


# Global circuit breaker manager instance
_manager_instance: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager, creating if needed."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = CircuitBreakerManager()
        logger.info("circuit_breaker_manager_initialized")
    return _manager_instance
