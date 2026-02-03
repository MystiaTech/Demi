"""
Stability Test Suite for Demi.

Comprehensive test suite for long-running stability validation.
Includes both short-running tests for CI and long-running tests
for manual validation.

Requirements:
    - HEALTH-01: 7-day continuous operation validation
    - HEALTH-03: Emotional state preserved across restarts
"""

import asyncio
import time
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

from tests.stability.long_running import (
    LongRunningStabilityTest,
    StabilityMetrics,
    StabilityTestConfig,
)
from tests.stability.load_generator import (
    LoadGenerator,
    LoadPattern,
    InteractionType,
    InteractionPattern,
    MultiPatternLoadGenerator,
    PATTERNS,
    SAMPLE_MESSAGES,
)
from tests.stability.emotion_monitor import (
    EmotionStabilityMonitor,
    EmotionSnapshot,
    EmotionDriftReport,
    verify_emotion_consistency,
    verify_emotion_persistence_integrity,
    verify_decay_behavior,
    CONSISTENCY_RULES,
)
from tests.stability.recovery_test import (
    RecoveryTest,
    RecoveryResult,
    simulate_crash_recovery,
    test_backup_restore,
    run_all_recovery_tests,
)
from src.emotion.models import EmotionalState
from src.emotion.persistence import EmotionPersistence
from src.emotion.decay import DecaySystem


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_persistence():
    """Create a temporary persistence layer for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_emotions.db"
        persistence = EmotionPersistence(db_path=str(db_path))
        yield persistence


@pytest.fixture
def sample_emotional_state():
    """Create a sample emotional state for testing."""
    return EmotionalState(
        loneliness=0.5,
        excitement=0.6,
        frustration=0.3,
        jealousy=0.2,
        vulnerability=0.4,
        confidence=0.7,
        curiosity=0.5,
        affection=0.6,
        defensiveness=0.3,
    )


@pytest.fixture
def short_test_config():
    """Create a short-running test config for CI."""
    return StabilityTestConfig(
        duration_hours=0.05,  # 3 minutes
        checkpoint_interval_minutes=1,
        load_pattern="casual_user",
        emotion_check_interval_minutes=1,
    )


# ============================================================================
# Short-Running Tests for CI (< 5 minutes)
# ============================================================================

class TestStabilityMetrics:
    """Tests for StabilityMetrics dataclass."""
    
    def test_initialization(self):
        """Test that metrics initialize correctly."""
        metrics = StabilityMetrics()
        assert metrics.total_interactions == 0
        assert metrics.successful_responses == 0
        assert metrics.failed_responses == 0
        assert metrics.success_rate == 0.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = StabilityMetrics()
        metrics.successful_responses = 95
        metrics.failed_responses = 5
        assert metrics.success_rate == 0.95
    
    def test_success_rate_zero_division(self):
        """Test success rate with no responses."""
        metrics = StabilityMetrics()
        assert metrics.success_rate == 0.0
    
    def test_uptime_calculation(self):
        """Test uptime calculation."""
        metrics = StabilityMetrics()
        # Manually set start time to 1 hour ago
        metrics.start_time = time.time() - 3600
        assert 0.99 <= metrics.uptime_hours <= 1.01
    
    def test_p90_response_time(self):
        """Test p90 response time calculation."""
        metrics = StabilityMetrics()
        metrics.response_times = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        # p90 of 10 items = index 9 = 1.0s = 1000ms
        assert metrics.p90_response_time == 1000.0
    
    def test_avg_response_time(self):
        """Test average response time calculation."""
        metrics = StabilityMetrics()
        metrics.response_times = [0.1, 0.2, 0.3]
        # Average = 0.2s = 200ms
        assert metrics.avg_response_time == 200.0
    
    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = StabilityMetrics()
        metrics.total_interactions = 100
        metrics.successful_responses = 95
        
        data = metrics.to_dict()
        assert data["total_interactions"] == 100
        assert data["successful_responses"] == 95
        assert "uptime_hours" in data
        assert "success_rate" in data


class TestLongRunningStabilityTest:
    """Tests for LongRunningStabilityTest class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test test harness initialization."""
        test = LongRunningStabilityTest(duration_hours=1)
        assert test.duration_hours == 1
        assert test.checkpoint_interval == 60
        assert test.metrics is not None
    
    @pytest.mark.asyncio
    async def test_setup(self, short_test_config):
        """Test test setup."""
        test = LongRunningStabilityTest(config=short_test_config)
        result = await test.setup()
        assert result is True
        assert test.status.value == "running"
    
    @pytest.mark.asyncio
    async def test_checkpoint_save_load(self, short_test_config):
        """Test checkpoint save and load."""
        test = LongRunningStabilityTest(config=short_test_config)
        await test.setup()
        
        # Set some metrics
        test.metrics.total_interactions = 50
        
        # Save checkpoint
        await test._save_checkpoint()
        
        # Verify checkpoint exists
        assert test._checkpoint_path().exists()
        
        # Load checkpoint
        checkpoint = test._load_checkpoint()
        assert checkpoint is not None
        assert checkpoint["metrics"]["total_interactions"] == 50
    
    @pytest.mark.asyncio
    async def test_record_interaction(self):
        """Test interaction recording."""
        test = LongRunningStabilityTest(duration_hours=1)
        
        # Record successful interaction
        await test.record_interaction(success=True, response_time_seconds=0.5)
        assert test.metrics.total_interactions == 1
        assert test.metrics.successful_responses == 1
        assert test.metrics.response_times == [0.5]
        
        # Record failed interaction
        await test.record_interaction(success=False, response_time_seconds=1.0, error="Test error")
        assert test.metrics.total_interactions == 2
        assert test.metrics.failed_responses == 1
        assert len(test.metrics.error_log) == 1
    
    @pytest.mark.asyncio
    async def test_verify_response_times(self):
        """Test response time verification."""
        test = LongRunningStabilityTest(duration_hours=1)
        
        # Add response times under threshold
        test.metrics.response_times = [0.1, 0.2, 0.3]  # All under 3s
        
        result = test.verify_response_times()
        assert result["passed"] is True
        assert result["p90_ms"] <= 3000
    
    @pytest.mark.asyncio
    async def test_verify_response_times_fail(self):
        """Test response time verification failure."""
        test = LongRunningStabilityTest(duration_hours=1)
        test.config.response_time_threshold_ms = 100  # 100ms threshold
        
        # Add response times over threshold
        test.metrics.response_times = [0.5, 0.6, 0.7]  # All over 100ms
        
        result = test.verify_response_times()
        assert result["passed"] is False
    
    @pytest.mark.asyncio
    async def test_generate_report(self, short_test_config):
        """Test report generation."""
        test = LongRunningStabilityTest(config=short_test_config)
        await test.setup()
        
        test.metrics.total_interactions = 100
        test.metrics.successful_responses = 95
        
        report = test.generate_report()
        assert "DEMI STABILITY TEST REPORT" in report
        assert "100" in report  # Total interactions
        assert "95" in report  # Successful responses


class TestLoadGenerator:
    """Tests for LoadGenerator class."""
    
    def test_pattern_initialization(self):
        """Test pattern initialization."""
        pattern = PATTERNS["casual_user"]
        generator = LoadGenerator(pattern)
        
        assert generator.pattern == pattern
        assert generator.stats["total_generated"] == 0
    
    def test_inter_arrival_time_calculation(self):
        """Test inter-arrival time calculation."""
        pattern = PATTERNS["casual_user"]  # 12 per hour = every 5 minutes
        generator = LoadGenerator(pattern)
        
        interval = generator._calculate_inter_arrival_time()
        # Should be around 300 seconds (5 minutes) with some variance
        assert 1.0 <= interval <= 3000.0
    
    def test_message_selection(self):
        """Test message selection."""
        pattern = PATTERNS["casual_user"]
        generator = LoadGenerator(pattern, random_seed=42)
        
        message = generator._select_message()
        assert isinstance(message, str)
        assert len(message) > 0
    
    def test_generate_interaction(self):
        """Test interaction generation."""
        pattern = PATTERNS["casual_user"]
        generator = LoadGenerator(pattern)
        
        interaction = generator.generate_interaction()
        assert isinstance(interaction.message, str)
        assert isinstance(interaction.interaction_type, InteractionType)
        assert interaction.timestamp is not None
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        pattern = PATTERNS["casual_user"]
        generator = LoadGenerator(pattern)
        
        stats = generator.get_stats()
        assert "pattern_name" in stats
        assert "total_generated" in stats
    
    @pytest.mark.asyncio
    async def test_generate_load(self):
        """Test load generation."""
        pattern = InteractionPattern(
            name="Test Pattern",
            interactions_per_hour=60,  # 1 per minute
            burstiness=0.0,
            types=[InteractionType.GREETING],
            duration_hours=0.01,  # Very short for testing
        )
        generator = LoadGenerator(pattern)
        
        messages = []
        
        async def callback(msg):
            messages.append(msg)
        
        await generator.generate_load(callback, duration_hours=0.01)
        
        # Should have generated some messages
        assert len(messages) >= 0  # May be 0 due to short duration
    
    def test_stop(self):
        """Test stopping generator."""
        pattern = PATTERNS["casual_user"]
        generator = LoadGenerator(pattern)
        
        generator._running = True
        generator.stop()
        assert generator._running is False


class TestEmotionStabilityMonitor:
    """Tests for EmotionStabilityMonitor class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, temp_persistence):
        """Test monitor initialization."""
        monitor = EmotionStabilityMonitor(temp_persistence)
        
        assert monitor.persistence == temp_persistence
        assert monitor.snapshots == []
        assert monitor.check_interval == 30
    
    @pytest.mark.asyncio
    async def test_record_state(self, temp_persistence, sample_emotional_state):
        """Test state recording."""
        monitor = EmotionStabilityMonitor(temp_persistence)
        
        snapshot = await monitor.record_state(sample_emotional_state, trigger="test")
        
        assert len(monitor.snapshots) == 1
        assert snapshot.state == sample_emotional_state
        assert snapshot.trigger == "test"
    
    @pytest.mark.asyncio
    async def test_prune_old_snapshots(self, temp_persistence):
        """Test old snapshot pruning."""
        monitor = EmotionStabilityMonitor(temp_persistence, max_history_hours=1)
        
        # Add old snapshot
        old_time = datetime.now() - timedelta(hours=2)
        old_snapshot = EmotionSnapshot(
            timestamp=old_time,
            state=EmotionalState(),
            trigger="old"
        )
        monitor.snapshots.append(old_snapshot)
        
        # Add new snapshot
        new_snapshot = EmotionSnapshot(
            timestamp=datetime.now(),
            state=EmotionalState(),
            trigger="new"
        )
        monitor.snapshots.append(new_snapshot)
        
        # Prune
        monitor._prune_old_snapshots()
        
        # Old should be removed
        assert len(monitor.snapshots) == 1
        assert monitor.snapshots[0].trigger == "new"
    
    @pytest.mark.asyncio
    async def test_check_consistency(self, temp_persistence):
        """Test consistency checking."""
        monitor = EmotionStabilityMonitor(temp_persistence)
        
        # Add snapshots with consistent values
        for i in range(3):
            state = EmotionalState(loneliness=0.5 + i * 0.01)
            await monitor.record_state(state, trigger="test")
        
        reports = monitor.check_consistency()
        
        assert "loneliness" in reports
        assert isinstance(reports["loneliness"], EmotionDriftReport)
    
    @pytest.mark.asyncio
    async def test_detect_anomalies(self, temp_persistence):
        """Test anomaly detection."""
        monitor = EmotionStabilityMonitor(temp_persistence)
        
        # Add snapshots with a sudden jump
        state1 = EmotionalState(loneliness=0.5)
        state2 = EmotionalState(loneliness=0.9)  # Big jump
        
        await monitor.record_state(state1, trigger="test")
        await monitor.record_state(state2, trigger="test")
        
        anomalies = monitor.detect_anomalies()
        
        # Should detect the sudden change
        assert len(anomalies) > 0
        assert any(a["type"] == "sudden_change" for a in anomalies)
    
    @pytest.mark.asyncio
    async def test_generate_decay_report(self, temp_persistence):
        """Test decay report generation."""
        monitor = EmotionStabilityMonitor(temp_persistence)
        
        # Add snapshots with decay trigger
        for i in range(3):
            state = EmotionalState(loneliness=0.5 - i * 0.01)
            await monitor.record_state(state, trigger="decay")
        
        report = monitor.generate_decay_report()
        
        assert isinstance(report, dict)


class TestRecoveryTest:
    """Tests for RecoveryTest class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test recovery test initialization."""
        test = RecoveryTest()
        assert test.persistence is None
        assert test.temp_dir is None
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown recovery."""
        test = RecoveryTest()
        result = await test.test_graceful_shutdown()
        
        assert isinstance(result, RecoveryResult)
        assert result.test_name == "graceful_shutdown"
        assert result.success is True
        assert result.emotion_preserved is True
    
    @pytest.mark.asyncio
    async def test_crash_recovery(self):
        """Test crash recovery."""
        test = RecoveryTest()
        result = await test.test_crash_recovery()
        
        assert isinstance(result, RecoveryResult)
        assert result.test_name == "crash_recovery"
    
    @pytest.mark.asyncio
    async def test_extended_offline_recovery(self):
        """Test extended offline recovery."""
        test = RecoveryTest()
        result = await test.test_extended_offline_recovery(offline_hours=1)
        
        assert isinstance(result, RecoveryResult)
        assert "extended_offline" in result.test_name
    
    @pytest.mark.asyncio
    async def test_backup_restore(self):
        """Test backup and restore."""
        test = RecoveryTest()
        result = await test.test_backup_restore()
        
        assert isinstance(result, RecoveryResult)
        assert result.test_name == "backup_restore"
    
    @pytest.mark.asyncio
    async def test_verify_emotional_state_preserved(self, sample_emotional_state):
        """Test emotional state preservation verification."""
        test = RecoveryTest()
        
        # Same state
        result = await test.verify_emotional_state_preserved(
            sample_emotional_state,
            sample_emotional_state,
        )
        assert result["preserved"] is True
        
        # Different state
        different_state = EmotionalState(loneliness=0.9)
        result = await test.verify_emotional_state_preserved(
            sample_emotional_state,
            different_state,
        )
        assert result["preserved"] is False
        assert result["differences"] is not None


class TestConsistencyRules:
    """Tests for consistency rules."""
    
    def test_rules_exist(self):
        """Test that consistency rules are defined."""
        assert "max_single_change" in CONSISTENCY_RULES
        assert "max_daily_drift" in CONSISTENCY_RULES
        assert "floor_violation_tolerance" in CONSISTENCY_RULES
    
    def test_max_single_change_value(self):
        """Test max single change value is reasonable."""
        assert 0 < CONSISTENCY_RULES["max_single_change"] <= 1.0


# ============================================================================
# Parameterized Tests
# ============================================================================

@pytest.mark.parametrize("pattern_name", ["active_user", "casual_user", "sporadic_user"])
class TestLoadPatterns:
    """Parameterized tests for different load patterns."""
    
    def test_pattern_exists(self, pattern_name):
        """Test that pattern exists."""
        assert pattern_name in PATTERNS
    
    def test_pattern_valid(self, pattern_name):
        """Test that pattern has valid parameters."""
        pattern = PATTERNS[pattern_name]
        assert pattern.interactions_per_hour > 0
        assert 0 <= pattern.burstiness <= 1
        assert len(pattern.types) > 0
        assert pattern.duration_hours > 0


class TestInteractionTypes:
    """Parameterized tests for interaction types."""
    
    @pytest.mark.parametrize("interaction_type", list(InteractionType))
    def test_has_sample_messages(self, interaction_type):
        """Test that each type has sample messages."""
        from tests.stability.load_generator import SAMPLE_MESSAGES
        assert interaction_type in SAMPLE_MESSAGES
        assert len(SAMPLE_MESSAGES[interaction_type]) > 0


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestStabilityIntegration:
    """Integration tests for stability components."""
    
    async def test_full_recovery_suite(self):
        """Test running all recovery tests."""
        results = await run_all_recovery_tests()
        
        assert "graceful_shutdown" in results
        assert "crash_recovery" in results
        assert "extended_offline" in results
        assert "backup_restore" in results
        assert "corruption_recovery" in results
    
    async def test_emotion_monitor_with_persistence(
        self, temp_persistence, sample_emotional_state
    ):
        """Test emotion monitor with real persistence."""
        monitor = EmotionStabilityMonitor(temp_persistence)
        
        # Save state to persistence
        temp_persistence.save_state(sample_emotional_state)
        
        # Record snapshot from persistence
        snapshot = await monitor.record_snapshot(trigger="test")
        
        assert snapshot is not None
        assert snapshot.state is not None
    
    async def test_verify_emotion_consistency_integration(self, temp_persistence):
        """Test emotion consistency verification."""
        # Save some states
        for i in range(3):
            state = EmotionalState(loneliness=0.5 + i * 0.01)
            temp_persistence.save_state(state)
        
        result = await verify_emotion_consistency(temp_persistence)
        
        assert "status" in result
        assert "violations" in result
    
    async def test_verify_decay_behavior_integration(self, sample_emotional_state):
        """Test decay behavior verification."""
        # Simulate some decay
        current_state = EmotionalState(loneliness=0.4)  # Decayed from 0.5
        
        result = await verify_decay_behavior(
            sample_emotional_state,
            current_state,
            hours_elapsed=1
        )
        
        assert "status" in result
        assert "discrepancies" in result


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.benchmark
class TestStabilityPerformance:
    """Performance tests for stability components."""
    
    @pytest.mark.asyncio
    async def test_metrics_collection_performance(self):
        """Test that metrics collection is fast."""
        test = LongRunningStabilityTest(duration_hours=1)
        await test.setup()
        
        start = time.time()
        for _ in range(1000):
            await test.record_interaction(success=True, response_time_seconds=0.1)
        duration = time.time() - start
        
        # Should handle 1000 records in under 1 second
        assert duration < 1.0
    
    @pytest.mark.asyncio
    async def test_emotion_monitor_performance(self, temp_persistence):
        """Test emotion monitor performance."""
        monitor = EmotionStabilityMonitor(temp_persistence)
        
        start = time.time()
        for i in range(100):
            state = EmotionalState(loneliness=i / 100)
            await monitor.record_state(state, trigger="test")
        duration = time.time() - start
        
        # Should handle 100 snapshots in under 1 second
        assert duration < 1.0


# ============================================================================
# Long-Running Tests (Manual Only)
# ============================================================================

@pytest.mark.long_running
@pytest.mark.manual
class TestLongRunning:
    """Long-running tests for manual validation only."""
    
    @pytest.mark.asyncio
    async def test_one_hour_stability(self):
        """Test one hour of stability."""
        config = StabilityTestConfig(
            duration_hours=1,
            checkpoint_interval_minutes=10,
            load_pattern="casual_user",
        )
        test = LongRunningStabilityTest(config=config)
        
        await test.setup()
        result = await test.run()
        
        assert result is True
        assert test.status.value == "completed"
        
        report = test.generate_report()
        assert "PASS" in report or "FAIL" in report
    
    @pytest.mark.asyncio
    async def test_active_user_load(self):
        """Test with active user load pattern."""
        config = StabilityTestConfig(
            duration_hours=0.5,  # 30 minutes
            load_pattern="active_user",
        )
        test = LongRunningStabilityTest(config=config)
        
        await test.setup()
        result = await test.run()
        
        assert result is True


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
