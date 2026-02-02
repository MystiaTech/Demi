#!/usr/bin/env python3
"""
Demi main entry point - Application startup and lifecycle management.

Handles:
- Command-line argument parsing
- Configuration validation
- Conductor initialization and startup
- Graceful shutdown with signal handling
- Exit codes for different failure scenarios
"""

import asyncio
import argparse
import signal
import sys
import time
from pathlib import Path

from src.core.logger import get_logger
from src.core.config import DemiConfig
from src.conductor import get_conductor

logger = get_logger()


class ApplicationManager:
    """Manages application lifecycle."""

    def __init__(self, config_path: str = None, log_level: str = None):
        """
        Initialize application manager.

        Args:
            config_path: Path to config file (optional)
            log_level: Log level override (optional)
        """
        self.config_path = config_path or "src/core/defaults.yaml"
        self.log_level = log_level
        self.conductor = None
        self.start_time = None
        self._shutdown_in_progress = False

    def validate_configuration(self) -> bool:
        """
        Validate configuration before startup.

        Returns:
            True if valid, False otherwise
        """
        try:
            logger.info("Validating configuration...")

            # Check config file exists
            if self.config_path:
                config_file = Path(self.config_path)
                if not config_file.exists():
                    logger.error(f"Config file not found: {self.config_path}")
                    return False

            # Load and validate config
            config = DemiConfig.load(self.config_path)

            # Basic validation
            if not config.system:
                logger.error("Invalid config: missing 'system' section")
                return False

            logger.info("✓ Configuration valid")
            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False

    async def startup(self) -> bool:
        """
        Execute application startup.

        Returns:
            True if startup successful, False otherwise
        """
        try:
            self.start_time = time.time()
            logger.info("=" * 70)
            logger.info("DEMI APPLICATION STARTUP")
            logger.info("=" * 70)

            # Load configuration
            logger.info("Loading configuration...")
            config = DemiConfig.load(self.config_path)

            # Initialize conductor
            logger.info("Initializing conductor...")
            self.conductor = get_conductor(config)

            # Execute startup sequence
            if not await self.conductor.startup():
                logger.error("Conductor startup failed")
                return False

            # Startup complete
            startup_time_sec = time.time() - self.start_time
            logger.info("=" * 70)
            logger.info(f"✓ DEMI STARTUP COMPLETE ({startup_time_sec:.2f}s)")
            logger.info("=" * 70)

            return True

        except Exception as e:
            logger.error(f"Application startup failed: {str(e)}", exc_info=True)
            return False

    async def shutdown(self) -> None:
        """
        Execute graceful shutdown.

        Handles cleanup of all resources.
        """
        if self._shutdown_in_progress:
            return

        self._shutdown_in_progress = True

        try:
            logger.info("Shutdown signal received, initiating graceful shutdown...")

            if self.conductor and self.conductor.is_running():
                await self.conductor.shutdown()

            uptime = time.time() - self.start_time if self.start_time else 0
            logger.info(f"Application uptime: {uptime:.2f}s")

        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}", exc_info=True)

    def register_signal_handlers(self) -> None:
        """Register OS signal handlers for graceful shutdown."""

        def handle_signal(signum, frame):
            logger.info(f"Signal {signum} received")
            asyncio.create_task(self.shutdown())

        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
            logger.debug("Signal handlers registered")
        except Exception as e:
            logger.warning(f"Failed to register signal handlers: {str(e)}")

    async def run_main_loop(self) -> None:
        """
        Main application loop.

        Runs until shutdown is requested.
        """
        try:
            logger.info("Entering main loop...")

            while self.conductor and self.conductor.is_running():
                # Keep the event loop running
                await asyncio.sleep(1)

            logger.info("Main loop exited")

        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}", exc_info=True)

    async def run(self) -> int:
        """
        Run the application.

        Returns:
            Exit code (0 for success, >0 for failure)
        """
        # Validate configuration
        if not self.validate_configuration():
            return 1

        # Register signal handlers
        self.register_signal_handlers()

        # Startup
        if not await self.startup():
            return 1

        try:
            # Main loop
            await self.run_main_loop()
            return 0

        except Exception as e:
            logger.error(f"Application error: {str(e)}", exc_info=True)
            return 1

        finally:
            # Ensure shutdown is called
            if not self._shutdown_in_progress:
                await self.shutdown()


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Demi - AI Companion with Personality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Run with defaults
  python main.py --config config/custom.yaml       # Use custom config
  python main.py --log-level DEBUG                 # Enable debug logging
  python main.py --version                         # Show version
  python main.py --dry-run                         # Validate config only
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file (default: src/core/defaults.yaml)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Override log level",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and exit without starting",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information",
    )

    return parser.parse_args()


async def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code
    """
    args = parse_arguments()

    # Handle version flag
    if args.version:
        print("Demi v1.0")
        print("AI Companion with Personality")
        return 0

    # Create application manager
    app = ApplicationManager(config_path=args.config, log_level=args.log_level)

    # Handle dry-run mode
    if args.dry_run:
        logger.info("Dry-run mode: validating configuration only")
        if app.validate_configuration():
            logger.info("✓ Configuration valid")
            return 0
        else:
            logger.error("✗ Configuration invalid")
            return 1

    # Run application
    return await app.run()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
