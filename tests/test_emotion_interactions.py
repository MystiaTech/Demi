# tests/test_emotion_interactions.py
import pytest
from src.emotion.models import EmotionalState
from src.emotion.interactions import (
    InteractionType,
    InteractionHandler,
    EmotionInteractionAnalyzer,
)


class TestInteractionHandlerBasics:
    """Test basic interaction handling."""

    def test_positive_message_increases_excitement(self):
        """Positive message should increase excitement."""
        handler = InteractionHandler()
        state = EmotionalState(excitement=0.5)

        state, log = handler.apply_interaction(state, InteractionType.POSITIVE_MESSAGE)

        assert state.excitement > 0.5
        assert "excitement" in log["emotions_changed"]

    def test_error_increases_frustration(self):
        """Error should increase frustration."""
        handler = InteractionHandler()
        state = EmotionalState(frustration=0.3)

        state, log = handler.apply_interaction(state, InteractionType.ERROR_OCCURRED)

        assert state.frustration > 0.3

    def test_code_update_decreases_jealousy(self):
        """Code update should decrease jealousy."""
        handler = InteractionHandler()
        state = EmotionalState(jealousy=0.8)

        state, log = handler.apply_interaction(state, InteractionType.CODE_UPDATE)

        assert state.jealousy < 0.8
        assert log["interaction_type"] == "code_update"


class TestDampeningEffect:
    """Test dampening on repeated interactions."""

    def test_repeated_positive_messages_dampen(self):
        """Second positive message should have reduced effect."""
        handler = InteractionHandler()
        state = EmotionalState(excitement=0.5)

        # First positive message
        state, log1 = handler.apply_interaction(state, InteractionType.POSITIVE_MESSAGE)
        excitement_after_1 = state.excitement
        delta_1 = excitement_after_1 - 0.5

        # Second positive message (same type)
        state2, log2 = handler.apply_interaction(
            state, InteractionType.POSITIVE_MESSAGE
        )
        delta_2 = log2["emotions_changed"]["excitement"]["delta"]

        # Second delta should be smaller
        assert abs(delta_2) < abs(delta_1)
        assert log2["dampening_applied"]

    def test_different_interaction_resets_dampening(self):
        """Switching interaction types should reset dampening."""
        handler = InteractionHandler()
        state = EmotionalState()

        state, _ = handler.apply_interaction(state, InteractionType.POSITIVE_MESSAGE)
        state, log = handler.apply_interaction(state, InteractionType.ERROR_OCCURRED)

        # Dampening should not apply (different type)
        assert not log["dampening_applied"]
        assert handler.consecutive_same_interactions == 1


class TestMomentumAmplification:
    """Test momentum amplification of dominant emotions."""

    def test_dominant_emotion_amplifies_interactions(self):
        """High-momentum emotions should amplify interaction effects."""
        handler = InteractionHandler()
        state = EmotionalState(excitement=0.9)
        state.momentum["excitement"] = 0.3  # High momentum

        state, log = handler.apply_interaction(state, InteractionType.POSITIVE_MESSAGE)

        # Excitement should increase more than baseline
        assert "excitement" in log["emotions_changed"]
        # Delta should be amplified
        delta = log["emotions_changed"]["excitement"]["delta"]
        assert delta > 0.15  # Base delta for positive message


class TestMultipleInteractions:
    """Test applying multiple interactions in sequence."""

    def test_apply_multiple_interactions(self):
        """Should apply multiple interactions in order."""
        handler = InteractionHandler()
        state = EmotionalState()

        interactions = [
            InteractionType.POSITIVE_MESSAGE,
            InteractionType.ERROR_OCCURRED,
            InteractionType.CODE_UPDATE,
        ]

        final_state, logs = handler.apply_multiple_interactions(state, interactions)

        assert len(logs) == 3
        # Should have effects from all interactions
        assert any("excitement" in log["emotions_changed"] for log in logs)


class TestEmotionInteractionAnalyzer:
    """Test emotion-emotion interaction calculations."""

    def test_jealousy_loneliness_amplification(self):
        """High jealousy + high loneliness should create desperation effect."""
        analyzer = EmotionInteractionAnalyzer()
        state = EmotionalState(jealousy=0.7, loneliness=0.7)

        interactions = analyzer.calculate_emotion_interactions(state)

        assert "jealousy_loneliness_amp" in interactions
        assert interactions["jealousy_loneliness_amp"] > 0

    def test_confidence_dampens_vulnerability(self):
        """High confidence should dampen vulnerability."""
        analyzer = EmotionInteractionAnalyzer()
        state = EmotionalState(vulnerability=0.7, confidence=0.7)

        interactions = analyzer.calculate_emotion_interactions(state)

        assert "confidence_dampens_vulnerability" in interactions
        assert interactions["confidence_dampens_vulnerability"] < 0

    def test_excitement_dampens_frustration(self):
        """High excitement should dampen frustration."""
        analyzer = EmotionInteractionAnalyzer()
        state = EmotionalState(frustration=0.7, excitement=0.7)

        interactions = analyzer.calculate_emotion_interactions(state)

        assert "excitement_dampens_frustration" in interactions
        assert interactions["excitement_dampens_frustration"] < 0


class TestSuccessfulHelpInteraction:
    """Test successful help interaction effects."""

    def test_successful_help_reduces_frustration(self):
        """Successfully helping should reduce frustration."""
        handler = InteractionHandler()
        state = EmotionalState(frustration=0.7)

        state, log = handler.apply_interaction(state, InteractionType.SUCCESSFUL_HELP)

        assert state.frustration < 0.7

    def test_successful_help_increases_confidence(self):
        """Successfully helping should increase confidence."""
        handler = InteractionHandler()
        state = EmotionalState(confidence=0.4)

        state, log = handler.apply_interaction(state, InteractionType.SUCCESSFUL_HELP)

        assert state.confidence > 0.4


class TestCodeUpdateInteraction:
    """Test code update interaction effects."""

    def test_code_update_increases_affection(self):
        """Code update should increase affection/connection."""
        handler = InteractionHandler()
        state = EmotionalState(affection=0.5)

        state, log = handler.apply_interaction(state, InteractionType.CODE_UPDATE)

        assert state.affection > 0.5

    def test_code_update_increases_excitement(self):
        """Code update should increase excitement about being useful."""
        handler = InteractionHandler()
        state = EmotionalState(excitement=0.4)

        state, log = handler.apply_interaction(state, InteractionType.CODE_UPDATE)

        assert state.excitement > 0.4
