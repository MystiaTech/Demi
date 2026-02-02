"""
Unit tests for ConversationHistory and Message.

Validates message storage, trimming, and token-aware context management.
"""

import pytest
from src.llm.history_manager import ConversationHistory, Message
from src.emotion.models import EmotionalState
from src.core.logger import DemiLogger


@pytest.fixture
def logger():
    """Create a test logger."""
    return DemiLogger()


@pytest.fixture
def token_counter():
    """Token counter for testing (1 token ≈ 4 chars)."""
    return lambda text: max(1, len(text) // 4)


@pytest.fixture
def history(logger):
    """Create a ConversationHistory instance."""
    return ConversationHistory(max_context_tokens=1000, logger=logger)


class TestMessageDataclass:
    """Test Message dataclass."""

    def test_message_creation(self):
        """Create a basic message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None
        assert msg.emotional_context is None

    def test_message_with_emotional_context(self):
        """Create message with emotional context."""
        state = EmotionalState(excitement=0.8)
        msg = Message(role="user", content="Hello", emotional_context=state)
        assert msg.emotional_context is not None
        assert msg.emotional_context.excitement == 0.8


class TestConversationHistoryBasics:
    """Test basic ConversationHistory functionality."""

    def test_history_initialization(self, history):
        """Verify history initializes with empty messages."""
        assert history.max_context_tokens == 1000
        assert len(history.messages) == 0

    def test_add_single_message(self, history):
        """Add a single message to history."""
        msg = history.add_message("user", "Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert len(history.messages) == 1

    def test_add_multiple_messages(self, history):
        """Add multiple messages."""
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi there!")
        history.add_message("user", "How are you?")
        assert len(history.messages) == 3

    def test_add_message_with_emotional_context(self, history):
        """Add message with emotional state."""
        state = EmotionalState(loneliness=7.0)
        msg = history.add_message("user", "Hello", emotional_context=state)
        assert msg.emotional_context is not None
        assert len(history.messages) == 1

    def test_messages_property_returns_copy(self, history):
        """Messages property returns copy not reference."""
        history.add_message("user", "Hello")
        messages1 = history.messages
        messages2 = history.messages
        assert messages1 is not messages2  # Different objects
        assert len(messages1) == len(messages2)

    def test_clear_history(self, history):
        """Clear all messages."""
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi!")
        assert len(history.messages) == 2

        history.clear()
        assert len(history.messages) == 0


class TestConversationHistoryTrimming:
    """Test message trimming with context limits."""

    def test_trim_keeps_all_when_under_limit(self, history, token_counter):
        """Don't trim if messages fit within limit."""
        history.add_message("user", "Short")
        history.add_message("assistant", "OK")
        history.add_message("user", "Brief")

        # Trim with generous limit
        trimmed = history.trim_for_inference(
            system_prompt_tokens=100, token_counter=token_counter
        )
        assert len(trimmed) == 3

    def test_trim_removes_oldest_messages(self, history, token_counter):
        """Trimming removes oldest messages first."""
        # Add messages with specific patterns
        history.add_message("user", "A" * 400)  # ~100 tokens
        history.add_message("assistant", "B" * 400)  # ~100 tokens
        history.add_message("user", "Current question?")  # ~5 tokens

        # Trim with tight limit
        trimmed = history.trim_for_inference(
            system_prompt_tokens=500,
            max_response_tokens=256,
            token_counter=token_counter,
        )

        # Should have removed oldest messages
        assert len(trimmed) < 3
        # But last user message should be present
        assert trimmed[-1]["role"] == "user"
        assert "Current question?" in trimmed[-1]["content"]

    def test_trim_preserves_last_user_message(self, history, token_counter):
        """Last user message should never be removed."""
        # Add many old assistant messages
        for i in range(5):
            history.add_message("user", f"Q{i}")
            history.add_message("assistant", "Long response " + ("X" * 400))

        # Add final user message
        final_msg = "What is this?"
        history.add_message("user", final_msg)

        # Trim with low limit
        trimmed = history.trim_for_inference(
            system_prompt_tokens=800,
            max_response_tokens=256,
            token_counter=token_counter,
        )

        # Last message should be the final user message
        assert trimmed[-1]["role"] == "user"
        assert final_msg in trimmed[-1]["content"]

    def test_trim_returns_dicts_not_message_objects(self, history, token_counter):
        """Trimmed output should be dicts, not Message objects."""
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi")

        trimmed = history.trim_for_inference(
            system_prompt_tokens=100, token_counter=token_counter
        )

        assert isinstance(trimmed, list)
        assert all(isinstance(m, dict) for m in trimmed)
        assert all("role" in m and "content" in m for m in trimmed)

    def test_trim_respects_system_prompt_tokens(self, history, token_counter):
        """Trimming accounts for system prompt size."""
        history.add_message("user", "Message 1 " * 50)  # ~62 tokens
        history.add_message("assistant", "Response 1 " * 50)  # ~62 tokens
        history.add_message("user", "Message 2")  # ~1 token

        # With large system prompt, should trim more aggressively
        trimmed_large_system = history.trim_for_inference(
            system_prompt_tokens=800,
            max_response_tokens=256,
            token_counter=token_counter,
        )

        # With small system prompt, should keep more
        trimmed_small_system = history.trim_for_inference(
            system_prompt_tokens=100,
            max_response_tokens=256,
            token_counter=token_counter,
        )

        # Large system prompt should result in fewer messages
        assert len(trimmed_large_system) <= len(trimmed_small_system)


class TestConversationHistoryWindow:
    """Test conversation window functionality."""

    def test_get_conversation_window_default(self, history):
        """Get last 5 messages by default."""
        for i in range(10):
            history.add_message("user" if i % 2 == 0 else "assistant", f"Message {i}")

        window = history.get_conversation_window()
        assert len(window) == 5
        assert window[0].content == "Message 5"
        assert window[-1].content == "Message 9"

    def test_get_conversation_window_custom_size(self, history):
        """Get custom number of recent messages."""
        for i in range(10):
            history.add_message("user" if i % 2 == 0 else "assistant", f"Message {i}")

        window = history.get_conversation_window(num_messages=3)
        assert len(window) == 3
        assert window[0].content == "Message 7"

    def test_get_conversation_window_empty(self, history):
        """Get window from empty history."""
        window = history.get_conversation_window()
        assert window == []

    def test_get_conversation_window_fewer_than_requested(self, history):
        """Get window when fewer messages than requested."""
        history.add_message("user", "Only message")

        window = history.get_conversation_window(num_messages=5)
        assert len(window) == 1
        assert window[0].content == "Only message"


class TestConversationHistorySummarization:
    """Test conversation summarization."""

    def test_summarize_empty_history(self, history):
        """Summarize empty history."""
        summary = history.summarize()

        assert summary["total_messages"] == 0
        assert summary["total_tokens"] == 0
        assert summary["first_message_time"] is None
        assert summary["last_message_time"] is None
        assert summary["turns"] == 0

    def test_summarize_single_turn(self, history):
        """Summarize single user-assistant turn."""
        history.add_message("user", "Hello world")
        history.add_message("assistant", "Hi there!")

        summary = history.summarize()

        assert summary["total_messages"] == 2
        assert summary["total_tokens"] > 0
        assert summary["first_message_time"] is not None
        assert summary["last_message_time"] is not None
        assert summary["turns"] == 1  # One user message = one turn

    def test_summarize_multiple_turns(self, history):
        """Summarize multiple conversation turns."""
        for i in range(3):
            history.add_message("user", f"Question {i}")
            history.add_message("assistant", f"Answer {i}")

        summary = history.summarize()

        assert summary["total_messages"] == 6
        assert summary["turns"] == 3  # Three user messages

    def test_summarize_preserves_timestamps(self, history):
        """Summarize preserves first and last timestamps."""
        import time

        history.add_message("user", "First")
        first_time = history.messages[0].timestamp

        time.sleep(0.01)  # Small delay

        history.add_message("assistant", "Response")
        last_time = history.messages[-1].timestamp

        summary = history.summarize()

        assert summary["first_message_time"] == first_time
        assert summary["last_message_time"] == last_time


class TestConversationHistoryTokenEstimation:
    """Test token estimation for fallback."""

    def test_default_token_estimation(self, history):
        """Use default token estimation when none provided."""
        history.add_message("user", "Hello world")  # 11 chars
        history.add_message("assistant", "Hi there!")  # 9 chars

        trimmed = history.trim_for_inference(
            system_prompt_tokens=100  # No token_counter provided
        )

        # Should still work with default estimation
        assert len(trimmed) >= 1

    def test_token_estimation_accuracy(self):
        """Test token estimator's accuracy."""
        from src.llm.history_manager import ConversationHistory

        hist = ConversationHistory()

        # Test with various text lengths
        assert hist._estimate_tokens("") >= 1  # Minimum 1 token
        assert hist._estimate_tokens("Hello") >= 1  # ~1 token
        assert hist._estimate_tokens("Hello world test") > hist._estimate_tokens(
            "Hi"
        )  # Longer = more tokens
