"""
Prometheus metrics collection system for health monitoring, circuit breaker tracking, and platform failure analysis.
"""

from typing import Dict, Optional, Callable, TYPE_CHECKING
import time
from contextlib import contextmanager

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        CollectorRegistry,
        generate_latest,
    )

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    # Type stubs for when prometheus_client is not available
    if TYPE_CHECKING:
        from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

from src.core.logger import logger


class MetricsRegistry:
    """Centralized Prometheus metrics registry for Demi's conductor system."""

    def __init__(self):
        """Initialize metrics registry with empty metrics dict."""
        self.registry: Dict[str, object] = {}
        self._prometheus_registry: Optional[CollectorRegistry] = None

        if HAS_PROMETHEUS:
            self._prometheus_registry = CollectorRegistry()
            self._init_prometheus_metrics()
        else:
            logger.warning(
                "prometheus_client not installed, metrics will be logged only"
            )

    def _init_prometheus_metrics(self):
        """Initialize all Prometheus metrics."""
        if not HAS_PROMETHEUS:
            return

        # Health check counter: total checks by platform and status
        self.registry["health_check_total"] = Counter(
            "health_check_total",
            "Total health checks performed",
            labelnames=["platform", "status"],
            registry=self._prometheus_registry,
        )

        # Health check duration histogram: response times by platform
        self.registry["health_check_duration_seconds"] = Histogram(
            "health_check_duration_seconds",
            "Health check duration in seconds",
            labelnames=["platform"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0),
            registry=self._prometheus_registry,
        )

        # Circuit breaker state gauge: current state per platform
        self.registry["circuit_breaker_state"] = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
            labelnames=["platform"],
            registry=self._prometheus_registry,
        )

        # Plugin failure counter: failures by platform and error type
        self.registry["plugin_failure_total"] = Counter(
            "plugin_failure_total",
            "Total plugin failures by platform and error type",
            labelnames=["platform", "error_type"],
            registry=self._prometheus_registry,
        )

        # System resource gauge: RAM and CPU usage
        self.registry["system_resources_percent"] = Gauge(
            "system_resources_percent",
            "System resource usage (RAM/CPU percentage)",
            labelnames=["resource"],
            registry=self._prometheus_registry,
        )

        logger.info("Prometheus metrics initialized", metrics_count=6)

    def get_counter(self, name: str) -> Optional["Counter"]:
        """Get a counter metric by name."""
        if not HAS_PROMETHEUS:
            return None
        return self.registry.get(name)

    def get_gauge(self, name: str) -> Optional["Gauge"]:
        """Get a gauge metric by name."""
        if not HAS_PROMETHEUS:
            return None
        return self.registry.get(name)

    def get_histogram(self, name: str) -> Optional["Histogram"]:
        """Get a histogram metric by name."""
        if not HAS_PROMETHEUS:
            return None
        return self.registry.get(name)

    @contextmanager
    def measure_duration(self, histogram_name: str, labels: Dict[str, str]):
        """Context manager to measure operation duration and record to histogram."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            histogram = self.get_histogram(histogram_name)
            if histogram:
                histogram.labels(**labels).observe(duration)

    def record_health_check(self, platform: str, status: str, duration_seconds: float):
        """Record a health check result."""
        # Record counter
        counter = self.get_counter("health_check_total")
        if counter:
            counter.labels(platform=platform, status=status).inc()

        # Record duration
        histogram = self.get_histogram("health_check_duration_seconds")
        if histogram:
            histogram.labels(platform=platform).observe(duration_seconds)

        logger.debug(
            "health_check_recorded",
            platform=platform,
            status=status,
            duration=duration_seconds,
        )

    def record_plugin_failure(self, platform: str, error_type: str):
        """Record a plugin failure."""
        counter = self.get_counter("plugin_failure_total")
        if counter:
            counter.labels(platform=platform, error_type=error_type).inc()

        logger.warning(
            "plugin_failure_recorded", platform=platform, error_type=error_type
        )

    def set_circuit_breaker_state(self, platform: str, state: int):
        """Set circuit breaker state gauge (0=CLOSED, 1=OPEN, 2=HALF_OPEN)."""
        gauge = self.get_gauge("circuit_breaker_state")
        if gauge:
            gauge.labels(platform=platform).set(state)

    def set_system_resource(self, resource: str, percentage: float):
        """Set system resource usage percentage."""
        gauge = self.get_gauge("system_resources_percent")
        if gauge:
            gauge.labels(resource=resource).set(percentage)

    def get_metrics_registry(self) -> Optional["CollectorRegistry"]:
        """Get Prometheus registry for scraping."""
        return self._prometheus_registry

    def export_metrics_text(self) -> Optional[str]:
        """Export metrics in Prometheus text format."""
        if not HAS_PROMETHEUS or not self._prometheus_registry:
            return None
        from prometheus_client import generate_latest

        return generate_latest(self._prometheus_registry).decode("utf-8")


# Global metrics instance
_metrics_instance: Optional[MetricsRegistry] = None


def init_metrics() -> MetricsRegistry:
    """Initialize global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsRegistry()
        logger.info("Global metrics registry initialized")
    return _metrics_instance


def get_metrics() -> MetricsRegistry:
    """Get global metrics instance, initializing if needed."""
    if _metrics_instance is None:
        return init_metrics()
    return _metrics_instance
