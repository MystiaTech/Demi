"""Telegram-specific message formatting utilities.

Handles MarkdownV2 escaping, emotion displays, inline keyboards, and visual formatting.
"""

from typing import Dict, Optional, List, Tuple
import re


# Emotion to emoji mapping
EMOTION_EMOJIS = {
    "loneliness": "💔",
    "excitement": "✨",
    "frustration": "😤",
    "affection": "💕",
    "confidence": "💪",
    "curiosity": "🧠",
    "jealousy": "😠",
    "vulnerability": "🥺",
    "defensiveness": "🛡️",
}


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 format.

    MarkdownV2 requires escaping: _ * [ ] ( ) ~ ` > # + - = | { } . !

    Args:
        text: Raw text to escape

    Returns:
        Text safe for MarkdownV2 formatting
    """
    # Characters that need escaping in MarkdownV2
    special_chars = r"_*[]()~`>#+-=|{}.!"

    # Escape each special character
    for char in special_chars:
        text = text.replace(char, f"\\{char}")

    return text


def format_telegram_response(
    response_dict: Dict, user_name: str = "User"
) -> str:
    """Format LLM response as MarkdownV2 Telegram message with emotion context.

    Args:
        response_dict: Response from conductor with keys:
            - "content": str (the message text)
            - "emotion_state": Dict (emotional state before response)
            - "message_id": str (optional)
        user_name: Name of user who sent message

    Returns:
        MarkdownV2-formatted message string
    """
    content = response_dict.get("content", "Error generating response")
    emotion_state = response_dict.get("emotion_state", {})

    # Get dominant emotion for footer
    dominant_emotion = get_dominant_emotion(emotion_state)
    emotion_emoji = EMOTION_EMOJIS.get(dominant_emotion, "💭")

    # Escape content for MarkdownV2
    escaped_content = escape_markdown_v2(content)

    # Build message with emotion footer
    message = f"{escaped_content}\n\n_{emotion_emoji} {dominant_emotion.replace('_', ' ').title()}_"

    return message


def get_dominant_emotion(emotion_state: Optional[Dict[str, float]]) -> str:
    """Get the dominant emotion from emotional state.

    Args:
        emotion_state: Dict like {"loneliness": 0.5, "excitement": 0.8, ...}

    Returns:
        Name of dominant emotion (or "neutral" if none)
    """
    if not emotion_state:
        return "neutral"

    max_emotion = max(emotion_state.items(), key=lambda x: x[1])
    return max_emotion[0]


def create_emotion_keyboard() -> List[List[Dict]]:
    """Create inline keyboard with emotion buttons.

    Returns:
        List of button rows for InlineKeyboardMarkup
    """
    emotions = [
        "loneliness",
        "excitement",
        "frustration",
        "affection",
        "confidence",
        "curiosity",
        "jealousy",
        "vulnerability",
        "defensiveness",
    ]

    # Create 2 buttons per row
    keyboard = []
    for i in range(0, len(emotions), 2):
        row = []
        for j in range(2):
            if i + j < len(emotions):
                emotion = emotions[i + j]
                emoji = EMOTION_EMOJIS.get(emotion, "❓")
                row.append(
                    {
                        "text": f"{emoji} {emotion.replace('_', ' ').title()}",
                        "callback_data": f"emotion_detail_{emotion}",
                    }
                )
        keyboard.append(row)

    # Add refresh button
    keyboard.append([{"text": "🔄 Refresh", "callback_data": "refresh_emotions"}])

    return keyboard


def format_emotion_display(emotion_state: Optional[Dict[str, float]]) -> str:
    """Format emotion state for display with visual bars.

    Args:
        emotion_state: Dict of emotion values (0.0-10.0)

    Returns:
        MarkdownV2-formatted emotion display
    """
    if not emotion_state:
        return "*No emotional data available*"

    # Create emotional state visualization
    lines = []
    lines.append("*Emotional State:*\n")

    for emotion, value in sorted(emotion_state.items(), key=lambda x: x[1], reverse=True):
        if value > 0:  # Only show non-zero emotions
            emoji = EMOTION_EMOJIS.get(emotion, "❓")
            # Create visual bar (0-10 scale)
            filled = int(value)
            empty = 10 - filled
            bar = "▓" * filled + "░" * empty
            escaped_emotion = emotion.replace("_", " ").title()
            lines.append(
                f"{emoji} {escaped_emotion}: {bar} {value:.1f}/10"
            )

    if not any(v > 0 for v in emotion_state.values()):
        return "*Emotionally balanced*"

    return "\n".join(lines)


def format_emotion_detail(
    emotion_name: str, emotion_state: Optional[Dict[str, float]]
) -> str:
    """Format detailed view of a specific emotion.

    Args:
        emotion_name: Name of emotion to show details for
        emotion_state: Full emotional state dict

    Returns:
        MarkdownV2-formatted detail message
    """
    if not emotion_state or emotion_name not in emotion_state:
        return f"*No data available for {emotion_name}*"

    value = emotion_state[emotion_name]
    emoji = EMOTION_EMOJIS.get(emotion_name, "❓")
    escaped_name = emotion_name.replace("_", " ").title()

    # Determine emotional intensity interpretation
    if value < 2:
        intensity = "Very Low"
    elif value < 4:
        intensity = "Low"
    elif value < 6:
        intensity = "Moderate"
    elif value < 8:
        intensity = "High"
    else:
        intensity = "Very High"

    # Create bar visualization
    filled = int(value)
    empty = 10 - filled
    bar = "▓" * filled + "░" * empty

    message = (
        f"{emoji} *{escaped_name}*\n\n"
        f"Level: {bar} {value:.1f}/10\n"
        f"Intensity: _{intensity}_"
    )

    return message


def format_status_message(conductor_health: Dict, bot_status: str) -> str:
    """Format system status message.

    Args:
        conductor_health: Health status from conductor
        bot_status: Bot connectivity status

    Returns:
        MarkdownV2-formatted status message
    """
    conductor_status = conductor_health.get("status", "unknown")
    last_inference = conductor_health.get("last_inference_time", "N/A")

    message = (
        f"*System Status*\n\n"
        f"🤖 Bot: _{bot_status}_\n"
        f"⚙️ Conductor: _{conductor_status}_\n"
        f"⏱️ Last Response: _{last_inference}_"
    )

    return message


def format_help_message() -> str:
    """Format help message with available commands.

    Returns:
        MarkdownV2-formatted help message
    """
    return (
        "*Available Commands*\n\n"
        "`/start` \\- Welcome and introduction\n"
        "`/help` \\- Show this help message\n"
        "`/emotions` \\- Display current emotional state\n"
        "`/status` \\- Show system status\n"
        "`/ramble` \\- Generate a spontaneous thought\n\n"
        "*How to interact:*\n"
        "Send any message and I'll respond\\. You can mention me in groups "
        "or reply to my messages\\.\n\n"
        "*Features:*\n"
        "• Emotional awareness across all interactions\n"
        "• Personality\\-driven responses\n"
        "• Spontaneous thoughts and rambles\n"
        "• Real\\-time emotion tracking"
    )


def format_start_message() -> str:
    """Format welcome/start message.

    Returns:
        MarkdownV2-formatted welcome message
    """
    return (
        "👋 *Hello\\!* I'm *Demi*, an AI companion with emotions and personality\\.\n\n"
        "I can:\n"
        "• Have meaningful conversations\n"
        "• Express genuine emotions\n"
        "• Remember our interactions\n"
        "• Share spontaneous thoughts\n\n"
        "Use `/help` to see available commands or just send me a message\\!"
    )


def should_generate_telegram_ramble(
    emotion_state: Optional[Dict[str, float]],
    last_ramble_time: Optional[object] = None,
    min_interval_minutes: int = 60,
) -> Tuple[bool, Optional[str]]:
    """Decide if Demi should post a ramble on Telegram.

    Rules:
    - Loneliness > 0.7 → ramble (missing interaction)
    - Excitement > 0.8 → ramble (feeling social)
    - Frustration > 0.6 → ramble (venting)
    - Don't ramble more than every 60 minutes (prevents spam)

    Args:
        emotion_state: Dict of emotion values
        last_ramble_time: When last ramble was posted
        min_interval_minutes: Minimum minutes between rambles

    Returns:
        (should_ramble: bool, trigger: Optional[str])
    """
    if not emotion_state:
        return False, None

    # Check if enough time since last ramble
    if last_ramble_time:
        from datetime import datetime, timedelta, timezone

        if datetime.now(timezone.utc) - last_ramble_time < timedelta(
            minutes=min_interval_minutes
        ):
            return False, None

    # Check emotional triggers
    if emotion_state.get("loneliness", 0) > 0.7:
        return True, "loneliness"

    if emotion_state.get("excitement", 0) > 0.8:
        return True, "excitement"

    if emotion_state.get("frustration", 0) > 0.6:
        return True, "frustration"

    return False, None
