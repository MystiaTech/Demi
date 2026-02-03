"""Mobile app integration module.

Provides REST and WebSocket API for mobile clients (Flutter, native, etc.)
"""

from src.mobile.api import MobileAPIServer

__all__ = ["MobileAPIServer"]
