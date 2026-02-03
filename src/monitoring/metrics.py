"""Metrics collection system with SQLite persistence.

Collects and stores system metrics including CPU, memory, response times,
and emotional states for health monitoring and trend analysis.
"""

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union

from src.core.logger import get_logger

logger = get_logger()


class MetricType(Enum):
    """Types of metrics supported."""

    COUNTER = "counter"  # Monotonically increasing (e.g., total requests)
    GAUGE = "gauge"  # Can go up or down (e.g., current memory)
    HISTOGRAM = "histogram"  # Distribution of values (e.g., response times)


@dataclass
class Metric:
    """A single metric data point."""

    name: str
    value: float
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metric":
        """Create metric from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            value=data["value"],
            metric_type=MetricType(data["metric_type"]),
            timestamp=data["timestamp"],
            labels=data.get("labels", {}),
        )


class MetricsCollector:
    """Collects and stores metrics with SQLite persistence.

    Features:
    - Time-series data storage in SQLite
    - Automatic retention policy (configurable)
    - Aggregation functions for analysis
    - Real-time metrics collection loop
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        retention_days: int = 7,
        collection_interval: int = 30,
    ):
        """Initialize metrics collector.

        Args:
            db_path: Path to SQLite database (default: ~/.demi/metrics.db)
            retention_days: Days to retain metrics data
            collection_interval: Seconds between automatic collections
        """
        if db_path is None:
            data_dir = Path.home() / ".demi"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "metrics.db")

        self.db_path = db_path
        self.retention_days = retention_days
        self.collection_interval = collection_interval

        self._running = False
        self._collection_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[Metric], None]] = []

        # Initialize database
        self._init_db()

        logger.info(
            "MetricsCollector initialized",
            db_path=db_path,
            retention_days=retention_days,
        )

    def _init_db(self):
        """Initialize SQLite database with metrics table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    metric_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    labels TEXT DEFAULT '{}'
                )
            """)

            # Create indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name_time
                ON metrics(name, timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
                ON metrics(timestamp)
            """)

            conn.commit()

    def record(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
    ) -> Metric:
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            labels: Optional labels for categorization

        Returns:
            The recorded Metric object
        """
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {},
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO metrics (id, name, value, metric_type, timestamp, labels)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    metric.id,
                    metric.name,
                    metric.value,
                    metric.metric_type.value,
                    metric.timestamp,
                    json.dumps(metric.labels),
                ),
            )
            conn.commit()

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error("Metrics callback error", error=str(e))

        return metric

    def get_metric(
        self,
        name: str,
        time_range: Optional[timedelta] = None,
        limit: int = 1000,
    ) -> List[Metric]:
        """Query metrics by name with optional time range.

        Args:
            name: Metric name to query
            time_range: Optional time range to look back
            limit: Maximum number of results

        Returns:
            List of Metric objects
        """
        cutoff_time = 0.0
        if time_range:
            cutoff_time = time.time() - time_range.total_seconds()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM metrics
                WHERE name = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (name, cutoff_time, limit),
            )

            rows = cursor.fetchall()

        metrics = []
        for row in rows:
            metrics.append(
                Metric(
                    id=row["id"],
                    name=row["name"],
                    value=row["value"],
                    metric_type=MetricType(row["metric_type"]),
                    timestamp=row["timestamp"],
                    labels=json.loads(row["labels"]),
                )
            )

        return list(reversed(metrics))

    def get_latest(self, name: str) -> Optional[Metric]:
        """Get the most recent value for a metric.

        Args:
            name: Metric name

        Returns:
            Most recent Metric or None if no data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM metrics
                WHERE name = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (name,),
            )

            row = cursor.fetchone()

        if row:
            return Metric(
                id=row["id"],
                name=row["name"],
                value=row["value"],
                metric_type=MetricType(row["metric_type"]),
                timestamp=row["timestamp"],
                labels=json.loads(row["labels"]),
            )
        return None

    def aggregate(
        self,
        name: str,
        func: str,
        time_range: Optional[timedelta] = None,
    ) -> Optional[float]:
        """Aggregate metric values over a time range.

        Args:
            name: Metric name
            func: Aggregation function ('avg', 'min', 'max', 'sum', 'count')
            time_range: Optional time range to look back

        Returns:
            Aggregated value or None if no data
        """
        cutoff_time = 0.0
        if time_range:
            cutoff_time = time.time() - time_range.total_seconds()

        func_map = {
            "avg": "AVG",
            "min": "MIN",
            "max": "MAX",
            "sum": "SUM",
            "count": "COUNT",
        }

        sql_func = func_map.get(func.lower())
        if not sql_func:
            raise ValueError(f"Unknown aggregation function: {func}")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"""
                SELECT {sql_func}(value) FROM metrics
                WHERE name = ? AND timestamp >= ?
                """,
                (name, cutoff_time),
            )

            result = cursor.fetchone()[0]

        return result

    def get_all_metric_names(self) -> List[str]:
        """Get list of all unique metric names.

        Returns:
            List of metric names
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT DISTINCT name FROM metrics ORDER BY name"
            )
            return [row[0] for row in cursor.fetchall()]

    def cleanup_old_data(self) -> int:
        """Remove metrics older than retention period.

        Returns:
            Number of rows deleted
        """
        cutoff_time = time.time() - (self.retention_days * 24 * 60 * 60)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM metrics WHERE timestamp < ?",
                (cutoff_time,),
            )
            conn.commit()
            deleted = cursor.rowcount

        if deleted > 0:
            logger.info("Cleaned up old metrics", deleted=deleted)

        return deleted

    def register_callback(self, callback: Callable[[Metric], None]):
        """Register a callback to be called when a metric is recorded.

        Args:
            callback: Function to call with the recorded Metric
        """
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[Metric], None]):
        """Unregister a callback.

        Args:
            callback: Function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def collect_system_metrics(self) -> Dict[str, float]:
        """Collect current system metrics.

        Returns:
            Dictionary of collected metrics
        """
        metrics = {}

        try:
            import psutil

            # Memory metrics
            memory = psutil.virtual_memory()
            metrics["memory_percent"] = memory.percent
            metrics["memory_used_gb"] = memory.used / (1024**3)
            metrics["memory_available_gb"] = memory.available / (1024**3)

            # CPU metrics
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)

            # Disk metrics
            disk = psutil.disk_usage("/")
            metrics["disk_percent"] = disk.percent
            metrics["disk_free_gb"] = disk.free / (1024**3)

            # Record all metrics
            for name, value in metrics.items():
                self.record(name, value, MetricType.GAUGE)

        except ImportError:
            logger.warning("psutil not available, skipping system metrics")
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))

        return metrics

    async def start_collection(self):
        """Start automatic background metrics collection."""
        if self._running:
            logger.warning("Metrics collection already running")
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())

        logger.info("Started metrics collection", interval=self.collection_interval)

    async def stop_collection(self):
        """Stop automatic background metrics collection."""
        if not self._running:
            return

        self._running = False

        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped metrics collection")

    async def _collection_loop(self):
        """Background loop for periodic metrics collection."""
        while self._running:
            try:
                await self.collect_system_metrics()

                # Cleanup old data periodically (every hour)
                if int(time.time()) % 3600 < self.collection_interval:
                    self.cleanup_old_data()

                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Metrics collection error", error=str(e))
                await asyncio.sleep(self.collection_interval)


# Global metrics collector instance
_metrics_collector_instance: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector_instance
    if _metrics_collector_instance is None:
        _metrics_collector_instance = MetricsCollector()
    return _metrics_collector_instance
