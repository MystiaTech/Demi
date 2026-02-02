"""
Platform integration stubs for Demi.
Provides grumbling implementations for Minecraft, Twitch, TikTok, and YouTube.
"""

from src.integrations.stubs import (
    PlatformStatus,
    BasePlatformStub,
    create_platform_stubs,
    platform_stubs,
)

__all__ = [
    "PlatformStatus",
    "BasePlatformStub",
    "create_platform_stubs",
    "platform_stubs",
]
