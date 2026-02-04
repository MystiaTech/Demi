"""Comprehensive metrics collection system with SQLite persistence.

Collects and stores system metrics including CPU, memory, response times,
emotional states, LLM performance, platform stats, and conversation quality
for health monitoring and trend analysis.
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


class LLMMetricsCollector:
    """Collect and track LLM inference performance metrics."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.token_buffer = {}  # Buffer for efficient batch processing

    def record_inference(
        self,
        response_time_ms: float,
        tokens_generated: int,
        inference_latency_ms: float,
        prompt_tokens: int = 0,
        model: str = "unknown",
    ):
        """Record LLM inference performance.

        Args:
            response_time_ms: Total response time in milliseconds
            tokens_generated: Number of tokens generated
            inference_latency_ms: Model inference latency in milliseconds
            prompt_tokens: Number of tokens in prompt
            model: Model name
        """
        self.metrics.record(
            "llm_response_time_ms",
            response_time_ms,
            MetricType.HISTOGRAM,
            labels={"model": model},
        )
        self.metrics.record(
            "llm_tokens_generated",
            tokens_generated,
            MetricType.GAUGE,
            labels={"model": model},
        )
        self.metrics.record(
            "llm_inference_latency_ms",
            inference_latency_ms,
            MetricType.HISTOGRAM,
            labels={"model": model},
        )
        if prompt_tokens > 0:
            self.metrics.record(
                "llm_prompt_tokens",
                prompt_tokens,
                MetricType.GAUGE,
                labels={"model": model},
            )

    def record_error(self, error_type: str, model: str = "unknown"):
        """Record LLM inference error.

        Args:
            error_type: Type of error
            model: Model name
        """
        self.metrics.record(
            "llm_errors",
            1,
            MetricType.COUNTER,
            labels={"error_type": error_type, "model": model},
        )


class PlatformMetricsCollector:
    """Collect and track platform interaction metrics."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.platform_stats = {}  # In-memory stats for quick access

    def record_message(
        self,
        platform: str,
        response_time_ms: float,
        message_length: int,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """Record platform message interaction.

        Args:
            platform: Platform name (discord, android, etc.)
            response_time_ms: Response time in milliseconds
            message_length: Length of message
            success: Whether operation was successful
            error: Error message if failed
        """
        self.metrics.record(
            f"platform_{platform}_messages",
            1,
            MetricType.COUNTER,
        )
        self.metrics.record(
            f"platform_{platform}_response_time_ms",
            response_time_ms,
            MetricType.HISTOGRAM,
        )
        self.metrics.record(
            f"platform_{platform}_message_length",
            message_length,
            MetricType.GAUGE,
        )

        if not success and error:
            self.metrics.record(
                f"platform_{platform}_errors",
                1,
                MetricType.COUNTER,
                labels={"error": error},
            )

        # Update in-memory stats
        if platform not in self.platform_stats:
            self.platform_stats[platform] = {
                "messages": 0,
                "total_response_time": 0,
                "errors": 0,
            }
        self.platform_stats[platform]["messages"] += 1
        self.platform_stats[platform]["total_response_time"] += response_time_ms
        if not success:
            self.platform_stats[platform]["errors"] += 1

    def get_platform_stats(self, time_range: timedelta = None) -> Dict[str, Any]:
        """Get aggregated platform statistics.

        Args:
            time_range: Optional time range to aggregate

        Returns:
            Dictionary of platform stats
        """
        stats = {}
        for platform in list(self.platform_stats.keys()):
            messages = self.metrics.aggregate(
                f"platform_{platform}_messages", "count", time_range
            )
            response_times = self.metrics.get_metric(
                f"platform_{platform}_response_time_ms", time_range
            )
            errors = self.metrics.aggregate(
                f"platform_{platform}_errors", "count", time_range
            )

            if messages:
                avg_response = 0
                if response_times:
                    avg_response = sum(m.value for m in response_times) / len(
                        response_times
                    )

                stats[platform] = {
                    "message_count": int(messages or 0),
                    "avg_response_time_ms": round(avg_response, 2),
                    "error_count": int(errors or 0),
                    "error_rate": (
                        round((errors / messages * 100), 2) if messages else 0
                    ),
                }

        return stats


class ConversationMetricsCollector:
    """Collect and track conversation quality metrics."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector

    def record_conversation(
        self,
        user_message_length: int,
        bot_response_length: int,
        conversation_turn: int,
        sentiment_score: float = 0.5,
    ):
        """Record conversation metrics.

        Args:
            user_message_length: Length of user message
            bot_response_length: Length of bot response
            conversation_turn: Turn number in conversation
            sentiment_score: Sentiment score 0-1
        """
        self.metrics.record(
            "conversation_user_message_length",
            user_message_length,
            MetricType.GAUGE,
        )
        self.metrics.record(
            "conversation_bot_response_length",
            bot_response_length,
            MetricType.GAUGE,
        )
        self.metrics.record(
            "conversation_turn_number", conversation_turn, MetricType.GAUGE
        )
        self.metrics.record(
            "conversation_sentiment", sentiment_score, MetricType.GAUGE
        )

    def get_quality_metrics(
        self, time_range: timedelta = None
    ) -> Dict[str, float]:
        """Get conversation quality metrics.

        Args:
            time_range: Optional time range

        Returns:
            Dictionary of quality metrics
        """
        avg_user_length = self.metrics.aggregate(
            "conversation_user_message_length", "avg", time_range
        )
        avg_response_length = self.metrics.aggregate(
            "conversation_bot_response_length", "avg", time_range
        )
        avg_sentiment = self.metrics.aggregate(
            "conversation_sentiment", "avg", time_range
        )
        max_turn = self.metrics.aggregate(
            "conversation_turn_number", "max", time_range
        )

        return {
            "avg_user_message_length": round(avg_user_length or 0, 2),
            "avg_response_length": round(avg_response_length or 0, 2),
            "avg_sentiment": round(avg_sentiment or 0.5, 3),
            "max_conversation_turn": int(max_turn or 0),
        }


class EmotionMetricsCollector:
    """Collect and track emotional state metrics."""

    EMOTION_NAMES = [
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

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.last_state = {}

    def record_emotion_state(self, emotions: Dict[str, float]):
        """Record emotional state.

        Args:
            emotions: Dictionary mapping emotion names to values (0-1)
        """
        for emotion_name, value in emotions.items():
            if emotion_name in self.EMOTION_NAMES:
                self.metrics.record(
                    f"emotion_{emotion_name}",
                    value,
                    MetricType.GAUGE,
                )
        self.last_state = emotions

    def get_emotion_history(
        self, emotion: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get emotion history.

        Args:
            emotion: Emotion name
            limit: Maximum number of points

        Returns:
            List of emotion data points
        """
        metrics = self.metrics.get_metric(f"emotion_{emotion}", limit=limit)
        return [
            {"timestamp": m.timestamp, "value": m.value} for m in metrics
        ]

    def get_current_emotions(self) -> Dict[str, float]:
        """Get current emotional state.

        Returns:
            Dictionary of current emotion values
        """
        emotions = {}
        for emotion_name in self.EMOTION_NAMES:
            metric = self.metrics.get_latest(f"emotion_{emotion_name}")
            emotions[emotion_name] = metric.value if metric else 0.5
        return emotions


class DiscordMetricsCollector:
    """Collect and track Discord bot metrics."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.last_status = {}

    def record_bot_status(
        self,
        online: bool,
        latency_ms: float,
        guild_count: int,
        connected_users: int,
    ):
        """Record Discord bot status.

        Args:
            online: Whether bot is online
            latency_ms: Bot latency in milliseconds
            guild_count: Number of connected guilds
            connected_users: Number of connected users
        """
        self.metrics.record(
            "discord_bot_online",
            1.0 if online else 0.0,
            MetricType.GAUGE,
        )
        self.metrics.record(
            "discord_bot_latency_ms",
            latency_ms,
            MetricType.GAUGE,
        )
        self.metrics.record(
            "discord_guild_count",
            guild_count,
            MetricType.GAUGE,
        )
        self.metrics.record(
            "discord_connected_users",
            connected_users,
            MetricType.GAUGE,
        )

        self.last_status = {
            "online": online,
            "latency_ms": latency_ms,
            "guild_count": guild_count,
            "connected_users": connected_users,
        }

    def get_bot_status(self) -> Dict[str, Any]:
        """Get current bot status.

        Returns:
            Dictionary of bot status metrics
        """
        return self.last_status or {
            "online": False,
            "latency_ms": 0,
            "guild_count": 0,
            "connected_users": 0,
        }


# Global specialized collectors
_llm_metrics: Optional[LLMMetricsCollector] = None
_platform_metrics: Optional[PlatformMetricsCollector] = None
_conversation_metrics: Optional[ConversationMetricsCollector] = None
_emotion_metrics: Optional[EmotionMetricsCollector] = None
_discord_metrics: Optional[DiscordMetricsCollector] = None


def get_llm_metrics() -> LLMMetricsCollector:
    """Get global LLM metrics collector."""
    global _llm_metrics
    if _llm_metrics is None:
        _llm_metrics = LLMMetricsCollector(get_metrics_collector())
    return _llm_metrics


def get_platform_metrics() -> PlatformMetricsCollector:
    """Get global platform metrics collector."""
    global _platform_metrics
    if _platform_metrics is None:
        _platform_metrics = PlatformMetricsCollector(get_metrics_collector())
    return _platform_metrics


def get_conversation_metrics() -> ConversationMetricsCollector:
    """Get global conversation metrics collector."""
    global _conversation_metrics
    if _conversation_metrics is None:
        _conversation_metrics = ConversationMetricsCollector(get_metrics_collector())
    return _conversation_metrics


def get_emotion_metrics() -> EmotionMetricsCollector:
    """Get global emotion metrics collector."""
    global _emotion_metrics
    if _emotion_metrics is None:
        _emotion_metrics = EmotionMetricsCollector(get_metrics_collector())
    return _emotion_metrics


def get_discord_metrics() -> DiscordMetricsCollector:
    """Get global Discord metrics collector."""
    global _discord_metrics
    if _discord_metrics is None:
        _discord_metrics = DiscordMetricsCollector(get_metrics_collector())
    return _discord_metrics
