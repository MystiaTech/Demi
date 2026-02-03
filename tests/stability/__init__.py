"""
Long-Running Stability Tests for Demi.

This module provides infrastructure for testing Demi's ability to operate
continuously for 7+ days without manual intervention.

Exports:
    - LongRunningStabilityTest: Main stability test harness
    - StabilityMetrics: Metrics collection dataclass
    - StabilityTestConfig: Configuration for stability tests
    - LoadGenerator: Simulated user interaction generator
    - LoadPattern: Enum for different load patterns
    - EmotionStabilityMonitor: Emotional state consistency verification
    - EmotionSnapshot: Snapshot of emotional state at a point in time
    - EmotionDriftReport: Report on emotional state drift over time
    - RecoveryTest: Automatic restart and recovery testing
    - RecoveryResult: Result of a recovery test

Requirements:
    - HEALTH-01: 7-day continuous operation validation
    - HEALTH-03: Emotional state preserved across restarts

Example:
    >>> from tests.stability import LongRunningStabilityTest, LoadGenerator, LoadPattern
    >>> test = LongRunningStabilityTest(duration_hours=168)  # 7 days
    >>> await test.setup()
    >>> await test.run()
"""

from tests.stability.long_running import (
    LongRunningStabilityTest,
    StabilityMetrics,
    StabilityTestConfig,
)
from tests.stability.load_generator import (
    LoadGenerator,
    LoadPattern,
    InteractionPattern,
    MultiPatternLoadGenerator,
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

__all__ = [
    # Long-running test
    "LongRunningStabilityTest",
    "StabilityMetrics",
    "StabilityTestConfig",
    # Load generator
    "LoadGenerator",
    "LoadPattern",
    "InteractionPattern",
    "MultiPatternLoadGenerator",
    # Emotion monitor
    "EmotionStabilityMonitor",
    "EmotionSnapshot",
    "EmotionDriftReport",
    "verify_emotion_consistency",
    "verify_emotion_persistence_integrity",
    "verify_decay_behavior",
    "CONSISTENCY_RULES",
    # Recovery test
    "RecoveryTest",
    "RecoveryResult",
    "simulate_crash_recovery",
    "test_backup_restore",
    "run_all_recovery_tests",
]
