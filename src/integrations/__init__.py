"""
Platform integrations for Demi.
Provides both production integrations (Discord) and grumbling stubs (Minecraft, Twitch, TikTok, YouTube).
"""

from src.integrations.discord_bot import DiscordBot
from src.integrations.stubs import (
    PlatformStatus,
    BasePlatformStub,
    create_platform_stubs,
    platform_stubs,
)

__all__ = [
    "DiscordBot",
    "PlatformStatus",
    "BasePlatformStub",
    "create_platform_stubs",
    "platform_stubs",
]
