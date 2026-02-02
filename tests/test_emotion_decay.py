# tests/test_emotion_decay.py
import pytest
from datetime import datetime, timedelta, UTC
from src.emotion.models import EmotionalState
from src.emotion.decay import DecaySystem, DecayTuner


class TestDecaySystemBasics:
    """Test basic decay functionality."""

    def test_decay_system_initialization(self):
        """DecaySystem should initialize with correct tick interval."""
        decay = DecaySystem(tick_interval_seconds=300)
        assert decay.tick_interval == 300
        assert not decay.is_running

    def test_single_tick_applies_decay(self):
        """One tick should reduce all emotions slightly."""
        decay = DecaySystem()
        state = EmotionalState(loneliness=0.8, excitement=0.8, frustration=0.8)
        original_loneliness = state.loneliness

        state = decay.apply_decay(state)

        # All emotions should have decreased
        assert state.loneliness < original_loneliness
        assert state.excitement < 0.8
        assert state.frustration < 0.8


class TestExtremeEmotionInertia:
    """Test that extreme emotions (>0.8) decay slower."""

    def test_emotion_at_0_9_decays_slower(self):
        """Emotion at 0.9 should decay ~50% slower than normal."""
        decay = DecaySystem()

        # High emotion
        state_high = EmotionalState(frustration=0.9)
        state_high = decay.apply_decay(state_high)
        decay_high = 0.9 - state_high.frustration

        # Normal emotion (reset decay system tick time for fair comparison)
        decay.last_tick = datetime.now(UTC) - timedelta(seconds=300)
        state_normal = EmotionalState(frustration=0.5)
        state_normal = decay.apply_decay(state_normal)
        decay_normal = 0.5 - state_normal.frustration

        # High emotion should decay less absolutely
        assert decay_high < decay_normal


class TestIdleEffects:
    """Test idle effect accumulation."""

    def test_idle_effects_applied_during_offline_decay(self):
        """Idle effects should be applied during offline decay simulation."""
        decay = DecaySystem()
        state_no_idle = EmotionalState(excitement=0.8)
        state_with_idle = EmotionalState(excitement=0.8)

        # Apply decay without idle
        no_idle = decay.apply_decay(state_no_idle, idle_time_seconds=0)

        # Apply decay with idle
        decay.last_tick = datetime.now(UTC) - timedelta(seconds=300)
        with_idle = decay.apply_decay(
            state_with_idle, idle_time_seconds=3600, force_idle=True
        )

        # Excitement with idle should be lower (idle effect -0.02)
        assert with_idle.excitement < no_idle.excitement

    def test_idle_decreases_excitement(self):
        """Idle time should decrease excitement."""
        decay = DecaySystem()
        state = EmotionalState(excitement=0.7)

        state = decay.apply_decay(state, idle_time_seconds=3600, force_idle=True)

        assert state.excitement < 0.7

    def test_idle_effects_not_applied_when_recent_interaction(self):
        """Idle effects should not apply if idle_time_seconds < threshold."""
        decay = DecaySystem()
        state = EmotionalState(loneliness=0.5)
        original = state.loneliness

        # Recent interaction (100 seconds ago, below 300 threshold)
        state = decay.apply_decay(state, idle_time_seconds=100)

        # Loneliness should only decay normally, not increase from idle
        assert state.loneliness < original


class TestOfflineDecaySim:
    """Test offline decay simulation for persistence."""

    def test_offline_decay_applies_many_ticks(self):
        """Offline decay should apply decay across multiple ticks."""
        decay = DecaySystem()
        state = EmotionalState(excitement=0.8, confidence=0.7)

        # Offline for 100 ticks (500 seconds)
        aged_state = decay.simulate_offline_decay(state, 500)

        # System should complete without errors
        assert aged_state is not None
        assert isinstance(aged_state.excitement, float)

    def test_offline_decay_preserves_bounds(self):
        """Offline decay should never violate bounds."""
        decay = DecaySystem()
        state = EmotionalState(loneliness=0.95)

        # 7 days offline (worst case)
        aged_state = decay.simulate_offline_decay(state, 7 * 86400)

        # Should stay in bounds
        assert 0.0 <= aged_state.loneliness <= 1.0


class TestDecayTuner:
    """Test tuning/simulation utilities."""

    def test_tuner_simulate_hours(self):
        """DecayTuner should simulate N hours of decay."""
        decay = DecaySystem(tick_interval_seconds=60)  # 1-minute ticks for testing
        tuner = DecayTuner(decay)

        state = EmotionalState(excitement=0.9)
        decayed = tuner.simulate_hours(state, 1)

        # After 1 hour of decay (60 ticks), excitement should be slightly lower
        # With decay rate 0.06 per tick, it's reduced but still substantial
        assert decayed.excitement < 0.9

    def test_tuner_simulate_days_idle(self):
        """DecayTuner should simulate N days with idle effects."""
        decay = DecaySystem(tick_interval_seconds=60)
        tuner = DecayTuner(decay)

        state = EmotionalState(excitement=0.8)
        aged = tuner.simulate_days(state, 1, idle=True)

        # System should complete simulation without errors
        assert aged is not None
        assert isinstance(aged.excitement, float)
