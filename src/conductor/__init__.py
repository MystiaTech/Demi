"""
Conductor orchestrator system for Demi - manages health monitoring, circuit breakers, and integration management.
"""

from src.conductor.metrics import (
    MetricsRegistry,
    init_metrics,
    get_metrics as get_metrics_instance,
)


# Convenience function for getting the global metrics registry
def get_metrics_registry():
    """Get the global metrics registry instance."""
    return get_metrics_instance().get_metrics_registry()


__all__ = [
    "MetricsRegistry",
    "init_metrics",
    "get_metrics_instance",
    "get_metrics_registry",
]
