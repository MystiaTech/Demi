"""
System boot orchestrator for Demi.
Manages staged initialization of logging, database, and platform integrations.
"""

from typing import List, Callable, Any

from src.core.config import DemiConfig
from src.core.logger import get_logger
from src.core.database import db_manager
from src.integrations.stubs import platform_stubs
from src.core.error_handler import global_error_handler


class SystemBootOrchestrator:
    """Orchestrates system initialization with staged boot sequence"""

    def __init__(self, config: DemiConfig = None):
        """
        Initialize boot orchestrator

        Args:
            config: Configuration object (loads default if None)
        """
        self.config = config or DemiConfig.load()
        self.logger = get_logger()
        self.boot_stages: List[Callable[[], Any]] = [
            self._initialize_logging,
            self._initialize_database,
            self._initialize_platform_stubs,
        ]
        self.initialized = False

    def _initialize_logging(self) -> None:
        """Logging configuration happens in logger.py, just log boot stage"""
        self.logger.info("✓ Logging system initialized")

    def _initialize_database(self) -> None:
        """Initialize database connection and verify tables"""
        try:
            # Database manager already initializes in its constructor
            session = db_manager.get_session()
            session.close()
            self.logger.info("✓ Database system initialized")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    def _initialize_platform_stubs(self) -> None:
        """Initialize all platform stubs"""
        initialized_platforms = []
        failed_platforms = []

        for name, stub in platform_stubs.items():
            try:
                if stub.initialize():
                    initialized_platforms.append(name)
                    self.logger.debug(f"✓ Platform stub initialized: {name}")
                else:
                    failed_platforms.append(name)
                    self.logger.warning(f"⚠ Platform stub failed to initialize: {name}")
            except Exception as e:
                failed_platforms.append(name)
                self.logger.error(f"Platform stub error ({name}): {e}")

        if initialized_platforms:
            self.logger.info(
                f"✓ Initialized platforms: {', '.join(initialized_platforms)}"
            )
        if failed_platforms:
            self.logger.warning(f"⚠ Failed platforms: {', '.join(failed_platforms)}")

    def boot(self) -> bool:
        """
        Execute system boot sequence

        Returns:
            True if boot successful, False otherwise
        """
        if self.initialized:
            self.logger.warning("System already booted, skipping boot sequence")
            return True

        self.logger.info("🚀 Demi system booting up...")
        global_error_handler.reset_error_count()

        try:
            for stage in self.boot_stages:
                try:
                    stage()
                except Exception as e:
                    self.logger.error(f"Boot stage failed: {stage.__name__} - {e}")
                    return False

            self.initialized = True
            self.logger.info("✓ Demi system boot complete")
            return True

        except Exception as e:
            self.logger.error(f"System boot failed: {e}")
            return False

    def shutdown(self) -> None:
        """Clean shutdown of system resources"""
        self.logger.info("Demi system shutting down...")
        try:
            db_manager.close()
            self.logger.info("✓ Database connection closed")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def get_boot_status(self) -> dict:
        """Get current boot status"""
        return {
            "initialized": self.initialized,
            "config_loaded": self.config is not None,
            "database_connected": db_manager.db_path is not None,
            "platform_stubs": {
                name: stub.get_status() for name, stub in platform_stubs.items()
            },
        }


# Global system boot orchestrator
system_boot = SystemBootOrchestrator()


def initialize_system() -> bool:
    """
    Convenience function to boot the system

    Returns:
        True if boot successful, False otherwise
    """
    return system_boot.boot()


def shutdown_system() -> None:
    """Convenience function to shutdown the system"""
    system_boot.shutdown()
