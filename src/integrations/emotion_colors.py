"""
Emotion color mappings for Discord integration.

Centralizes emotion-to-color mapping for better organization and reusability
across different platform integrations.
"""

import discord


# Emotion to Discord color mapping
EMOTION_COLORS = {
    "loneliness": discord.Color.purple(),    # 0x9370DB - longing, introspection
    "excitement": discord.Color.green(),     # 0x2ECC71 - energy, growth
    "frustration": discord.Color.red(),      # 0xE74C3C - anger, warning
    "affection": discord.Color.magenta(),    # 0xFF1493 - love, warmth (hot pink)
    "confidence": discord.Color.blue(),      # 0x3498DB - stability, trust
    "curiosity": discord.Color.teal(),       # 0x1ABC9C - exploration (cyan)
    "jealousy": discord.Color.orange(),      # 0xE67E22 - envy, caution
    "vulnerability": discord.Color.magenta(), # 0xD946EF - openness, sensitivity
    "defensiveness": discord.Color.dark_gray(), # 0x36393B - withdrawal, protection
}


def get_emotion_color(emotion_name: str) -> discord.Color:
    """
    Get the Discord color for a given emotion.
    
    Args:
        emotion_name: Name of the emotion
        
    Returns:
        Discord Color object, defaults to purple if emotion not found
    """
    return EMOTION_COLORS.get(emotion_name, discord.Color.purple())


def get_all_emotion_colors() -> dict:
    """
    Get all emotion color mappings.
    
    Returns:
        Dictionary mapping emotion names to Discord colors
    """
    return EMOTION_COLORS.copy()
