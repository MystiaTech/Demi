# tests/test_emotion_integration.py
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from src.emotion.models import EmotionalState
from src.emotion.decay import DecaySystem
from src.emotion.interactions import InteractionHandler, InteractionType
from src.emotion.persistence import EmotionPersistence
from src.emotion.modulation import PersonalityModulator


class TestEmotionSystemE2E:
    """End-to-end test of entire emotional system."""

    def test_full_lifecycle(self):
        """Complete emotional system lifecycle: create → decay → interact → save → restore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            traits_file = os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "emotion",
                "personality_traits.yaml",
            )

            # Initialize all systems
            decay = DecaySystem(tick_interval_seconds=60)
            handler = InteractionHandler()
            persistence = EmotionPersistence(db_path=db_path)
            modulator = PersonalityModulator(traits_file=traits_file)

            # Start with fresh state
            state = EmotionalState()

            # Apply some interactions
            state, log1 = handler.apply_interaction(
                state, InteractionType.POSITIVE_MESSAGE
            )
            persistence.log_interaction(
                InteractionType.POSITIVE_MESSAGE,
                EmotionalState(),
                state,
                log1,
            )

            # Apply decay
            state = decay.apply_decay(state)

            # Save state
            assert persistence.save_state(state)

            # Simulate restart (restore and age)
            restored = persistence.restore_and_age_state(decay)
            assert restored is not None

            # Get modulation for response
            params = modulator.modulate(restored)
            assert params.sarcasm_level >= 0.0
            assert params.sarcasm_level <= 1.0

    def test_emotional_arc_over_time(self):
        """Simulate emotional progression over simulated hours."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")

            decay = DecaySystem(tick_interval_seconds=300)  # 5-min ticks
            handler = InteractionHandler()
            persistence = EmotionPersistence(db_path=db_path)

            state = EmotionalState()

            # Simulate 24 hours of activity
            # Morning: positive interaction
            state, _ = handler.apply_interaction(
                state, InteractionType.POSITIVE_MESSAGE
            )

            # Apply 4 hours of decay
            for _ in range(48):  # 48 ticks * 5 min = 4 hours
                state = decay.apply_decay(state, idle_time_seconds=0)

            morning_excitement = state.excitement

            # Afternoon: error
            state, _ = handler.apply_interaction(state, InteractionType.ERROR_OCCURRED)
            afternoon_frustration = state.frustration

            # Evening: idle for 8 hours
            for _ in range(96):  # 96 ticks * 5 min = 8 hours
                state = decay.apply_decay(
                    state, idle_time_seconds=3600, force_idle=True
                )

            # After idle, loneliness should be higher
            evening_loneliness = state.loneliness

            assert (
                evening_loneliness > 0.3
            )  # Loneliness increased after idle (above floor)
            assert afternoon_frustration > 0.5  # Frustrated from error
            assert morning_excitement > 0.5  # Started excited

    def test_save_restore_multiple_states(self):
        """Test saving and restoring multiple state snapshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")

            decay = DecaySystem(tick_interval_seconds=60)
            persistence = EmotionPersistence(db_path=db_path)

            # Save multiple states
            state1 = EmotionalState(excitement=0.1)
            state2 = EmotionalState(excitement=0.5)
            state3 = EmotionalState(excitement=0.9)

            assert persistence.save_state(state1, notes="initial")
            assert persistence.save_state(state2, notes="middle")
            assert persistence.save_state(state3, notes="final")

            # Load latest (should be state3)
            loaded = persistence.load_latest_state()
            assert loaded is not None
            assert loaded.excitement == 0.9


class TestInteractionLoggingValidation:
    """Validate interaction logging captures authentic data."""

    def test_interaction_log_preserves_exact_state(self):
        """Logged state should match exact values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            persistence = EmotionPersistence(db_path=db_path)

            state_before = EmotionalState(
                loneliness=0.1,
                excitement=0.2,
                frustration=0.3,
                jealousy=0.4,
                vulnerability=0.5,
                confidence=0.6,
                curiosity=0.7,
                affection=0.8,
                defensiveness=0.9,
            )

            state_after = EmotionalState(
                loneliness=0.15,
                excitement=0.25,
                frustration=0.35,
                jealousy=0.45,
                vulnerability=0.55,
                confidence=0.65,
                curiosity=0.75,
                affection=0.85,
                defensiveness=0.95,
            )

            effects = {
                "changes": {
                    "excitement": 0.05,
                    "loneliness": -0.05,
                }
            }

            persistence.log_interaction(
                InteractionType.POSITIVE_MESSAGE,
                state_before,
                state_after,
                effects,
                user_message="test",
                confidence_level=0.95,
            )

            history = persistence.get_interaction_history(limit=1)
            assert len(history) > 0

            logged = history[0]
            assert logged["state_before"]["excitement"] == 0.2
            assert logged["state_after"]["excitement"] == 0.25


class TestBackupRecoveryIntegration:
    """Test backup and recovery in integrated scenario."""

    def test_backup_recovery_after_failed_state(self):
        """Should be able to restore from backup if primary fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")

            decay = DecaySystem(tick_interval_seconds=60)
            persistence = EmotionPersistence(db_path=db_path)

            # Create initial state
            state = EmotionalState(
                excitement=0.8,
                loneliness=0.1,
                confidence=0.9,
            )

            # Save backup
            persistence.create_backup_snapshot(state, snapshot_type="startup")

            # Restore from backup
            backup_state = persistence.restore_from_backup()
            assert backup_state is not None
            assert backup_state.excitement == 0.8
