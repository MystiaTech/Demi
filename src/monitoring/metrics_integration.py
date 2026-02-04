"""Integration helpers for recording metrics from various Demi components.

This module provides convenient methods to record metrics from LLM inference,
platform handlers, emotions, and Discord bot operations.
"""

import time
from contextlib import contextmanager
from typing import Optional, Dict, Any

from src.core.logger import get_logger
from src.monitoring.metrics import (
    get_metrics_collector,
    get_llm_metrics,
    get_platform_metrics,
    get_emotion_metrics,
    get_discord_metrics,
)

logger = get_logger()


class LLMInferenceMetrics:
    """Context manager for recording LLM inference metrics."""

    def __init__(self, model: str = "unknown"):
        self.model = model
        self.start_time = None
        self.prompt_tokens = 0
        self.response_tokens = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            llm_metrics = get_llm_metrics()
            llm_metrics.record_error(str(exc_type.__name__), self.model)
            return False

        if self.start_time:
            elapsed_ms = (time.time() - self.start_time) * 1000
            llm_metrics = get_llm_metrics()
            llm_metrics.record_inference(
                response_time_ms=elapsed_ms,
                tokens_generated=self.response_tokens,
                inference_latency_ms=elapsed_ms * 0.8,  # Estimate
                prompt_tokens=self.prompt_tokens,
                model=self.model,
            )

        return True

    def set_tokens(self, prompt_tokens: int, response_tokens: int):
        """Set token counts."""
        self.prompt_tokens = prompt_tokens
        self.response_tokens = response_tokens


class PlatformMessageMetrics:
    """Context manager for recording platform message metrics."""

    def __init__(self, platform: str):
        self.platform = platform
        self.start_time = None
        self.message_length = 0
        self.success = True
        self.error = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.success = False
            self.error = str(exc_type.__name__)

        if self.start_time:
            elapsed_ms = (time.time() - self.start_time) * 1000
            platform_metrics = get_platform_metrics()
            platform_metrics.record_message(
                platform=self.platform,
                response_time_ms=elapsed_ms,
                message_length=self.message_length,
                success=self.success,
                error=self.error,
            )

        return False  # Don't suppress exceptions

    def set_message_length(self, length: int):
        """Set message length."""
        self.message_length = length


@contextmanager
def track_inference(model: str = "unknown"):
    """Context manager for tracking LLM inference.

    Usage:
        with track_inference("llama2"):
            response = await llm.chat(messages)
    """
    metrics = LLMInferenceMetrics(model)
    with metrics:
        yield metrics


@contextmanager
def track_platform_message(platform: str):
    """Context manager for tracking platform messages.

    Usage:
        with track_platform_message("discord"):
            response = await send_message(...)
    """
    metrics = PlatformMessageMetrics(platform)
    with metrics:
        yield metrics


def record_emotion_state(emotions: Dict[str, float]):
    """Record current emotional state.

    Args:
        emotions: Dictionary mapping emotion names to values (0-1)
    """
    emotion_metrics = get_emotion_metrics()
    emotion_metrics.record_emotion_state(emotions)


def record_conversation_turn(
    user_message_length: int,
    bot_response_length: int,
    turn_number: int,
    sentiment_score: float = 0.5,
):
    """Record conversation metrics.

    Args:
        user_message_length: Length of user message
        bot_response_length: Length of bot response
        turn_number: Turn number in conversation
        sentiment_score: Sentiment score (0-1)
    """
    from src.monitoring.metrics import get_conversation_metrics

    conv_metrics = get_conversation_metrics()
    conv_metrics.record_conversation(
        user_message_length=user_message_length,
        bot_response_length=bot_response_length,
        conversation_turn=turn_number,
        sentiment_score=sentiment_score,
    )


def update_discord_bot_status(
    online: bool,
    latency_ms: float,
    guild_count: int,
    connected_users: int,
):
    """Update Discord bot status metrics.

    Args:
        online: Whether bot is online
        latency_ms: Bot latency in milliseconds
        guild_count: Number of connected guilds
        connected_users: Number of connected users
    """
    discord_metrics = get_discord_metrics()
    discord_metrics.record_bot_status(
        online=online,
        latency_ms=latency_ms,
        guild_count=guild_count,
        connected_users=connected_users,
    )


def record_llm_tokens(
    prompt_tokens: int,
    response_tokens: int,
    model: str = "unknown",
):
    """Record LLM token counts.

    Args:
        prompt_tokens: Number of prompt tokens
        response_tokens: Number of response tokens
        model: Model name
    """
    llm_metrics = get_llm_metrics()
    llm_metrics.record_inference(
        response_time_ms=0,  # Will be set by context manager
        tokens_generated=response_tokens,
        inference_latency_ms=0,
        prompt_tokens=prompt_tokens,
        model=model,
    )


def get_current_emotions() -> Dict[str, float]:
    """Get current emotional state.

    Returns:
        Dictionary of emotion values
    """
    emotion_metrics = get_emotion_metrics()
    return emotion_metrics.get_current_emotions()


def get_emotion_history(emotion: str, limit: int = 100):
    """Get emotion history.

    Args:
        emotion: Emotion name
        limit: Maximum points to return

    Returns:
        List of emotion data points with timestamps
    """
    emotion_metrics = get_emotion_metrics()
    return emotion_metrics.get_emotion_history(emotion, limit)


def get_platform_stats(time_range: Any = None) -> Dict[str, Any]:
    """Get platform statistics.

    Args:
        time_range: Optional timedelta for aggregation window

    Returns:
        Dictionary of platform stats
    """
    platform_metrics = get_platform_metrics()
    return platform_metrics.get_platform_stats(time_range)


def get_conversation_quality() -> Dict[str, float]:
    """Get conversation quality metrics.

    Returns:
        Dictionary of quality metrics
    """
    from src.monitoring.metrics import get_conversation_metrics

    conv_metrics = get_conversation_metrics()
    return conv_metrics.get_quality_metrics()


def get_discord_status() -> Dict[str, Any]:
    """Get Discord bot status.

    Returns:
        Dictionary of bot status metrics
    """
    discord_metrics = get_discord_metrics()
    return discord_metrics.get_bot_status()
