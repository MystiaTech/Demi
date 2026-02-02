"""
Global error handling and recovery mechanism for Demi.
Provides comprehensive exception handling, logging, and recovery strategies.
"""

import sys
import traceback
from typing import Optional, Dict, Any, Type

from src.core.logger import get_logger
from src.core.config import DemiConfig


class DemiErrorHandler:
    """Global error handling and recovery mechanism"""

    def __init__(self, config: Optional[DemiConfig] = None):
        """Initialize error handler with configuration"""
        self.config = config or DemiConfig.load()
        self.error_count = 0
        self.max_consecutive_errors = self.config.system.get("max_errors", 5)
        self.logger = get_logger()

    def handle_exception(
        self,
        exc_type: Type[Exception],
        exc_value: Exception,
        exc_traceback: traceback,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Comprehensive exception handling with logging and potential recovery

        Args:
            exc_type: The exception type
            exc_value: The exception instance
            exc_traceback: The traceback object
            context: Optional context dictionary for additional information
        """
        context = context or {}

        # Log exception with full traceback
        self.logger.exception(
            f"Unhandled exception: {exc_type.__name__}",
            extra={**context, "error_type": exc_type.__name__},
        )

        # Track consecutive errors
        self.error_count += 1

        # Determine severity
        if exc_type in (KeyboardInterrupt, SystemExit):
            self.logger.critical("System exit or keyboard interrupt detected")
            sys.exit(1)

        # Severity-based handling
        if self.error_count > self.max_consecutive_errors:
            self.logger.error(
                f"Maximum error threshold ({self.max_consecutive_errors}) exceeded. "
                "Initiating emergency shutdown."
            )
            sys.exit(1)

        # Optional recovery logic
        if self.config.system.get("auto_recover", False):
            self._attempt_recovery(exc_type, exc_value)

    def _attempt_recovery(
        self, exc_type: Type[Exception], exc_value: Exception
    ) -> None:
        """Attempt to recover from specific error types"""
        recovery_map = {
            MemoryError: self._memory_recovery,
            RuntimeError: self._runtime_recovery,
        }

        recovery_func = recovery_map.get(exc_type)
        if recovery_func:
            try:
                recovery_func(exc_value)
            except Exception as e:
                self.logger.error(f"Recovery attempt failed: {e}")

    def _memory_recovery(self, exc: MemoryError) -> None:
        """Attempt to recover from memory-related issues"""
        self.logger.warning("Memory pressure detected. Attempting cleanup...")
        try:
            import gc

            gc.collect()
            self.logger.info("Garbage collection completed")
        except Exception as e:
            self.logger.error(f"Memory recovery failed: {e}")

    def _runtime_recovery(self, exc: RuntimeError) -> None:
        """Generic runtime error recovery"""
        self.logger.warning("Attempting runtime recovery...")
        # Add runtime recovery strategies here

    def reset_error_count(self) -> None:
        """Reset consecutive error tracking"""
        self.error_count = 0
        self.logger.debug("Error count reset to 0")

    def get_error_status(self) -> Dict[str, Any]:
        """Get current error handler status"""
        return {
            "consecutive_errors": self.error_count,
            "max_errors": self.max_consecutive_errors,
            "auto_recovery_enabled": self.config.system.get("auto_recover", False),
        }


# Global error handler instance
global_error_handler = DemiErrorHandler()


def global_exception_handler(
    exc_type: Type[Exception], exc_value: Exception, exc_traceback: traceback
) -> None:
    """Global exception hook for unhandled exceptions"""
    global_error_handler.handle_exception(exc_type, exc_value, exc_traceback)


# Install global exception hook
sys.excepthook = global_exception_handler
