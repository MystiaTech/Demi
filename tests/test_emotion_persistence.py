# tests/test_emotion_persistence.py
import pytest
import os
import tempfile
import sqlite3
from datetime import datetime, timedelta, timezone
from src.emotion.models import EmotionalState
from src.emotion.persistence import EmotionPersistence
from src.emotion.decay import DecaySystem
from src.emotion.interactions import InteractionType


class TestEmotionPersistenceBasics:
    """Test basic save/load operations."""

    def test_persistence_initialization(self):
        """Should create database and schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            persistence = EmotionPersistence(db_path=db_path)

            # Database file should exist
            assert os.path.exists(db_path)

    def test_save_and_load_state(self):
        """Should save and retrieve emotional state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            persistence = EmotionPersistence(db_path=db_path)

            # Create and save state
            original = EmotionalState(loneliness=0.8, excitement=0.3, frustration=0.5)
            original.momentum["excitement"] = 0.1

            assert persistence.save_state(original)

            # Load it back
            loaded = persistence.load_latest_state()
            assert loaded is not None
            assert loaded.loneliness == 0.8
            assert loaded.excitement == 0.3
            assert loaded.frustration == 0.5
            assert loaded.momentum["excitement"] == 0.1


class TestOfflineDecayRecovery:
    """Test restore_and_age_state simulates offline decay."""

    def test_restore_and_age_simulates_offline_decay(self):
        """Loading state should apply offline decay."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            persistence = EmotionPersistence(db_path=db_path)
            decay_system = DecaySystem(tick_interval_seconds=60)

            # Create a state with high excitement (should decay)
            original = EmotionalState(excitement=0.9)
            persistence.save_state(original)

            # Simulate being offline for 1 hour
            # We need to manually set the timestamp in the database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            cursor.execute(
                "UPDATE emotional_state SET timestamp = ? WHERE id = (SELECT MAX(id) FROM emotional_state)",
                (one_hour_ago,),
            )
            conn.commit()
            conn.close()

            # Restore and age
            aged = persistence.restore_and_age_state(decay_system)

            # Excitement should be lower (decayed)
            assert aged is not None
            assert aged.excitement < 0.9


class TestInteractionLogging:
    """Test interaction logging and history."""

    def test_log_interaction(self):
        """Should log interaction with before/after states."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            persistence = EmotionPersistence(db_path=db_path)

            state_before = EmotionalState(excitement=0.5)
            state_after = EmotionalState(excitement=0.7)

            effects = {
                "interaction_type": "positive_message",
                "emotions_changed": {"excitement": {"delta": 0.2, "new_value": 0.7}},
            }

            result = persistence.log_interaction(
                InteractionType.POSITIVE_MESSAGE,
                state_before,
                state_after,
                effects,
                user_message="That's awesome!",
                confidence_level=0.95,
            )

            assert result

    def test_retrieve_interaction_history(self):
        """Should retrieve logged interactions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            persistence = EmotionPersistence(db_path=db_path)

            # Log multiple interactions
            state_before = EmotionalState()
            state_after = EmotionalState(excitement=0.7)
            effects = {"interaction_type": "positive_message"}

            persistence.log_interaction(
                InteractionType.POSITIVE_MESSAGE,
                state_before,
                state_after,
                effects,
            )
            persistence.log_interaction(
                InteractionType.ERROR_OCCURRED,
                state_after,
                EmotionalState(frustration=0.7),
                effects,
            )

            history = persistence.get_interaction_history()

            assert len(history) >= 2
            assert history[0]["interaction_type"] == "error_occurred"  # Most recent


class TestBackupAndRecovery:
    """Test backup snapshot and recovery."""

    def test_create_backup_snapshot(self):
        """Should create backup snapshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            persistence = EmotionPersistence(db_path=db_path)

            state = EmotionalState(loneliness=0.8)
            persistence.create_backup_snapshot(state, snapshot_type="manual")

            # Should be in database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM state_snapshots")
            count = cursor.fetchone()[0]
            conn.close()

            assert count >= 1

    def test_restore_from_backup(self):
        """Should restore state from backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "emotions.db")
            persistence = EmotionPersistence(db_path=db_path)

            state = EmotionalState(loneliness=0.8, excitement=0.3, frustration=0.5)
            persistence.create_backup_snapshot(state)

            # Restore
            restored = persistence.restore_from_backup()

            assert restored is not None
            assert restored.loneliness == 0.8
            assert restored.excitement == 0.3
