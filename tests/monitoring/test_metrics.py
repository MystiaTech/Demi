"""Tests for metrics collection system."""

import pytest
import tempfile
import os
from datetime import timedelta
from src.monitoring.metrics import MetricType, Metric, MetricsCollector


class TestMetric:
    """Test Metric dataclass."""

    def test_metric_creation(self):
        """Test creating a metric."""
        metric = Metric(
            name="test_metric",
            value=42.0,
            metric_type=MetricType.GAUGE,
            labels={"env": "test"},
        )

        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.metric_type == MetricType.GAUGE
        assert metric.labels == {"env": "test"}
        assert metric.id is not None
        assert metric.timestamp > 0

    def test_metric_to_dict(self):
        """Test metric serialization."""
        metric = Metric(
            name="test_metric",
            value=42.0,
            metric_type=MetricType.COUNTER,
        )

        data = metric.to_dict()
        assert data["name"] == "test_metric"
        assert data["value"] == 42.0
        assert data["metric_type"] == "counter"
        assert "id" in data
        assert "timestamp" in data


class TestMetricsCollector:
    """Test MetricsCollector class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        os.unlink(db_path)

    @pytest.fixture
    def collector(self, temp_db):
        """Create a metrics collector with temp database."""
        return MetricsCollector(db_path=temp_db, collection_interval=30)

    def test_record_metric(self, collector):
        """Test recording a metric."""
        metric = collector.record(
            name="cpu_usage",
            value=75.5,
            metric_type=MetricType.GAUGE,
            labels={"host": "localhost"},
        )

        assert metric.name == "cpu_usage"
        assert metric.value == 75.5

        # Verify it was stored
        latest = collector.get_latest("cpu_usage")
        assert latest is not None
        assert latest.value == 75.5

    def test_get_metric_history(self, collector):
        """Test retrieving metric history."""
        # Record multiple metrics
        for i in range(5):
            collector.record("memory", value=float(i * 10), metric_type=MetricType.GAUGE)

        # Get history
        history = collector.get_metric("memory")
        assert len(history) == 5

        # Check order (should be chronological)
        values = [m.value for m in history]
        assert values == [0.0, 10.0, 20.0, 30.0, 40.0]

    def test_get_latest(self, collector):
        """Test getting latest metric value."""
        collector.record("test", 1.0, MetricType.GAUGE)
        collector.record("test", 2.0, MetricType.GAUGE)
        collector.record("test", 3.0, MetricType.GAUGE)

        latest = collector.get_latest("test")
        assert latest is not None
        assert latest.value == 3.0

    def test_get_latest_nonexistent(self, collector):
        """Test getting latest for non-existent metric."""
        latest = collector.get_latest("nonexistent")
        assert latest is None

    def test_aggregate(self, collector):
        """Test metric aggregation."""
        # Record values: 10, 20, 30, 40, 50
        for i in range(1, 6):
            collector.record("values", float(i * 10), MetricType.GAUGE)

        # Test different aggregations
        assert collector.aggregate("values", "avg") == 30.0
        assert collector.aggregate("values", "min") == 10.0
        assert collector.aggregate("values", "max") == 50.0
        assert collector.aggregate("values", "sum") == 150.0
        assert collector.aggregate("values", "count") == 5

    def test_get_all_metric_names(self, collector):
        """Test getting all metric names."""
        collector.record("metric_a", 1.0, MetricType.GAUGE)
        collector.record("metric_b", 2.0, MetricType.GAUGE)
        collector.record("metric_c", 3.0, MetricType.GAUGE)

        names = collector.get_all_metric_names()
        assert sorted(names) == ["metric_a", "metric_b", "metric_c"]

    def test_time_range_filter(self, collector):
        """Test filtering by time range."""
        import time
        import sqlite3

        # Insert old metric directly into database
        with sqlite3.connect(collector.db_path) as conn:
            conn.execute(
                """
                INSERT INTO metrics (id, name, value, metric_type, timestamp, labels)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("old-id", "time_test", 1.0, "gauge", time.time() - 3600, "{}"),
            )
            conn.commit()

        # Record recent metric
        collector.record("time_test", 2.0, MetricType.GAUGE)

        # Query with time range
        recent = collector.get_metric("time_test", time_range=timedelta(minutes=30))
        assert len(recent) == 1
        assert recent[0].value == 2.0

    def test_callback_registration(self, collector):
        """Test callback registration."""
        callbacks = []

        def callback(metric):
            callbacks.append(metric.name)

        collector.register_callback(callback)
        collector.record("test_cb", 1.0, MetricType.GAUGE)

        assert "test_cb" in callbacks

        # Unregister and verify
        collector.unregister_callback(callback)
        collector.record("test_cb2", 2.0, MetricType.GAUGE)

        # Should only have first callback
        assert callbacks == ["test_cb"]


class TestMetricTypes:
    """Test different metric types."""

    def test_counter_type(self):
        """Test counter metric type."""
        assert MetricType.COUNTER.value == "counter"

    def test_gauge_type(self):
        """Test gauge metric type."""
        assert MetricType.GAUGE.value == "gauge"

    def test_histogram_type(self):
        """Test histogram metric type."""
        assert MetricType.HISTOGRAM.value == "histogram"
