"""Dashboard main module integrating all components.

Provides a high-level Dashboard class that coordinates metrics collection,
alert management, and the web dashboard server.
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from src.core.logger import get_logger
from src.monitoring.metrics import MetricsCollector, get_metrics_collector
from src.monitoring.alerts import AlertManager, get_alert_manager, AlertLevel
from src.monitoring.dashboard_server import DashboardServer

logger = get_logger()


class Dashboard:
    """Main dashboard class integrating all monitoring components.

    This class provides a unified interface for:
    - Metrics collection with SQLite persistence
    - Alert management with configurable rules
    - Web dashboard with real-time updates
    - Integration with Conductor for system access

    Example:
        ```python
        dashboard = Dashboard(host="localhost", port=8080)
        await dashboard.start()
        print(f"Dashboard available at: {dashboard.get_url()}")
        # ... run your application ...
        await dashboard.stop()
        ```
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        update_interval: int = 5,
        metrics_interval: int = 30,
        api_key: Optional[str] = None,
        enable_alerts: bool = True,
        enable_metrics_collection: bool = True,
    ):
        """Initialize the dashboard.

        Args:
            host: Host to bind the dashboard server to
            port: Port for the dashboard server
            update_interval: Seconds between dashboard updates
            metrics_interval: Seconds between metrics collection
            api_key: Optional API key for authentication
            enable_alerts: Whether to enable alert checking
            enable_metrics_collection: Whether to auto-start metrics collection
        """
        self.host = host
        self.port = port
        self.update_interval = update_interval
        self.metrics_interval = metrics_interval
        self.enable_alerts = enable_alerts
        self.enable_metrics_collection = enable_metrics_collection

        # Initialize components
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()
        self.server = DashboardServer(
            host=host,
            port=port,
            update_interval=update_interval,
            api_key=api_key,
        )

        # State
        self._running = False
        self._alert_task: Optional[asyncio.Task] = None
        self._start_time: Optional[datetime] = None

        logger.info(
            "Dashboard initialized",
            host=host,
            port=port,
            alerts_enabled=enable_alerts,
        )

    async def start(self):
        """Start the dashboard and all components.

        This starts:
        - Metrics collection (if enabled)
        - Alert checking loop (if enabled)
        - Dashboard web server
        """
        if self._running:
            logger.warning("Dashboard already running")
            return

        self._running = True
        self._start_time = datetime.now()

        # Start metrics collection
        if self.enable_metrics_collection:
            await self.metrics_collector.start_collection()
            logger.info("Metrics collection started")

        # Start alert checking
        if self.enable_alerts:
            self._alert_task = asyncio.create_task(self._alert_loop())
            logger.info("Alert checking started")

        # Register metrics callback for alert checking
        self.metrics_collector.register_callback(self._on_metric_recorded)

        logger.info("Dashboard started", url=self.get_url())

        # Start server (this blocks until stopped)
        await self.server.start()

    async def stop(self):
        """Stop the dashboard and all components gracefully."""
        if not self._running:
            return

        self._running = False

        # Stop server
        await self.server.stop()

        # Stop metrics collection
        if self.enable_metrics_collection:
            await self.metrics_collector.stop_collection()

        # Stop alert checking
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass

        # Unregister callback
        self.metrics_collector.unregister_callback(self._on_metric_recorded)

        logger.info("Dashboard stopped")

    def get_url(self) -> str:
        """Get the dashboard URL.

        Returns:
            URL string (e.g., "http://localhost:8080")
        """
        return self.server.get_url()

    async def _alert_loop(self):
        """Background loop for checking alert conditions."""
        while self._running:
            try:
                await self._check_alerts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Alert loop error", error=str(e))
                await asyncio.sleep(30)

    async def _check_alerts(self):
        """Check all alert rules against current system state."""
        try:
            # Gather current system state
            data = await self._gather_system_state()

            # Check alerts
            triggered = self.alert_manager.check_alerts(data)

            if triggered:
                logger.info(
                    f"Triggered {len(triggered)} alert(s)",
                    alerts=[a.rule_name for a in triggered],
                )

        except Exception as e:
            logger.error("Alert check failed", error=str(e))

    async def _gather_system_state(self) -> Dict[str, Any]:
        """Gather current system state for alert checking.

        Returns:
            Dictionary with current metrics, emotions, and platform status
        """
        data = {}

        # Get latest metrics
        latest_metrics = [
            "memory_percent",
            "memory_used_gb",
            "cpu_percent",
            "disk_percent",
            "response_time_p90",
        ]

        for metric_name in latest_metrics:
            metric = self.metrics_collector.get_latest(metric_name)
            if metric:
                data[metric_name] = metric.value

        # Get emotions
        emotions = {}
        emotion_names = [
            "loneliness",
            "excitement",
            "frustration",
            "jealousy",
            "vulnerability",
            "confidence",
            "curiosity",
            "affection",
            "defensiveness",
        ]

        for emotion in emotion_names:
            metric = self.metrics_collector.get_latest(f"emotion_{emotion}")
            if metric:
                emotions[emotion] = metric.value

        if emotions:
            data["emotions"] = emotions

        # Count unhealthy platforms
        try:
            from src.conductor.health import get_health_monitor

            health_monitor = get_health_monitor()
            statuses = health_monitor.get_all_statuses()
            unhealthy = sum(
                1 for s in statuses.values() if s.status.value != "healthy"
            )
            data["unhealthy_platforms"] = unhealthy
            data["platforms"] = {
                name: {"status": s.status.value} for name, s in statuses.items()
            }
        except Exception as e:
            logger.debug("Could not get platform health", error=str(e))

        return data

    def _on_metric_recorded(self, metric):
        """Callback when a metric is recorded.

        Args:
            metric: The recorded Metric object
        """
        # Could trigger real-time alert evaluation here
        pass

    def record_emotion(self, emotion_name: str, value: float):
        """Record an emotion metric.

        Args:
            emotion_name: Name of the emotion
            value: Emotion value (0.0-1.0)
        """
        from src.monitoring.metrics import MetricType
        self.metrics_collector.record(
            name=f"emotion_{emotion_name}",
            value=value,
            metric_type=MetricType.GAUGE,
        )

    def record_response_time(self, duration_seconds: float):
        """Record an API response time.

        Args:
            duration_seconds: Response time in seconds
        """
        from src.monitoring.metrics import MetricType
        self.metrics_collector.record(
            name="response_time",
            value=duration_seconds,
            metric_type=MetricType.HISTOGRAM,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics.

        Returns:
            Dictionary with dashboard statistics
        """
        uptime = None
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()

        return {
            "running": self._running,
            "url": self.get_url(),
            "uptime_seconds": uptime,
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "total_alerts": len(self.alert_manager.alerts),
            "metrics_count": len(self.metrics_collector.get_all_metric_names()),
            "websocket_connections": len(self.server.websocket_connections),
        }


# Convenience function for starting the dashboard
async def start_dashboard(
    host: str = "localhost",
    port: int = 8080,
    **kwargs
) -> Dashboard:
    """Start the dashboard.

    Args:
        host: Host to bind to
        port: Port to listen on
        **kwargs: Additional arguments for Dashboard

    Returns:
        Running Dashboard instance
    """
    dashboard = Dashboard(host=host, port=port, **kwargs)
    # Start in background
    asyncio.create_task(dashboard.start())
    return dashboard


# Backwards compatibility alias
HealthDashboard = Dashboard
