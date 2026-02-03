"""
Advanced logging system for Demi with structured logging, file rotation, and multiple outputs.
Supports console and file logging with configurable severity levels.
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import structlog

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


class DemiLogger:
    """Enhanced logger with file rotation, structured logging, and exception capturing."""

    def __init__(self):
        self._logger = None
        self._file_handler = None
        self._console_handler = None
        self._is_configured = False

    def configure(self, config) -> "DemiLogger":
        """Configure logging based on system configuration."""

        # Create log directory
        log_dir = Path(config.system.get("data_dir", "~/.demi")).expanduser() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Determine log level from configuration
        log_level_str = config.system.get("log_level", "INFO").upper()
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        log_level = log_level_map.get(log_level_str, logging.INFO)

        # Create date-based log filename
        log_filename = log_dir / f"demi_{datetime.now().strftime('%Y-%m-%d')}.log"

        # Remove existing handlers to avoid duplicates
        if self._is_configured:
            self._remove_handlers()

        # Configure file handler with rotation by date
        self._file_handler = logging.FileHandler(log_filename)
        self._file_handler.setLevel(log_level)

        # Configure console handler
        self._console_handler = logging.StreamHandler(sys.stdout)
        self._console_handler.setLevel(log_level)

        # Create formatters
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")

        # Apply formatters
        self._file_handler.setFormatter(file_formatter)
        self._console_handler.setFormatter(console_formatter)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add our handlers
        root_logger.addHandler(self._file_handler)
        root_logger.addHandler(self._console_handler)

        # Get the main logger instance
        self._logger = logging.getLogger("demi")
        self._is_configured = True

        # Configure structlog if available
        if HAS_STRUCTLOG:
            self._configure_structlog()

        return self

    def _configure_structlog(self):
        """Configure structlog for structured logging (JSON output)."""
        try:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.JSONRenderer(),
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        except Exception as e:
            self._logger.warning(f"Failed to configure structlog: {e}")

    def _remove_handlers(self):
        """Remove existing handlers to prevent duplicates."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if self._logger:
            self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        if self._logger:
            self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if self._logger:
            self._logger.warning(message, extra=kwargs)

    def error(self, message: str, exc_info=False, **kwargs):
        """Log error message."""
        if self._logger:
            self._logger.error(message, exc_info=exc_info, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        if self._logger:
            self._logger.critical(message, extra=kwargs)

    def exception(self, message: str, exc_info=True, **kwargs):
        """Log exception with contextual information."""
        if self._logger:
            self._logger.exception(message, extra=kwargs, exc_info=exc_info)

    def set_level(self, level: str):
        """Dynamically change log level."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        if level.upper() not in level_map:
            self.warning(f"Invalid log level: {level}")
            return

        new_level = level_map[level.upper()]

        if self._logger:
            self._logger.setLevel(new_level)
        if self._file_handler:
            self._file_handler.setLevel(new_level)
        if self._console_handler:
            self._console_handler.setLevel(new_level)

        self.info(f"Log level changed to {level.upper()}")


# Global logger instance
_logger_instance = None


def configure_logger(config):
    """Configure and return the global logger."""
    global _logger_instance

    _logger_instance = DemiLogger()
    _logger_instance.configure(config)

    return _logger_instance


def reconfigure_logger(config):
    """Reconfigure the global logger (used for dynamic log level changes)."""
    global _logger_instance

    if _logger_instance:
        _logger_instance.configure(config)
    else:
        configure_logger(config)


def get_logger() -> DemiLogger:
    """Get the global logger instance."""
    global _logger_instance

    if _logger_instance is None:
        from src.core.config import DemiConfig

        config = DemiConfig.load()
        configure_logger(config)

    return _logger_instance


# Initialize logger on import
try:
    from src.core.config import DemiConfig

    logger = configure_logger(DemiConfig.load())
except Exception as e:
    # Fallback logger if config not available
    logging.basicConfig(level=logging.INFO)
    logger = None
