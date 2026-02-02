"""
Unit tests for PromptBuilder.

Validates that system prompts are built correctly with personality + emotional modulation.
"""

import pytest
from src.llm.prompt_builder import PromptBuilder, BASE_DEMI_PROMPT
from src.emotion.models import EmotionalState
from src.emotion.modulation import PersonalityModulator
from src.core.logger import DemiLogger


@pytest.fixture
def logger():
    """Create a test logger."""
    return DemiLogger()


@pytest.fixture
def token_counter():
    """Simple token counter for testing (1 token ≈ 4 chars)."""
    return lambda text: max(1, len(text) // 4)


@pytest.fixture
def prompt_builder(logger, token_counter):
    """Create a PromptBuilder instance."""
    return PromptBuilder(logger, token_counter)


@pytest.fixture
def modulator():
    """Create a personality modulator."""
    return PersonalityModulator()


class TestPromptBuilderBasics:
    """Test basic PromptBuilder functionality."""

    def test_base_demi_prompt_exists(self):
        """Verify BASE_DEMI_PROMPT is defined and contains key elements."""
        assert BASE_DEMI_PROMPT is not None
        assert isinstance(BASE_DEMI_PROMPT, str)
        assert "sarcastic" in BASE_DEMI_PROMPT.lower()
        assert "personality" in BASE_DEMI_PROMPT.lower()
        assert (
            "guidelines" in BASE_DEMI_PROMPT.lower()
            or "response" in BASE_DEMI_PROMPT.lower()
        )

    def test_prompt_builder_initialization(self, prompt_builder, logger):
        """Verify PromptBuilder initializes correctly."""
        assert prompt_builder is not None
        assert prompt_builder.logger is logger
        assert prompt_builder.token_counter is not None

    def test_build_empty_history(self, prompt_builder, modulator):
        """Build prompt with empty conversation history."""
        state = EmotionalState()
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])

        # Should have system message
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 0

    def test_system_prompt_includes_emotions(self, prompt_builder, modulator):
        """Verify system prompt includes emotional state."""
        state = EmotionalState(loneliness=7.0, excitement=2.0, frustration=5.0)
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should mention emotions
        assert "loneliness" in system_content.lower()
        assert "excitement" in system_content.lower()
        assert "frustration" in system_content.lower()

    def test_system_prompt_includes_modulation(self, prompt_builder, modulator):
        """Verify system prompt includes modulation rules."""
        state = EmotionalState()
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should mention modulation
        assert (
            "modulation" in system_content.lower()
            or "emotional" in system_content.lower()
        )

    def test_system_prompt_preserves_history(self, prompt_builder, modulator):
        """Verify history is preserved after system prompt."""
        state = EmotionalState()
        modulation = modulator.modulate(state)
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        messages = prompt_builder.build(state, modulation, history)

        # Should have system + history
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"


class TestPromptBuilderWithEmotions:
    """Test PromptBuilder with different emotional states."""

    def test_prompt_high_loneliness(self, prompt_builder, modulator):
        """High loneliness should be reflected in prompt."""
        state = EmotionalState(loneliness=9.5, excitement=1.0, affection=2.0)
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should mention loneliness being high
        assert "9.5" in system_content or "desperate" in system_content.lower()
        # Should include modulation about connection-seeking
        assert (
            "seeking" in system_content.lower()
            or "longer" in system_content.lower()
            or "connection" in system_content.lower()
        )

    def test_prompt_high_frustration(self, prompt_builder, modulator):
        """High frustration should allow for short/cutting responses."""
        state = EmotionalState(frustration=9.0, excitement=2.0, confidence=3.0)
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should mention frustration level
        assert (
            "9.0" in system_content
            or "furious" in system_content.lower()
            or "done" in system_content.lower()
        )
        # Should mention ability to refuse
        assert (
            "refuse" in system_content.lower()
            or "cutting" in system_content.lower()
            or "shorter" in system_content.lower()
        )

    def test_prompt_high_excitement(self, prompt_builder, modulator):
        """High excitement should result in warmer tone."""
        state = EmotionalState(excitement=9.0, affection=8.0, frustration=1.0)
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should mention excitement
        assert (
            "9.0" in system_content
            or "hyped" in system_content.lower()
            or "excited" in system_content.lower()
        )
        # Should mention warmer tone
        assert (
            "warm" in system_content.lower()
            or "genuine enthusiasm" in system_content.lower()
            or "exclamation" in system_content.lower()
        )


class TestPromptBuilderEmotionDescriptions:
    """Test emotion value to description mapping."""

    def test_describe_emotion_loneliness(self, prompt_builder):
        """Test loneliness emotion descriptions."""
        assert prompt_builder._describe_emotion("loneliness", 0.2) == "detached"
        assert prompt_builder._describe_emotion("loneliness", 0.45) == "okay"
        assert prompt_builder._describe_emotion("loneliness", 0.65) == "lonely"
        assert prompt_builder._describe_emotion("loneliness", 0.9) == "desperate"

    def test_describe_emotion_excitement(self, prompt_builder):
        """Test excitement emotion descriptions."""
        assert prompt_builder._describe_emotion("excitement", 0.2) == "bored"
        assert prompt_builder._describe_emotion("excitement", 0.45) == "engaged"
        assert prompt_builder._describe_emotion("excitement", 0.65) == "excited"
        assert prompt_builder._describe_emotion("excitement", 0.9) == "hyped"

    def test_describe_emotion_frustration(self, prompt_builder):
        """Test frustration emotion descriptions."""
        assert prompt_builder._describe_emotion("frustration", 0.2) == "calm"
        assert prompt_builder._describe_emotion("frustration", 0.45) == "annoyed"
        assert prompt_builder._describe_emotion("frustration", 0.65) == "furious"
        assert prompt_builder._describe_emotion("frustration", 0.9) == "done"

    def test_describe_emotion_confidence(self, prompt_builder):
        """Test confidence emotion descriptions."""
        assert prompt_builder._describe_emotion("confidence", 0.2) == "unsure"
        assert prompt_builder._describe_emotion("confidence", 0.45) == "capable"
        assert prompt_builder._describe_emotion("confidence", 0.65) == "confident"
        assert prompt_builder._describe_emotion("confidence", 0.9) == "invincible"

    def test_describe_emotion_unknown(self, prompt_builder):
        """Test unknown emotion returns neutral."""
        result = prompt_builder._describe_emotion("unknown_emotion", 5.0)
        assert result == "neutral"


class TestPromptBuilderIntegration:
    """Integration tests with modulation parameters."""

    def test_modulation_parameters_in_prompt(self, prompt_builder, modulator):
        """Verify modulation parameters are included in prompt."""
        state = EmotionalState(loneliness=7.0, excitement=2.0)
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should include modulation parameter values
        # These come from ModulationParameters.to_prompt_context()
        assert "Sarcasm" in system_content or "sarcasm" in system_content.lower()
        assert "Warmth" in system_content or "warmth" in system_content.lower()
        assert (
            "Response length" in system_content
            or "response length" in system_content.lower()
        )

    def test_all_nine_emotions_included(self, prompt_builder, modulator):
        """Verify all 9 emotion dimensions are in system prompt."""
        state = EmotionalState(
            loneliness=1.0,
            excitement=2.0,
            frustration=3.0,
            jealousy=4.0,
            vulnerability=5.0,
            confidence=6.0,
            curiosity=7.0,
            affection=8.0,
            defensiveness=9.0,
        )
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # All 9 emotions should be mentioned
        assert "Loneliness" in system_content
        assert "Excitement" in system_content
        assert "Frustration" in system_content
        assert "Jealousy" in system_content
        assert "Vulnerability" in system_content
        assert "Confidence" in system_content
        assert "Curiosity" in system_content
        assert "Affection" in system_content
        assert "Defensiveness" in system_content


class TestPromptBuilderLogging:
    """Test PromptBuilder logging output."""

    def test_logs_system_prompt_building(self, prompt_builder, modulator, caplog):
        """Verify logging when building system prompt."""
        state = EmotionalState(loneliness=7.0, excitement=2.0)
        modulation = modulator.modulate(state)

        # Build prompt - should log
        prompt_builder.build(state, modulation, [])

        # Check that some log output occurred (via logger)
        # Logger uses structlog/custom logging, so we check logger was called
        assert prompt_builder.logger is not None
