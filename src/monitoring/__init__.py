"""Monitoring module for Demi.

Provides metrics collection, alerting, and dashboard for system health monitoring.
"""

from src.monitoring.metrics import (
    MetricType,
    Metric,
    MetricsCollector,
    get_metrics_collector,
)
from src.monitoring.alerts import (
    AlertLevel,
    AlertRule,
    Alert,
    AlertManager,
    get_alert_manager,
    NotificationChannel,
    LogNotificationChannel,
)
from src.monitoring.dashboard import Dashboard

__all__ = [
    # Metrics
    "MetricType",
    "Metric",
    "MetricsCollector",
    "get_metrics_collector",
    # Alerts
    "AlertLevel",
    "AlertRule",
    "Alert",
    "AlertManager",
    "get_alert_manager",
    "NotificationChannel",
    "LogNotificationChannel",
    # Dashboard
    "Dashboard",
]
__version__ = "1.0.0"
