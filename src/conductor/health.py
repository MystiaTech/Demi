"""
Health monitoring system for Demi's conductor.
Continuously monitors platform integrations with 5-second intervals.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict, Any
from enum import Enum

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from src.core.logger import logger
from src.conductor.circuit_breaker import get_circuit_breaker_manager
from src.conductor.metrics import get_metrics


class HealthStatus(Enum):
    """Health check result status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    platform: str
    status: HealthStatus
    duration: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResourceMetrics:
    """System resource usage metrics."""

    ram_percent: float
    cpu_percent: float
    disk_percent: float
    timestamp: float = field(default_factory=time.time)


class HealthMonitor:
    """
    Monitors health of all platform integrations.
    Runs staggered health checks every 5 seconds.
    """

    def __init__(self, check_interval: float = 5.0, check_timeout: float = 5.0):
        """
        Initialize health monitor.

        Args:
            check_interval: Seconds between full health check cycles
            check_timeout: Timeout per individual platform check
        """
        self.check_interval = check_interval
        self.check_timeout = check_timeout
        self._running = False
        self._last_check_time: Optional[float] = None
        self._check_results: Dict[str, HealthCheckResult] = {}
        self._resource_metrics: Optional[ResourceMetrics] = None
        self._degraded_mode = False
        self._circuit_breaker_manager = get_circuit_breaker_manager()

        logger.info(
            "health_monitor_initialized",
            check_interval=check_interval,
            check_timeout=check_timeout,
        )

    async def check_platform_health(
        self, platform: str, health_check_fn: Optional[Callable] = None
    ) -> HealthCheckResult:
        """
        Check health of a single platform.

        Args:
            platform: Platform name to check
            health_check_fn: Optional async function to call for health check

        Returns:
            HealthCheckResult with status and timing
        """
        start_time = time.time()

        try:
            # Skip if circuit breaker is open
            if not self._circuit_breaker_manager.can_execute(platform):
                duration = time.time() - start_time
                result = HealthCheckResult(
                    platform=platform,
                    status=HealthStatus.UNHEALTHY,
                    duration=duration,
                    error="Circuit breaker OPEN",
                )
                self._circuit_breaker_manager.record_failure(platform)
                return result

            # Run health check function if provided
            if health_check_fn:
                try:
                    # Wrap sync function in async if needed
                    if asyncio.iscoroutinefunction(health_check_fn):
                        await asyncio.wait_for(
                            health_check_fn(platform), timeout=self.check_timeout
                        )
                    else:
                        # Run sync function in executor
                        loop = asyncio.get_event_loop()
                        await asyncio.wait_for(
                            loop.run_in_executor(None, health_check_fn, platform),
                            timeout=self.check_timeout,
                        )
                except asyncio.TimeoutError:
                    duration = time.time() - start_time
                    result = HealthCheckResult(
                        platform=platform,
                        status=HealthStatus.UNHEALTHY,
                        duration=duration,
                        error=f"Health check timeout (>{self.check_timeout}s)",
                    )
                    self._circuit_breaker_manager.record_failure(platform)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    result = HealthCheckResult(
                        platform=platform,
                        status=HealthStatus.UNHEALTHY,
                        duration=duration,
                        error=str(e),
                    )
                    self._circuit_breaker_manager.record_failure(platform)
                    return result

            # Success
            duration = time.time() - start_time
            result = HealthCheckResult(
                platform=platform,
                status=HealthStatus.HEALTHY,
                duration=duration,
            )
            self._circuit_breaker_manager.record_success(platform)

        except Exception as e:
            duration = time.time() - start_time
            result = HealthCheckResult(
                platform=platform,
                status=HealthStatus.UNHEALTHY,
                duration=duration,
                error=str(e),
            )
            self._circuit_breaker_manager.record_failure(platform)

        # Record in metrics
        self._record_health_check_metric(result)
        self._check_results[platform] = result

        return result

    async def staggered_health_checks(
        self,
        platforms: List[str],
        health_check_fn: Optional[Callable] = None,
        stagger_delay: float = 0.5,
    ) -> List[HealthCheckResult]:
        """
        Execute health checks for multiple platforms with staggered timing.
        Prevents resource spikes by spacing out checks.

        Args:
            platforms: List of platform names to check
            health_check_fn: Optional health check function
            stagger_delay: Delay between starting each check

        Returns:
            List of HealthCheckResult objects
        """
        tasks = []

        for i, platform in enumerate(platforms):
            # Create delayed task
            async def delayed_check(p=platform, delay=i * stagger_delay):
                await asyncio.sleep(delay)
                return await self.check_platform_health(p, health_check_fn)

            tasks.append(delayed_check())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract actual results (handle exceptions if any)
        check_results = []
        for result in results:
            if isinstance(result, HealthCheckResult):
                check_results.append(result)
            elif isinstance(result, Exception):
                logger.error("staggered_check_exception", error=str(result))

        return check_results

    def update_resource_metrics(self):
        """Update system resource usage metrics."""
        if not HAS_PSUTIL:
            logger.debug("psutil not available, skipping resource monitoring")
            return

        try:
            ram_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=0.1)
            disk_percent = psutil.disk_usage("/").percent

            self._resource_metrics = ResourceMetrics(
                ram_percent=ram_percent,
                cpu_percent=cpu_percent,
                disk_percent=disk_percent,
            )

            # Record in metrics
            metrics = get_metrics()
            metrics.set_system_resource("ram", ram_percent)
            metrics.set_system_resource("cpu", cpu_percent)
            metrics.set_system_resource("disk", disk_percent)

            # Check for degraded mode (>80% usage)
            if ram_percent > 80 or cpu_percent > 80:
                if not self._degraded_mode:
                    self._degraded_mode = True
                    logger.warning(
                        "health_monitor_degraded_mode_enabled",
                        ram_percent=ram_percent,
                        cpu_percent=cpu_percent,
                    )
            else:
                if self._degraded_mode:
                    self._degraded_mode = False
                    logger.info("health_monitor_degraded_mode_disabled")

        except Exception as e:
            logger.error("resource_metrics_update_failed", error=str(e))

    def is_degraded(self) -> bool:
        """Check if system is in degraded mode (resources >80%)."""
        return self._degraded_mode

    async def health_check_loop(
        self,
        platforms: List[str],
        health_check_fn: Optional[Callable] = None,
    ):
        """
        Main health check loop - runs continuously every check_interval seconds.

        Args:
            platforms: List of platform names to monitor
            health_check_fn: Optional health check function for platforms
        """
        logger.info(
            "health_check_loop_started",
            platforms=platforms,
            interval=self.check_interval,
        )
        self._running = True

        cycle = 0
        while self._running:
            try:
                cycle += 1
                self._last_check_time = time.time()

                # Update system resources
                self.update_resource_metrics()

                # Run staggered health checks
                results = await self.staggered_health_checks(platforms, health_check_fn)

                # Count results
                healthy = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
                unhealthy = sum(
                    1 for r in results if r.status == HealthStatus.UNHEALTHY
                )

                logger.debug(
                    "health_check_cycle_complete",
                    cycle=cycle,
                    platforms_checked=len(results),
                    healthy=healthy,
                    unhealthy=unhealthy,
                    degraded=self._degraded_mode,
                )

                # Wait for next cycle
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info("health_check_loop_cancelled")
                self._running = False
                break
            except Exception as e:
                logger.error("health_check_loop_error", error=str(e))
                await asyncio.sleep(self.check_interval)

    def stop(self):
        """Stop the health check loop."""
        self._running = False
        logger.info("health_check_loop_stop_requested")

    def get_last_check_time(self) -> Optional[float]:
        """Get timestamp of last completed health check cycle."""
        return self._last_check_time

    def get_platform_status(self, platform: str) -> Optional[HealthCheckResult]:
        """Get last health check result for a platform."""
        return self._check_results.get(platform)

    def get_all_statuses(self) -> Dict[str, HealthCheckResult]:
        """Get all platform health check results."""
        return dict(self._check_results)

    def get_resource_metrics(self) -> Optional[ResourceMetrics]:
        """Get current system resource metrics."""
        return self._resource_metrics

    def _record_health_check_metric(self, result: HealthCheckResult):
        """Record health check result to metrics."""
        try:
            metrics = get_metrics()
            metrics.record_health_check(
                platform=result.platform,
                status=result.status.value,
                duration_seconds=result.duration,
            )
        except Exception as e:
            logger.debug("metrics_recording_failed", error=str(e))


# Global health monitor instance
_health_monitor_instance: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance, creating if needed."""
    global _health_monitor_instance
    if _health_monitor_instance is None:
        _health_monitor_instance = HealthMonitor()
        logger.info("global_health_monitor_initialized")
    return _health_monitor_instance
