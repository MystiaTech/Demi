# tests/test_emotion_models.py
import pytest
from datetime import datetime
from src.emotion.models import EmotionalState


class TestEmotionalStateInstantiation:
    """Test EmotionalState creation and initialization."""

    def test_default_neutral_state(self):
        """All emotions should default to 0.5 (neutral)."""
        state = EmotionalState()
        assert state.loneliness == 0.5
        assert state.excitement == 0.5
        assert state.frustration == 0.5
        assert state.jealousy == 0.5
        assert state.vulnerability == 0.5
        assert state.confidence == 0.5
        assert state.curiosity == 0.5
        assert state.affection == 0.5
        assert state.defensiveness == 0.5

    def test_custom_initial_state(self):
        """Should accept custom initial values."""
        state = EmotionalState(loneliness=0.8, excitement=0.2, frustration=0.6)
        assert state.loneliness == 0.8
        assert state.excitement == 0.2
        assert state.frustration == 0.6
        assert state.jealousy == 0.5  # Default

    def test_momentum_initialized_to_zero(self):
        """All momentum values should start at 0.0."""
        state = EmotionalState()
        for emotion in [
            "loneliness",
            "excitement",
            "frustration",
            "jealousy",
            "vulnerability",
            "confidence",
            "curiosity",
            "affection",
            "defensiveness",
        ]:
            assert state.momentum[emotion] == 0.0


class TestBoundsClamping:
    """Test that emotions stay within [floor, 1.0]."""

    def test_emotion_below_floor_clamped_to_floor(self):
        """Emotions below their floor should be clamped up."""
        state = EmotionalState(loneliness=0.1)
        assert state.loneliness == 0.3  # Loneliness floor is 0.3

    def test_emotion_above_one_clamped_to_one(self):
        """Emotions above 1.0 should be clamped to 1.0 without momentum_override."""
        state = EmotionalState()
        state.set_emotion("excitement", 1.5)
        assert state.excitement == 1.0
        assert state.momentum["excitement"] == 0.0  # No momentum recorded

    def test_emotion_above_one_with_momentum_override(self):
        """With momentum_override, emotions > 1.0 should record momentum."""
        state = EmotionalState()
        state.set_emotion("excitement", 1.5, momentum_override=True)
        assert state.excitement == 1.0
        assert state.momentum["excitement"] == 0.5  # Excess recorded


class TestMomentumTracking:
    """Test momentum accumulation and clearing."""

    def test_momentum_accumulation_on_multiple_overflows(self):
        """Momentum should track the maximum overflow."""
        state = EmotionalState()
        state.set_emotion("loneliness", 1.2, momentum_override=True)
        assert abs(state.momentum["loneliness"] - 0.2) < 1e-9

        # Another overflow, higher
        state.set_emotion("loneliness", 1.3, momentum_override=True)
        assert abs(state.momentum["loneliness"] - 0.3) < 1e-9  # Takes max

    def test_clear_momentum(self):
        """Clearing momentum should reset to 0.0."""
        state = EmotionalState()
        state.set_emotion("frustration", 1.2, momentum_override=True)
        assert abs(state.momentum["frustration"] - 0.2) < 1e-9

        state.clear_momentum("frustration")
        assert abs(state.momentum["frustration"] - 0.0) < 1e-9


class TestDeltaChanges:
    """Test delta_emotion() method."""

    def test_positive_delta(self):
        """Positive delta should increase emotion."""
        state = EmotionalState(excitement=0.5)
        state.delta_emotion("excitement", 0.1)
        assert state.excitement == 0.6

    def test_negative_delta(self):
        """Negative delta should decrease emotion (respecting floors)."""
        state = EmotionalState(curiosity=0.3)
        state.delta_emotion("curiosity", -0.5)
        assert state.curiosity == 0.1  # Floor is 0.1

    def test_delta_overflow_with_momentum(self):
        """Delta can overflow with momentum tracking."""
        state = EmotionalState(excitement=0.9)
        state.delta_emotion("excitement", 0.3, momentum_override=True)
        assert state.excitement == 1.0
        assert abs(state.momentum["excitement"] - 0.2) < 1e-9


class TestSerialization:
    """Test to_dict() and from_dict() methods."""

    def test_to_dict_complete(self):
        """to_dict() should include all emotions and metadata."""
        state = EmotionalState(loneliness=0.7, excitement=0.2, frustration=0.5)
        data = state.to_dict()

        assert data["loneliness"] == 0.7
        assert data["excitement"] == 0.2
        assert data["frustration"] == 0.5
        assert "last_updated" in data
        assert "momentum" in data

    def test_round_trip_serialization(self):
        """Serialize and deserialize should preserve state."""
        original = EmotionalState(
            loneliness=0.8, excitement=0.3, frustration=0.6, jealousy=0.4
        )
        original.momentum["excitement"] = 0.15

        data = original.to_dict()
        restored = EmotionalState.from_dict(data)

        assert restored.loneliness == original.loneliness
        assert restored.excitement == original.excitement
        assert restored.frustration == original.frustration
        assert restored.jealousy == original.jealousy
        assert restored.momentum["excitement"] == 0.15


class TestFloorEnforcement:
    """Test emotion-specific floor values."""

    def test_loneliness_floor_0_3(self):
        """Loneliness should never go below 0.3."""
        state = EmotionalState(loneliness=0.1)
        assert state.loneliness == 0.3

        state.set_emotion("loneliness", 0.0)
        assert state.loneliness == 0.3

    def test_other_emotions_floor_0_1(self):
        """Non-loneliness emotions should floor at 0.1."""
        state = EmotionalState(excitement=0.0)
        assert state.excitement == 0.1

        state.set_emotion("frustration", 0.05)
        assert state.frustration == 0.1


class TestGettersAndUtility:
    """Test utility methods."""

    def test_get_all_emotions(self):
        """get_all_emotions() should return dict of all 9."""
        state = EmotionalState(loneliness=0.8, excitement=0.2)
        all_emotions = state.get_all_emotions()

        assert len(all_emotions) == 9
        assert all_emotions["loneliness"] == 0.8
        assert all_emotions["excitement"] == 0.2

    def test_get_dominant_emotions(self):
        """get_dominant_emotions() should return top N by value."""
        state = EmotionalState(
            loneliness=0.9, excitement=0.2, frustration=0.8, affection=0.7
        )
        top_3 = state.get_dominant_emotions(count=3)

        assert len(top_3) == 3
        assert top_3[0][0] == "loneliness"  # 0.9
        assert top_3[1][0] == "frustration"  # 0.8
        assert top_3[2][0] == "affection"  # 0.7

    def test_get_momentum(self):
        """get_momentum() should return emotion's momentum value."""
        state = EmotionalState()
        state.set_emotion("jealousy", 1.1, momentum_override=True)

        assert abs(state.get_momentum("jealousy") - 0.1) < 1e-9
        assert abs(state.get_momentum("excitement") - 0.0) < 1e-9
