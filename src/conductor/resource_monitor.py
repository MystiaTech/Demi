"""Resource monitoring system for tracking system resources with historical analysis.

This module provides real-time resource monitoring (CPU, RAM, disk) with a 30-minute
sliding window for trend analysis and anomaly detection.
"""

import asyncio
import time
import psutil
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.core.logger import get_logger
from src.core.config import DemiConfig
from src.conductor.metrics import get_metrics

logger = get_logger()


@dataclass
class ResourceMetrics:
    """Snapshot of system resource usage at a point in time."""

    timestamp: float
    cpu: float  # CPU usage percentage (0-100)
    memory: float  # Memory usage percentage (0-100)
    disk: float  # Disk usage percentage (0-100)
    memory_mb: int  # Absolute memory usage in MB
    disk_free_mb: int  # Free disk space in MB

    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary format."""
        return {
            "timestamp": self.timestamp,
            "cpu": self.cpu,
            "memory": self.memory,
            "disk": self.disk,
            "memory_mb": self.memory_mb,
            "disk_free_mb": self.disk_free_mb,
        }


class ResourceMonitor:
    """Monitors system resources with historical tracking and trend analysis.

    Maintains a 30-minute sliding window of resource metrics (60 data points at 30-second intervals).
    Provides methods for trend analysis and anomaly detection.
    """

    def __init__(
        self,
        window_size: int = 60,
        collection_interval: int = 30,
        config: Optional[DemiConfig] = None,
    ):
        """Initialize resource monitor.

        Args:
            window_size: Number of data points to maintain (default 60 for 30 min at 30s intervals)
            collection_interval: Seconds between collections (default 30)
            config: Optional DemiConfig for configuration overrides
        """
        self.window_size = window_size
        self.collection_interval = collection_interval
        self.config = config or DemiConfig.load()

        # Sliding window storage (FIFO - oldest data pushed out when full)
        self.history: deque = deque(maxlen=window_size)

        # Current state
        self._current_metrics: Optional[ResourceMetrics] = None
        self._last_collection_time: float = 0
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False

        # Metrics registry for Prometheus
        self.metrics = get_metrics()

        logger.info(
            "ResourceMonitor initialized",
            window_size=window_size,
            collection_interval=collection_interval,
        )

    async def collect_metrics(self) -> Dict[str, float]:
        """Collect current system resource metrics.

        Returns:
            Dictionary with cpu, memory, disk percentages and absolute values
        """
        try:
            # Get CPU usage (percentage across all cores)
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_mb = memory.used // (1024 * 1024)

            # Get disk usage
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_free_mb = disk.free // (1024 * 1024)

            # Create metrics snapshot
            now = time.time()
            metrics = ResourceMetrics(
                timestamp=now,
                cpu=cpu_percent,
                memory=memory_percent,
                disk=disk_percent,
                memory_mb=memory_mb,
                disk_free_mb=disk_free_mb,
            )

            # Store in history
            self.history.append(metrics)
            self._current_metrics = metrics
            self._last_collection_time = now

            # Record to Prometheus metrics
            if self.metrics:
                self.metrics.set_system_resource("cpu", cpu_percent)
                self.metrics.set_system_resource("memory", memory_percent)
                self.metrics.set_system_resource("disk", disk_percent)

            logger.debug(
                "metrics_collected",
                cpu=cpu_percent,
                memory=f"{memory_percent:.1f}%",
                disk=f"{disk_percent:.1f}%",
                memory_mb=memory_mb,
            )

            return metrics.to_dict()

        except Exception as e:
            logger.error("Failed to collect metrics", error=str(e))
            return {}

    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get the most recently collected metrics snapshot.

        Returns:
            ResourceMetrics object or None if no collection yet
        """
        return self._current_metrics

    def get_history(self, limit: Optional[int] = None) -> List[ResourceMetrics]:
        """Get historical metrics within sliding window.

        Args:
            limit: Optional limit on number of recent entries to return

        Returns:
            List of ResourceMetrics in chronological order
        """
        history_list = list(self.history)
        if limit:
            return history_list[-limit:]
        return history_list

    def get_history_values(self, key: str) -> List[float]:
        """Get specific metric values from history for analysis.

        Args:
            key: Metric key ('cpu', 'memory', 'disk', 'memory_mb', 'disk_free_mb')

        Returns:
            List of values for the specified metric
        """
        if key not in ResourceMetrics.__dataclass_fields__:
            logger.warning(f"Unknown metric key: {key}")
            return []

        return [getattr(m, key) for m in self.history if hasattr(m, key)]

    def calculate_trends(self) -> Dict[str, Dict[str, float]]:
        """Calculate trend statistics for each resource.

        Returns:
            Dictionary with trend data: average, min, max, current
        """
        if not self.history:
            return {}

        current = self.get_current_metrics()
        if not current:
            return {}

        trends = {}
        for metric in ["cpu", "memory", "disk"]:
            values = self.get_history_values(metric)
            if values:
                trends[metric] = {
                    "current": current.__dict__[metric],
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "trend": self._calculate_rate_of_change(values),
                }

        return trends

    def _calculate_rate_of_change(self, values: List[float]) -> float:
        """Calculate rate of change (slope) for a sequence of values.

        Args:
            values: Sequence of values (assumes uniform time intervals)

        Returns:
            Rate of change (positive = increasing, negative = decreasing)
        """
        if len(values) < 2:
            return 0.0

        # Simple linear regression: (last - first) / (n - 1)
        return (values[-1] - values[0]) / (len(values) - 1)

    def detect_anomalies(
        self, threshold_std_dev: float = 2.0
    ) -> Dict[str, List[Tuple[int, float]]]:
        """Detect anomalies (sudden spikes/drops) using statistical analysis.

        Args:
            threshold_std_dev: Number of standard deviations for anomaly threshold

        Returns:
            Dictionary mapping metric names to list of (index, value) tuples for anomalies
        """
        if len(self.history) < 10:
            return {}  # Need minimum data for statistical analysis

        anomalies = {}

        for metric in ["cpu", "memory", "disk"]:
            values = self.get_history_values(metric)
            if len(values) < 3:
                continue

            # Calculate mean and standard deviation
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std_dev = variance**0.5

            # Find values beyond threshold
            threshold = mean + (threshold_std_dev * std_dev)
            anomalies_for_metric = []

            for i, value in enumerate(values):
                if value > threshold:
                    anomalies_for_metric.append((i, value))

            if anomalies_for_metric:
                anomalies[metric] = anomalies_for_metric

        return anomalies

    async def start_background_collection(self) -> None:
        """Start background collection task (runs continuously).

        This should be called once at system startup. The collection task
        runs asynchronously every `collection_interval` seconds.
        """
        if self._running:
            logger.warning("Collection already running")
            return

        self._running = True
        logger.info(
            "Starting background resource collection",
            interval=self.collection_interval,
        )

        try:
            self._collection_task = asyncio.create_task(self._collection_loop())
        except Exception as e:
            logger.error("Failed to start collection task", error=str(e))
            self._running = False

    async def _collection_loop(self) -> None:
        """Background loop for periodic metric collection."""
        try:
            while self._running:
                try:
                    await self.collect_metrics()
                    await asyncio.sleep(self.collection_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in collection loop", error=str(e))
                    await asyncio.sleep(self.collection_interval)
        finally:
            logger.info("Resource collection loop ended")

    async def stop_background_collection(self) -> None:
        """Stop the background collection task."""
        if not self._running:
            return

        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        logger.info("Background resource collection stopped")

    def get_resource_summary(self) -> Dict[str, any]:
        """Get a comprehensive summary of current resource state.

        Returns:
            Dictionary with current metrics and trend analysis
        """
        current = self.get_current_metrics()
        if not current:
            return {"status": "no_data"}

        trends = self.calculate_trends()
        anomalies = self.detect_anomalies()

        return {
            "status": "ok",
            "current": current.to_dict(),
            "trends": trends,
            "anomalies": anomalies if anomalies else None,
            "history_size": len(self.history),
            "last_collection": datetime.fromtimestamp(current.timestamp).isoformat(),
        }
