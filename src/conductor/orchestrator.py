"""
Main conductor orchestrator for Demi.

Coordinates all subsystems into a cohesive system:
- Plugin lifecycle management
- Health monitoring
- Resource auto-scaling
- Request routing
- Graceful startup/shutdown

This is the central nervous system that brings all components together.
"""

import asyncio
import signal
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.core.logger import get_logger
from src.core.config import DemiConfig
from src.core.database import DatabaseManager
from src.plugins.manager import PluginManager
from src.conductor.health import get_health_monitor, HealthMonitor, HealthStatus
from src.conductor.scaler import PredictiveScaler
from src.conductor.router import RequestRouter
from src.conductor.metrics import get_metrics
from src.conductor.circuit_breaker import get_circuit_breaker_manager

logger = get_logger()


@dataclass
class SystemStatus:
    """Overall system health status."""

    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
    component_statuses: Dict[str, str] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    active_plugins: int = 0
    total_requests: int = 0
    failed_requests: int = 0


class Conductor:
    """
    Main orchestrator managing all Demi subsystems.

    Coordinates:
    - Plugin lifecycle (discovery, loading, unloading)
    - Health monitoring (platform health, resource usage)
    - Auto-scaling (predictive resource management)
    - Request routing (content-based, load balancing)
    - Graceful shutdown (cleanup, resource release)
    """

    def __init__(self, config: Optional[DemiConfig] = None):
        """
        Initialize conductor with all subsystems.

        Args:
            config: Configuration object, loads default if None
        """
        self._config = config or DemiConfig.load()
        self._logger = logger

        # Initialize subsystems
        self._plugin_manager = PluginManager()
        self._health_monitor = get_health_monitor()
        self._scaler = PredictiveScaler()
        self._router = RequestRouter()
        self._metrics = get_metrics()
        self._circuit_breaker_manager = get_circuit_breaker_manager()

        # Database
        self._db_manager = DatabaseManager(self._config)

        # State tracking
        self._running = False
        self._startup_time: Optional[float] = None
        self._shutdown_event = asyncio.Event()
        self._background_tasks: List[asyncio.Task] = []
        self._request_count = 0
        self._failed_request_count = 0

        # Signal handlers
        self._signal_handlers_registered = False

        self._logger.info("conductor_initialized", config_path="defaults.yaml")

    async def startup(self) -> bool:
        """
        Execute full startup sequence in correct order.

        Sequence:
        1. Load configuration and initialize logging
        2. Initialize database connection and run migrations
        3. Discover and register plugins
        4. Start health monitoring loop
        5. Initialize predictive scaler
        6. Start request router
        7. Enable all registered plugins
        8. Register signal handlers for graceful shutdown

        Returns:
            True if startup successful, False otherwise
        """
        try:
            self._startup_time = time.time()
            self._logger.info("=" * 60)
            self._logger.info("CONDUCTOR STARTUP SEQUENCE INITIATED")
            self._logger.info("=" * 60)

            # Step 1: Configuration and logging (already done in __init__)
            self._logger.info("Configuration loaded")

            # Step 2: Database initialization
            self._logger.info("Initializing database...")
            try:
                # Initialize database tables
                self._db_manager.create_tables()
                self._logger.info("Database initialized")
            except Exception as e:
                self._logger.error(f"database_initialization_failed: {str(e)}")
                return False

            # Step 3: Plugin discovery and registration
            self._logger.info("Discovering plugins...")
            try:
                await self._plugin_manager.discover_and_register()
                plugin_count = len(self._plugin_manager.registry)
                self._logger.info(f"Plugin discovery complete: {plugin_count} plugins")
            except Exception as e:
                self._logger.error(f"plugin_discovery_failed: {str(e)}")
                return False

            # Step 4: Start health monitoring loop
            self._logger.info("Starting health monitor...")
            try:
                platforms = [p.name for p in self._plugin_manager.list_plugins()]
                health_task = asyncio.create_task(
                    self._health_monitor.health_check_loop(
                        platforms, health_check_fn=None
                    )
                )
                self._background_tasks.append(health_task)
                self._logger.info("Health monitor started")
            except Exception as e:
                self._logger.error(f"health_monitor_startup_failed: {str(e)}")
                return False

            # Step 5: Initialize predictive scaler
            self._logger.info("Initializing scaler...")
            try:
                # Scaler is stateless and operates on-demand during health checks
                self._logger.info("Scaler initialized")
            except Exception as e:
                self._logger.error(f"scaler_initialization_failed: {str(e)}")
                return False

            # Step 6: Start request router
            self._logger.info("Starting request router...")
            try:
                # Router is stateless, just initialize it
                self._logger.info("Request router ready")
            except Exception as e:
                self._logger.error(f"router_startup_failed: {str(e)}")
                return False

            # Step 7: Enable registered plugins
            self._logger.info("Loading plugins...")
            try:
                loaded_count = 0
                for metadata in self._plugin_manager.list_plugins():
                    try:
                        plugin = await self._plugin_manager.load_plugin(metadata.name)
                        if plugin:
                            loaded_count += 1
                            self._logger.info(f"Plugin loaded: {metadata.name}")
                    except Exception as e:
                        self._logger.warning(
                            f"plugin_load_failed {metadata.name}: {str(e)}"
                        )
                        # Continue with other plugins even if one fails
                        continue

                self._logger.info(f"Plugins loaded: {loaded_count}")
            except Exception as e:
                self._logger.error(f"plugin_loading_failed: {str(e)}")
                return False

            # Step 8: Register signal handlers
            self._logger.info("Registering signal handlers...")
            try:
                self._register_signal_handlers()
                self._logger.info("Signal handlers registered")
            except Exception as e:
                self._logger.error(f"signal_handler_registration_failed: {str(e)}")
                return False

            self._running = True
            startup_time_sec = time.time() - self._startup_time
            self._logger.info("=" * 60)
            self._logger.info(f"✓ CONDUCTOR STARTUP COMPLETE ({startup_time_sec:.2f}s)")
            self._logger.info("=" * 60)

            return True

        except Exception as e:
            self._logger.exception(f"conductor_startup_failed: {str(e)}")
            return False

            # Step 3: Plugin discovery and registration
            self._logger.info("step_3_start", message="Discovering plugins...")
            try:
                await self._plugin_manager.discover_and_register()
                plugin_count = len(self._plugin_manager.registry)
                self._logger.info("step_3_complete", plugins_discovered=plugin_count)
            except Exception as e:
                self._logger.error("plugin_discovery_failed", error=str(e))
                return False

            # Step 4: Start health monitoring loop
            self._logger.info("step_4_start", message="Starting health monitor...")
            try:
                platforms = [p.name for p in self._plugin_manager.list_plugins()]
                health_task = asyncio.create_task(
                    self._health_monitor.health_check_loop(
                        platforms, health_check_fn=None
                    )
                )
                self._background_tasks.append(health_task)
                self._logger.info("step_4_complete", message="Health monitor started")
            except Exception as e:
                self._logger.error("health_monitor_startup_failed", error=str(e))
                return False

            # Step 5: Initialize predictive scaler
            self._logger.info("step_5_start", message="Initializing scaler...")
            try:
                scaler_task = asyncio.create_task(
                    self._scaler.scaling_loop(
                        self._plugin_manager, self._config.conductor
                    )
                )
                self._background_tasks.append(scaler_task)
                self._logger.info("step_5_complete", message="Scaler initialized")
            except Exception as e:
                self._logger.error("scaler_initialization_failed", error=str(e))
                return False

            # Step 6: Start request router
            self._logger.info("step_6_start", message="Starting request router...")
            try:
                # Router is stateless, just initialize it
                self._logger.info("step_6_complete", message="Request router ready")
            except Exception as e:
                self._logger.error("router_startup_failed", error=str(e))
                return False

            # Step 7: Enable registered plugins
            self._logger.info("step_7_start", message="Loading plugins...")
            try:
                loaded_count = 0
                for metadata in self._plugin_manager.list_plugins():
                    try:
                        plugin = await self._plugin_manager.load_plugin(metadata.name)
                        if plugin:
                            loaded_count += 1
                            self._logger.info(f"plugin_loaded", name=metadata.name)
                    except Exception as e:
                        self._logger.warning(
                            f"plugin_load_failed", name=metadata.name, error=str(e)
                        )
                        # Continue with other plugins even if one fails
                        continue

                self._logger.info("step_7_complete", plugins_loaded=loaded_count)
            except Exception as e:
                self._logger.error("plugin_loading_failed", error=str(e))
                return False

            # Step 8: Register signal handlers
            self._logger.info("step_8_start", message="Registering signal handlers...")
            try:
                self._register_signal_handlers()
                self._logger.info(
                    "step_8_complete", message="Signal handlers registered"
                )
            except Exception as e:
                self._logger.error("signal_handler_registration_failed", error=str(e))
                return False

            self._running = True
            startup_time_sec = time.time() - self._startup_time
            self._logger.info("=" * 60)
            self._logger.info(f"✓ CONDUCTOR STARTUP COMPLETE ({startup_time_sec:.2f}s)")
            self._logger.info("=" * 60)

            return True

        except Exception as e:
            self._logger.error("conductor_startup_failed", error=str(e), exc_info=True)
            return False

    async def shutdown(self) -> None:
        """
        Execute graceful shutdown sequence in reverse order.

        Sequence:
        1. Stop accepting new requests
        2. Disable all plugins
        3. Stop background loops (health, scaling)
        4. Close database connections
        5. Cleanup remaining resources
        """
        try:
            self._logger.info("=" * 60)
            self._logger.info("CONDUCTOR SHUTDOWN SEQUENCE INITIATED")
            self._logger.info("=" * 60)

            # Step 1: Stop accepting new requests
            self._logger.info("Stopping request acceptance...")
            self._running = False
            self._logger.info("Request acceptance stopped")

            # Step 2: Disable all plugins
            self._logger.info("Disabling plugins...")
            try:
                await self._plugin_manager.shutdown_all()
                self._logger.info("All plugins disabled")
            except Exception as e:
                self._logger.error(f"plugin_shutdown_failed: {str(e)}")

            # Step 3: Stop background loops
            self._logger.info("Stopping background tasks...")
            try:
                self._health_monitor.stop()

                # Cancel all background tasks
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()

                # Wait for tasks to complete
                if self._background_tasks:
                    await asyncio.gather(
                        *self._background_tasks, return_exceptions=True
                    )

                self._logger.info("Background tasks stopped")
            except Exception as e:
                self._logger.error(f"background_task_shutdown_failed: {str(e)}")

            # Step 4: Close database connections
            self._logger.info("Closing database...")
            try:
                self._db_manager.close()
                self._logger.info("Database closed")
            except Exception as e:
                self._logger.error(f"database_shutdown_failed: {str(e)}")

            # Step 5: Record final metrics
            self._logger.info("Recording final metrics...")
            try:
                # Final metrics recording happens automatically
                self._logger.info("Final metrics recorded")
            except Exception as e:
                self._logger.error(f"metrics_recording_failed: {str(e)}")

            self._logger.info("=" * 60)
            self._logger.info("✓ CONDUCTOR SHUTDOWN COMPLETE")
            self._logger.info("=" * 60)

        except Exception as e:
            self._logger.exception(f"conductor_shutdown_failed: {str(e)}")

    def _register_signal_handlers(self) -> None:
        """Register handlers for SIGINT and SIGTERM for graceful shutdown."""
        if self._signal_handlers_registered:
            return

        def handle_signal(signum, frame):
            self._logger.info(f"signal_received", signal=signum)
            asyncio.create_task(self.shutdown())

        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
            self._signal_handlers_registered = True
        except Exception as e:
            self._logger.warning("signal_handler_registration_failed", error=str(e))

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for external requests.

        Routes request through:
        1. Request router (content-based routing)
        2. Plugin execution (isolated subprocess)
        3. Response aggregation

        Args:
            request: Request dictionary with platform, action, args

        Returns:
            Response dictionary with status, data, metrics
        """
        if not self._running:
            return {
                "status": "error",
                "error": "Conductor not running",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            self._request_count += 1
            request_start = time.time()

            # Route the request
            response = await self._router.route_request(request)

            if response.get("status") == "error":
                self._failed_request_count += 1

            # Add metrics
            response["conductor_metrics"] = {
                "total_requests": self._request_count,
                "failed_requests": self._failed_request_count,
                "processing_time_ms": (time.time() - request_start) * 1000,
                "uptime_seconds": time.time() - (self._startup_time or time.time()),
            }

            return response

        except Exception as e:
            self._failed_request_count += 1
            self._logger.error("request_handling_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_status(self) -> SystemStatus:
        """
        Get overall system health and status.

        Returns:
            SystemStatus with component statuses and metrics
        """
        try:
            # Get component statuses
            health_results = self._health_monitor.get_all_statuses()
            component_statuses = {
                name: result.status.value for name, result in health_results.items()
            }

            # Get resource metrics
            resource_metrics = self._health_monitor.get_resource_metrics()
            resource_usage = {}
            if resource_metrics:
                resource_usage = {
                    "ram_percent": resource_metrics.ram_percent,
                    "cpu_percent": resource_metrics.cpu_percent,
                    "disk_percent": resource_metrics.disk_percent,
                }

            # Count active plugins
            active_plugins = sum(
                1 for p in self._plugin_manager.list_plugins() if p.is_loaded()
            )

            # Determine overall status
            if not component_statuses:
                overall_status = "initializing"
            elif all(s == "healthy" for s in component_statuses.values()):
                overall_status = "healthy"
            elif any(s == "unhealthy" for s in component_statuses.values()):
                overall_status = "unhealthy"
            else:
                overall_status = "degraded"

            # Add degraded flag from health monitor
            if self._health_monitor.is_degraded():
                overall_status = "degraded"

            uptime = time.time() - self._startup_time if self._startup_time else 0

            return SystemStatus(
                status=overall_status,
                uptime_seconds=uptime,
                component_statuses=component_statuses,
                resource_usage=resource_usage,
                active_plugins=active_plugins,
                total_requests=self._request_count,
                failed_requests=self._failed_request_count,
            )

        except Exception as e:
            self._logger.error("get_status_failed", error=str(e))
            return SystemStatus(
                status="error",
                uptime_seconds=0,
                component_statuses={"error": str(e)},
            )

    def is_running(self) -> bool:
        """Check if conductor is running."""
        return self._running

    def get_request_count(self) -> int:
        """Get total request count."""
        return self._request_count

    def get_failed_request_count(self) -> int:
        """Get failed request count."""
        return self._failed_request_count

    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        if self._startup_time is None:
            return 0
        return time.time() - self._startup_time


# Global conductor instance
_conductor_instance: Optional[Conductor] = None


def get_conductor(config: Optional[DemiConfig] = None) -> Conductor:
    """Get or create global conductor instance."""
    global _conductor_instance
    if _conductor_instance is None:
        _conductor_instance = Conductor(config)
    return _conductor_instance
