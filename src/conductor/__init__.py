"""
Conductor orchestrator system for Demi - manages health monitoring, circuit breakers, and integration management.
"""

from src.conductor.metrics import (
    MetricsRegistry,
    init_metrics,
    get_metrics as get_metrics_instance,
)
from src.conductor.circuit_breaker import (
    PlatformCircuitBreaker,
    CircuitBreakerManager,
    get_circuit_breaker_manager,
)
from src.conductor.health import (
    HealthMonitor,
    HealthStatus,
    HealthCheckResult,
    ResourceMetrics,
    get_health_monitor,
)


# Convenience function for getting the global metrics registry
def get_metrics_registry():
    """Get the global metrics registry instance."""
    return get_metrics_instance().get_metrics_registry()


__all__ = [
    # Metrics
    "MetricsRegistry",
    "init_metrics",
    "get_metrics_instance",
    "get_metrics_registry",
    # Circuit Breaker
    "PlatformCircuitBreaker",
    "CircuitBreakerManager",
    "get_circuit_breaker_manager",
    # Health Monitoring
    "HealthMonitor",
    "HealthStatus",
    "HealthCheckResult",
    "ResourceMetrics",
    "get_health_monitor",
]
