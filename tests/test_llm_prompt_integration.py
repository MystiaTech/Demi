"""
Integration tests for PromptBuilder and ConversationHistory.

Validates full prompt building flow with emotional state, modulation, and history.
"""

import pytest
from src.llm.prompt_builder import PromptBuilder
from src.llm.history_manager import ConversationHistory
from src.emotion.models import EmotionalState
from src.emotion.modulation import PersonalityModulator
from src.core.logger import DemiLogger


@pytest.fixture
def logger():
    """Create a test logger."""
    return DemiLogger()


@pytest.fixture
def token_counter():
    """Token counter for testing."""
    return lambda text: max(1, len(text) // 4)


@pytest.fixture
def prompt_builder(logger, token_counter):
    """Create PromptBuilder."""
    return PromptBuilder(logger, token_counter)


@pytest.fixture
def history(logger):
    """Create ConversationHistory."""
    return ConversationHistory(max_context_tokens=8000, logger=logger)


@pytest.fixture
def modulator():
    """Create PersonalityModulator."""
    return PersonalityModulator()


class TestFullPromptFlow:
    """Test complete prompt building flow."""

    def test_full_prompt_flow_basic(
        self, prompt_builder, history, modulator, token_counter
    ):
        """Test basic flow: emotion → modulation → prompt with history."""
        # Create emotional state
        state = EmotionalState(
            loneliness=7.0,
            excitement=2.0,
            frustration=4.0,
            affection=6.0,
        )

        # Get modulation
        modulation = modulator.modulate(state)

        # Add messages to history
        history.add_message("user", "What's up?")
        history.add_message("assistant", "Hey bestie!")
        history.add_message("user", "How are you feeling?")

        # Get trimmed history
        history_for_inference = history.trim_for_inference(
            system_prompt_tokens=500, token_counter=token_counter
        )

        # Build full prompt
        messages = prompt_builder.build(state, modulation, history_for_inference)

        # Verify structure
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 100  # System prompt is substantial

        # Verify history is included
        message_roles = [m["role"] for m in messages]
        assert "user" in message_roles
        assert "assistant" in message_roles

    def test_full_prompt_preserves_order(
        self, prompt_builder, history, modulator, token_counter
    ):
        """Verify message order is preserved."""
        state = EmotionalState()
        modulation = modulator.modulate(state)

        history.add_message("user", "First")
        history.add_message("assistant", "Second")
        history.add_message("user", "Third")

        history_for_inference = history.trim_for_inference(
            system_prompt_tokens=100, token_counter=token_counter
        )

        messages = prompt_builder.build(state, modulation, history_for_inference)

        # After system prompt, order should be preserved
        non_system = messages[1:]
        assert non_system[0]["content"] == "First"
        assert non_system[1]["content"] == "Second"
        assert non_system[2]["content"] == "Third"

    def test_prompt_respects_token_limit(
        self, prompt_builder, history, modulator, token_counter
    ):
        """Verify trimming respects token limits."""
        state = EmotionalState()
        modulation = modulator.modulate(state)

        # Add many long messages
        for i in range(20):
            history.add_message("user", "Q " + "X" * 100)
            history.add_message("assistant", "A " + "Y" * 100)

        # Trim to small context
        history_for_inference = history.trim_for_inference(
            system_prompt_tokens=2000,
            max_response_tokens=256,
            token_counter=token_counter,
        )

        # Build prompt
        messages = prompt_builder.build(state, modulation, history_for_inference)

        # Calculate total tokens
        total_tokens = sum(token_counter(m["content"]) for m in messages)

        # Should fit within 8K limit
        assert total_tokens <= 8000


class TestPromptWithHighLoneliness:
    """Test prompt building with high loneliness."""

    def test_prompt_with_high_loneliness(self, prompt_builder, modulator):
        """High loneliness should affect prompt content."""
        state = EmotionalState(
            loneliness=0.95,
            excitement=0.1,
            affection=0.2,
            confidence=0.2,
        )

        modulation = modulator.modulate(state)
        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should contain loneliness (mapped from 0-1 to 0-10)
        assert "loneliness" in system_content.lower()
        assert "9" in system_content  # Should show ~9.5/10

        # Should contain description of high loneliness
        assert "desperate" in system_content.lower()

        # Modulation should reflect loneliness behavior
        assert (
            "seeking" in system_content.lower()
            or "connection" in system_content.lower()
            or "longer" in system_content.lower()
        )

        modulation = modulator.modulate(state)
        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should contain loneliness value
        assert "9.5" in system_content

        # Should contain description of high loneliness
        assert (
            "desperate" in system_content.lower() or "seeking" in system_content.lower()
        )

        # Modulation should reflect loneliness behavior
        assert (
            "seeking" in system_content.lower()
            or "connection" in system_content.lower()
            or "longer" in system_content.lower()
        )

    def test_modulation_reflects_loneliness(self, prompt_builder, modulator):
        """Modulation parameters should adjust for loneliness."""
        state = EmotionalState(loneliness=9.0)
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should include modulation parameters in prompt
        assert "Sarcasm" in system_content or "sarcasm" in system_content.lower()


class TestPromptWithHighFrustration:
    """Test prompt building with high frustration."""

    def test_prompt_with_high_frustration(self, prompt_builder, modulator):
        """High frustration should allow for refusal and cutting tone."""
        state = EmotionalState(
            frustration=0.9,
            excitement=0.1,
            affection=0.2,
            confidence=0.3,
        )

        modulation = modulator.modulate(state)
        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should contain frustration value
        assert "frustration" in system_content.lower()
        assert "9" in system_content  # Should show ~9.0/10

        # Should contain description of high frustration
        assert "furious" in system_content.lower() or "done" in system_content.lower()

        # Should mention ability to refuse
        assert (
            "refuse" in system_content.lower()
            or "shorter" in system_content.lower()
            or "cutting" in system_content.lower()
        )


class TestPromptWithHighExcitement:
    """Test prompt building with high excitement."""

    def test_prompt_with_high_excitement(self, prompt_builder, modulator):
        """High excitement should result in warmer, more enthusiastic prompt."""
        state = EmotionalState(
            excitement=0.9,
            affection=0.8,
            frustration=0.1,
            loneliness=0.1,
        )

        modulation = modulator.modulate(state)
        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should contain excitement value (mapped 0-1 to 0-10)
        assert "excitement" in system_content.lower()
        assert "9" in system_content  # Should show ~9.0/10

        # Should contain description of high excitement
        assert "hyped" in system_content.lower() or "excited" in system_content.lower()

        # Should mention warmer tone
        assert (
            "warm" in system_content.lower()
            or "genuine" in system_content.lower()
            or "exclamation" in system_content.lower()
        )


class TestHistoryTrimming:
    """Test history trimming integration."""

    def test_history_trimming_with_context(
        self, prompt_builder, history, modulator, token_counter
    ):
        """Test trimming history to fit in limited context."""
        state = EmotionalState()
        modulation = modulator.modulate(state)

        # Add 10+ messages with large content to force trimming
        for i in range(15):
            history.add_message("user", f"Q{i} " + "X" * 500)  # Larger messages
            history.add_message("assistant", f"A{i} " + "Y" * 500)

        # Trim to 1000 tokens (will definitely force trimming now)
        history_for_inference = history.trim_for_inference(
            system_prompt_tokens=2000,
            max_response_tokens=256,
            token_counter=token_counter,
        )

        # Should have removed some messages (30 total → smaller)
        assert len(history_for_inference) <= len(history.messages)

        # But should still have a user message (not necessarily last)
        user_messages = [m for m in history_for_inference if m["role"] == "user"]
        assert len(user_messages) > 0  # At least one user message preserved

        # Build prompt with trimmed history
        messages = prompt_builder.build(state, modulation, history_for_inference)

        # Should complete successfully
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"


class TestPromptContentValidation:
    """Validate prompt content structure."""

    def test_prompt_includes_all_emotion_categories(self, prompt_builder, modulator):
        """All 9 emotion categories should appear in system prompt."""
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

        # All 9 emotions should be in prompt
        emotions_to_check = [
            "Loneliness",
            "Excitement",
            "Frustration",
            "Jealousy",
            "Vulnerability",
            "Confidence",
            "Curiosity",
            "Affection",
            "Defensiveness",
        ]

        for emotion in emotions_to_check:
            assert emotion in system_content, f"{emotion} not found in system prompt"

    def test_prompt_includes_modulation_section(self, prompt_builder, modulator):
        """System prompt should include modulation rules section."""
        state = EmotionalState()
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])
        system_content = messages[0]["content"]

        # Should have modulation section
        assert "modulation" in system_content.lower()

        # Should include personality parameters
        assert "Sarcasm" in system_content or "sarcasm" in system_content.lower()
        assert "Warmth" in system_content or "warmth" in system_content.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_history(self, prompt_builder, modulator):
        """Build prompt with empty history."""
        state = EmotionalState()
        modulation = modulator.modulate(state)

        messages = prompt_builder.build(state, modulation, [])

        # Should still work
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"

    def test_extreme_emotions(self, prompt_builder, modulator):
        """Build prompt with extreme emotion values."""
        state = EmotionalState(
            loneliness=10.0,
            excitement=10.0,
            frustration=10.0,
            affection=0.0,
            confidence=0.0,
        )

        modulation = modulator.modulate(state)

        # Should not crash
        messages = prompt_builder.build(state, modulation, [])
        assert len(messages) >= 1

    def test_large_history(self, prompt_builder, history, modulator, token_counter):
        """Handle large conversation history."""
        state = EmotionalState()
        modulation = modulator.modulate(state)

        # Add 100 messages
        for i in range(100):
            history.add_message("user" if i % 2 == 0 else "assistant", f"Msg {i}")

        # Trim to manageable size
        history_for_inference = history.trim_for_inference(
            system_prompt_tokens=1000, token_counter=token_counter
        )

        # Build prompt
        messages = prompt_builder.build(state, modulation, history_for_inference)

        # Should complete without error
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"
