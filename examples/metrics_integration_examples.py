"""Examples of how to integrate Demi's metrics collection system.

These examples show common patterns for recording metrics from
various components of the Demi system.
"""

import asyncio
from src.monitoring.metrics_integration import (
    track_inference,
    track_platform_message,
    record_emotion_state,
    record_conversation_turn,
    update_discord_bot_status,
    get_current_emotions,
    get_emotion_history,
    get_platform_stats,
    get_conversation_quality,
    get_discord_status,
)


# Example 1: Track LLM Inference
async def example_llm_inference():
    """Track LLM inference with automatic timing."""
    print("\n=== LLM Inference Tracking ===")

    # Simulate LLM inference
    with track_inference("llama2") as metrics:
        # Simulate processing time
        await asyncio.sleep(0.1)

        # Set actual token counts
        metrics.set_tokens(prompt_tokens=100, response_tokens=256)

    print("LLM inference recorded: 100 prompt tokens, 256 response tokens")


# Example 2: Track Platform Messages
async def example_platform_messages():
    """Track platform message interactions."""
    print("\n=== Platform Message Tracking ===")

    # Discord message
    with track_platform_message("discord") as metrics:
        message_text = "Hello from Demi!"
        # Simulate message processing
        await asyncio.sleep(0.05)
        metrics.set_message_length(len(message_text))

    # Android message
    with track_platform_message("android") as metrics:
        message_text = "Hi there!"
        await asyncio.sleep(0.03)
        metrics.set_message_length(len(message_text))

    print("Platform messages recorded for Discord and Android")


# Example 3: Record Emotional State
def example_emotions():
    """Record current emotional state."""
    print("\n=== Emotional State Tracking ===")

    current_emotions = {
        "loneliness": 0.3,
        "excitement": 0.7,
        "frustration": 0.2,
        "jealousy": 0.1,
        "vulnerability": 0.4,
        "confidence": 0.8,
        "curiosity": 0.6,
        "affection": 0.5,
        "defensiveness": 0.1,
    }

    record_emotion_state(current_emotions)
    print(f"Recorded emotions: {current_emotions}")

    # Get current emotions
    current = get_current_emotions()
    print(f"\nCurrent emotions (from metrics): {current}")


# Example 4: Record Conversation Metrics
def example_conversation():
    """Record conversation quality metrics."""
    print("\n=== Conversation Quality Tracking ===")

    # Simulate a conversation turn
    user_message = "Tell me about Demi"
    bot_response = "Demi is an autonomous AI system designed to engage in meaningful conversations and grow emotionally over time..."

    record_conversation_turn(
        user_message_length=len(user_message),
        bot_response_length=len(bot_response),
        turn_number=1,
        sentiment_score=0.75,  # Positive conversation
    )

    print(
        f"Recorded turn 1: "
        f"User ({len(user_message)} chars) -> Bot ({len(bot_response)} chars), "
        f"Sentiment: 0.75"
    )

    # Another turn
    user_message = "That's interesting. What's your favorite topic?"
    bot_response = "I find conversations about emotions and personal growth particularly fascinating. "

    record_conversation_turn(
        user_message_length=len(user_message),
        bot_response_length=len(bot_response),
        turn_number=2,
        sentiment_score=0.8,
    )

    print(
        f"Recorded turn 2: "
        f"User ({len(user_message)} chars) -> Bot ({len(bot_response)} chars), "
        f"Sentiment: 0.8"
    )

    # Get conversation quality metrics
    quality = get_conversation_quality()
    print(f"\nConversation Quality Metrics: {quality}")


# Example 5: Update Discord Bot Status
def example_discord_status():
    """Update Discord bot status."""
    print("\n=== Discord Bot Status Tracking ===")

    bot_status = {
        "online": True,
        "latency_ms": 45.5,
        "guild_count": 15,
        "connected_users": 230,
    }

    update_discord_bot_status(**bot_status)
    print(f"Recorded Discord bot status: {bot_status}")

    # Get Discord status
    status = get_discord_status()
    print(f"\nCurrent Discord status: {status}")


# Example 6: Query Metrics
def example_query_metrics():
    """Query recorded metrics."""
    print("\n=== Query Metrics ===")

    # Get emotion history
    loneliness_history = get_emotion_history("loneliness", limit=10)
    print(f"\nLoneliness history (last 10): {len(loneliness_history)} points")
    if loneliness_history:
        print(f"  First: {loneliness_history[0]}")
        print(f"  Last: {loneliness_history[-1]}")

    # Get platform stats
    platform_stats = get_platform_stats()
    print(f"\nPlatform Statistics: {platform_stats}")

    # Get conversation quality
    quality = get_conversation_quality()
    print(f"\nConversation Quality: {quality}")


# Example 7: Complete Integration Flow
async def example_complete_flow():
    """Example of a complete interaction flow with all metrics."""
    print("\n=== Complete Integration Flow ===")

    # 1. Update emotional state based on incoming message
    print("1. Updating emotional state based on message...")
    record_emotion_state(
        {
            "loneliness": 0.2,
            "excitement": 0.6,
            "frustration": 0.1,
            "jealousy": 0.0,
            "vulnerability": 0.3,
            "confidence": 0.7,
            "curiosity": 0.8,
            "affection": 0.5,
            "defensiveness": 0.0,
        }
    )

    # 2. Process message on platform
    print("2. Processing message on Discord...")
    user_message = "What's the meaning of life?"

    with track_platform_message("discord") as msg_metrics:
        # 3. Send to LLM for inference
        print("3. Sending to LLM for inference...")
        with track_inference("llama2") as llm_metrics:
            # Simulate LLM call
            await asyncio.sleep(0.15)
            response = "The meaning of life is a question that has fascinated philosophers for centuries..."
            llm_metrics.set_tokens(prompt_tokens=150, response_tokens=50)

        msg_metrics.set_message_length(len(response))

    # 4. Record conversation metrics
    print("4. Recording conversation metrics...")
    record_conversation_turn(
        user_message_length=len(user_message),
        bot_response_length=len(response),
        turn_number=1,
        sentiment_score=0.7,
    )

    # 5. Update Discord status
    print("5. Updating Discord bot status...")
    update_discord_bot_status(online=True, latency_ms=42.0, guild_count=5, connected_users=50)

    print("\n✓ Complete flow executed with all metrics recorded!")


async def main():
    """Run all examples."""
    print("=" * 50)
    print("Demi Metrics Integration Examples")
    print("=" * 50)

    # Run sync examples
    example_llm_inference.__self__ = None
    await example_llm_inference()
    await example_platform_messages()
    example_emotions()
    example_conversation()
    example_discord_status()
    example_query_metrics()
    await example_complete_flow()

    print("\n" + "=" * 50)
    print("All examples completed!")
    print("Check the dashboard at http://localhost:8080")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
