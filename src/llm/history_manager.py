"""
Conversation history manager for multi-turn dialogue.

Manages message history with token-aware trimming to fit within context window.
Preserves conversation continuity while respecting LLM context limits.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional, Dict
from src.emotion.models import EmotionalState
from src.core.logger import DemiLogger


@dataclass
class Message:
    """Single message in conversation history."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    emotional_context: Optional[EmotionalState] = None  # For logging/analysis


class ConversationHistory:
    """
    Manages conversation history with token-aware trimming.

    Stores messages and trims oldest messages to fit within context window while
    preserving the current turn's user message.
    """

    def __init__(self, max_context_tokens: int = 8000, logger: DemiLogger = None):
        """
        Initialize ConversationHistory.

        Args:
            max_context_tokens: Maximum tokens allowed in context (default 8000)
            logger: Optional DemiLogger for logging
        """
        self.max_context_tokens = max_context_tokens
        self.logger = logger
        self._messages: List[Message] = []

    @property
    def messages(self) -> List[Message]:
        """Get current message list."""
        return self._messages.copy()

    def add_message(
        self,
        role: str,
        content: str,
        emotional_context: Optional[EmotionalState] = None,
    ) -> Message:
        """
        Add message to history.

        Args:
            role: "user", "assistant", or "system"
            content: Message text
            emotional_context: Optional emotional state for context

        Returns:
            The created Message object
        """
        message = Message(
            role=role, content=content, emotional_context=emotional_context
        )
        self._messages.append(message)

        if self.logger:
            self.logger.debug(
                f"Added {role} message ({len(content)} chars): {content[:50]}..."
            )

        return message

    def trim_for_inference(
        self,
        system_prompt_tokens: int,
        max_response_tokens: int = 256,
        token_counter: Callable[[str], int] = None,
    ) -> List[Dict[str, str]]:
        """
        Trim message history to fit within context window.

        Removes oldest messages while preserving last user message and conversation flow.

        Args:
            system_prompt_tokens: Token count of system prompt
            max_response_tokens: Tokens reserved for response generation
            token_counter: Function to count tokens in text

        Returns:
            List of message dicts ready for inference: [{"role": "...", "content": "..."}, ...]
        """
        # If no token counter provided, use simple estimation
        if token_counter is None:
            token_counter = self._estimate_tokens

        # Calculate available context for history
        safety_buffer = 256  # Extra safety margin
        available_tokens = (
            self.max_context_tokens
            - system_prompt_tokens
            - max_response_tokens
            - safety_buffer
        )

        # Convert messages to dicts for processing
        message_dicts = [
            {"role": msg.role, "content": msg.content} for msg in self._messages
        ]

        # Calculate total tokens
        total_tokens = sum(token_counter(msg["content"]) for msg in message_dicts)

        # If under limit, return all
        if total_tokens <= available_tokens:
            return message_dicts

        # Otherwise, trim from start, preserving last user message
        trimmed_messages = []
        current_tokens = 0
        last_user_message_idx = None

        # Find last user message index
        for i in range(len(message_dicts) - 1, -1, -1):
            if message_dicts[i]["role"] == "user":
                last_user_message_idx = i
                break

        # Build trimmed list starting from end
        for i in range(len(message_dicts) - 1, -1, -1):
            msg = message_dicts[i]
            msg_tokens = token_counter(msg["content"])

            # Always keep last user message
            if i == last_user_message_idx:
                trimmed_messages.insert(0, msg)
                current_tokens += msg_tokens
            elif current_tokens + msg_tokens <= available_tokens:
                trimmed_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # Stop adding when we exceed limit
                break

        if self.logger:
            before_count = len(self._messages)
            after_count = len(trimmed_messages)
            self.logger.debug(
                f"Trimmed history from {before_count} to {after_count} messages "
                f"({total_tokens} → {current_tokens} tokens)"
            )

        return trimmed_messages

    def get_conversation_window(self, num_messages: int = 5) -> List[Message]:
        """
        Get last N messages for display/debugging.

        Args:
            num_messages: Number of recent messages to return (default 5)

        Returns:
            List of most recent messages
        """
        return self._messages[-num_messages:] if self._messages else []

    def clear(self) -> None:
        """Clear all conversation history."""
        self._messages.clear()
        if self.logger:
            self.logger.debug("Cleared conversation history")

    def summarize(self) -> Dict[str, any]:
        """
        Summarize conversation statistics.

        Returns:
            Dict with total_messages, total_tokens, first/last message times, turn count
        """
        if not self._messages:
            return {
                "total_messages": 0,
                "total_tokens": 0,
                "first_message_time": None,
                "last_message_time": None,
                "turns": 0,
            }

        total_tokens = sum(len(msg.content.split()) * 1.3 for msg in self._messages)
        user_messages = [msg for msg in self._messages if msg.role == "user"]

        return {
            "total_messages": len(self._messages),
            "total_tokens": int(total_tokens),
            "first_message_time": self._messages[0].timestamp,
            "last_message_time": self._messages[-1].timestamp,
            "turns": len(user_messages),
        }

    def _estimate_tokens(self, text: str) -> int:
        """
        Simple token estimation (fallback if token_counter not provided).

        Uses rule of thumb: ~4 characters per token on average.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)
