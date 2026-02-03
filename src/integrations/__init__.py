"""
Platform integrations for Demi.
Provides both production integrations (Discord) and grumbling stubs (Minecraft, Twitch, TikTok, YouTube).
Includes voice channel integration for bidirectional voice I/O.
"""

from src.integrations.discord_bot import DiscordBot
from src.integrations.stubs import (
    PlatformStatus,
    BasePlatformStub,
    create_platform_stubs,
    platform_stubs,
)

# Voice integration (optional - requires DISCORD_VOICE_ENABLED=true)
try:
    from src.integrations.discord_voice import DiscordVoiceClient, VoiceSession
except ImportError:
    DiscordVoiceClient = None
    VoiceSession = None

__all__ = [
    "DiscordBot",
    "DiscordVoiceClient",
    "VoiceSession",
    "PlatformStatus",
    "BasePlatformStub",
    "create_platform_stubs",
    "platform_stubs",
]
