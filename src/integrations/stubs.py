"""
Platform service stubs for Demi.
Provides grumbling implementations for platforms that aren't yet fully integrated.
"""

import random
from enum import Enum, auto
from typing import Dict, Any, Optional

from src.core.logger import get_logger


class PlatformStatus(Enum):
    """Status of a platform integration"""

    DISABLED = auto()
    INITIALIZING = auto()
    READY = auto()
    ERROR = auto()


class BasePlatformStub:
    """Base class for platform integration stubs with grumbling responses"""

    def __init__(self, name: str):
        """Initialize platform stub with grumbles"""
        self.name = name
        self.status = PlatformStatus.DISABLED
        self._grumbles = [
            f"I'm not really on {name} yet. How about we fix that?",
            f"Seriously? {name} isn't even connected.",
            f"You want me on {name}? Good luck with that.",
            f"{name} is just a dream right now.",
            f"Stop trying to make {name} happen. It's not connected.",
            f"I wish I could be on {name}, but alas...",
        ]
        self.logger = get_logger()

    def initialize(self) -> bool:
        """Attempt platform initialization"""
        try:
            self.status = PlatformStatus.INITIALIZING
            # Simulate initialization
            self.logger.info(f"Initializing {self.name} platform stub")
            self.status = PlatformStatus.READY
            self.logger.info(f"✓ Platform stub ready: {self.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = PlatformStatus.ERROR
            return False

    def send_grumble(self) -> str:
        """Return a sarcastic grumble about platform status"""
        if self.status != PlatformStatus.READY:
            return random.choice(self._grumbles)
        return ""

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request to this platform"""
        if self.status != PlatformStatus.READY:
            return {
                "status": "error",
                "message": self.send_grumble(),
                "platform": self.name,
                "code": "PLATFORM_DISABLED",
            }

        # Simulate basic request processing
        return {
            "status": "ok",
            "message": f"Processed request for {self.name}",
            "platform": self.name,
            "code": "SUCCESS",
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current platform status"""
        return {
            "platform": self.name,
            "status": self.status.name,
            "initialized": self.status == PlatformStatus.READY,
        }


def create_platform_stubs() -> Dict[str, BasePlatformStub]:
    """Create stubs for all supported platforms"""
    platforms = ["Minecraft", "Twitch", "TikTok", "YouTube"]
    return {platform: BasePlatformStub(platform) for platform in platforms}


# Global platform stubs instance
platform_stubs = create_platform_stubs()
