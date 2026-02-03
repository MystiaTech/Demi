"""Tests for the dashboard server and main dashboard class."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.monitoring.dashboard import Dashboard, start_dashboard
from src.monitoring.dashboard_server import DashboardServer
from src.monitoring.metrics import MetricType


class TestDashboardServer:
    """Test DashboardServer class."""

    @pytest.fixture
    def server(self):
        """Create a dashboard server."""
        return DashboardServer(
            host="localhost",
            port=18080,  # Use different port to avoid conflicts
            update_interval=1,
        )

    def test_server_creation(self, server):
        """Test creating a dashboard server."""
        assert server.host == "localhost"
        assert server.port == 18080
        assert server.update_interval == 1
        assert server.app is not None

    def test_server_url(self, server):
        """Test getting server URL."""
        assert server.get_url() == "http://localhost:18080"

    @pytest.mark.asyncio
    async def test_get_system_metrics(self, server):
        """Test system metrics collection."""
        metrics = await server._get_system_metrics()

        assert "timestamp" in metrics
        assert isinstance(metrics, dict)

        # Check for expected keys (or error if psutil not available)
        if "error" not in metrics:
            assert "memory_percent" in metrics
            assert "cpu_percent" in metrics
            assert "memory_used_gb" in metrics

    @pytest.mark.asyncio
    async def test_get_emotional_state(self, server):
        """Test getting emotional state."""
        emotions = await server._get_emotional_state()

        # Should return dict or None
        if emotions is not None:
            assert isinstance(emotions, dict)
            # Check for expected emotion keys
            expected_emotions = [
                "loneliness", "excitement", "frustration",
                "jealousy", "vulnerability", "confidence",
                "curiosity", "affection", "defensiveness",
            ]
            for emotion in expected_emotions:
                assert emotion in emotions


class TestDashboard:
    """Test Dashboard main class."""

    @pytest.fixture
    def dashboard(self):
        """Create a dashboard instance."""
        return Dashboard(
            host="localhost",
            port=18081,
            update_interval=1,
            enable_alerts=False,  # Disable for testing
            enable_metrics_collection=False,  # Disable for testing
        )

    def test_dashboard_creation(self, dashboard):
        """Test creating a dashboard."""
        assert dashboard.host == "localhost"
        assert dashboard.port == 18081
        assert dashboard._running is False

    def test_dashboard_url(self, dashboard):
        """Test getting dashboard URL."""
        assert dashboard.get_url() == "http://localhost:18081"

    def test_record_emotion(self, dashboard):
        """Test recording emotion metric."""
        dashboard.record_emotion("loneliness", 0.75)

        # Check it was recorded
        metric = dashboard.metrics_collector.get_latest("emotion_loneliness")
        assert metric is not None
        assert abs(metric.value - 0.75) < 0.001  # Use tolerance for float comparison

    def test_record_response_time(self, dashboard):
        """Test recording response time."""
        dashboard.record_response_time(0.5)

        # Check it was recorded
        metric = dashboard.metrics_collector.get_latest("response_time")
        assert metric is not None
        assert metric.value == 0.5

    def test_get_stats(self, dashboard):
        """Test getting dashboard stats."""
        stats = dashboard.get_stats()

        assert "running" in stats
        assert "url" in stats
        assert "active_alerts" in stats
        assert "total_alerts" in stats
        assert "metrics_count" in stats


class TestDashboardIntegration:
    """Integration tests for dashboard components."""

    @pytest.mark.asyncio
    async def test_dashboard_start_stop(self):
        """Test starting and stopping dashboard."""
        dashboard = Dashboard(
            host="localhost",
            port=18082,
            enable_alerts=False,
            enable_metrics_collection=False,
        )

        # Mock the server start to avoid actually starting the server
        with patch.object(dashboard.server, 'start', new_callable=AsyncMock) as mock_start:
            with patch.object(dashboard.server, 'stop', new_callable=AsyncMock) as mock_stop:
                # Start should set running flag and call server.start
                task = asyncio.create_task(dashboard.start())
                await asyncio.sleep(0.1)  # Let it start

                assert dashboard._running is True
                mock_start.assert_called_once()

                # Stop should clean up
                await dashboard.stop()
                assert dashboard._running is False
                mock_stop.assert_called_once()

                # Cancel the task
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_gather_system_state(self):
        """Test gathering system state for alerts."""
        dashboard = Dashboard(
            host="localhost",
            port=18083,
            enable_alerts=False,
            enable_metrics_collection=False,
        )

        # Record some metrics first
        dashboard.metrics_collector.record("memory_percent", 75.0, MetricType.GAUGE)
        dashboard.metrics_collector.record("cpu_percent", 50.0, MetricType.GAUGE)
        dashboard.metrics_collector.record("emotion_loneliness", 0.6, MetricType.GAUGE)

        state = await dashboard._gather_system_state()

        assert "memory_percent" in state
        assert state["memory_percent"] == 75.0
        assert "cpu_percent" in state
        assert "emotions" in state
        assert state["emotions"]["loneliness"] == 0.6


class TestStartDashboard:
    """Test start_dashboard convenience function."""

    @pytest.mark.asyncio
    async def test_start_dashboard(self):
        """Test the start_dashboard helper."""
        with patch('src.monitoring.dashboard.Dashboard.start', new_callable=AsyncMock):
            dashboard = await start_dashboard(
                host="localhost",
                port=18084,
            )

            assert dashboard.host == "localhost"
            assert dashboard.port == 18084
            # _running is set by start(), which is mocked, so it stays False
            # but the dashboard object is created correctly


class TestDashboardAPIEndpoints:
    """Test API endpoint definitions."""

    def test_api_routes_exist(self):
        """Test that all expected routes are defined."""
        server = DashboardServer(host="localhost", port=18085)

        # Get all routes
        routes = [route.path for route in server.app.routes]

        # Check expected routes exist
        expected_routes = [
            "/",
            "/api/health",
            "/api/metrics/current",
            "/api/alerts",
            "/api/emotions",
            "/api/emotions/history",
            "/api/platforms",
        ]

        for route in expected_routes:
            # Routes might have prefixes or be in different formats
            assert any(route in r for r in routes), f"Route {route} not found"


class TestDashboardCallbacks:
    """Test dashboard callback functionality."""

    def test_metric_callback(self):
        """Test metric recording callback registration."""
        dashboard = Dashboard(
            host="localhost",
            port=18086,
            enable_alerts=False,
            enable_metrics_collection=False,
        )

        # Callback should be registered (on start, but we didn't start)
        # Register it manually for testing
        dashboard.metrics_collector.register_callback(dashboard._on_metric_recorded)
        callbacks = dashboard.metrics_collector._callbacks
        assert dashboard._on_metric_recorded in callbacks

        # Unregister and verify
        dashboard.metrics_collector.unregister_callback(dashboard._on_metric_recorded)
        assert dashboard._on_metric_recorded not in dashboard.metrics_collector._callbacks
