import os
import sys
import logging
import structlog
from datetime import datetime
from src.core.config import DemiConfig


def configure_logger(config: DemiConfig = None):
    """Configure logging based on system configuration"""
    if config is None:
        config = DemiConfig.load()
    
    log_dir = os.path.expanduser('~/.demi/logs')
    os.makedirs(log_dir, exist_ok=True)

    # Determine log level from configuration
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    log_level = log_level_map.get(config.system.get('log_level', 'INFO'), logging.INFO)

    # Configure file logging with rotation by date
    log_filename = os.path.join(log_dir, f'demi_{datetime.now().strftime("%Y-%m-%d")}.log')
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Formatter with structured information
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(module)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')

    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    # Clear existing handlers
    root_logger.handlers = []
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(log_level)

    # Structlog configuration
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,  # Respect log levels
            structlog.stdlib.add_log_level,  # Add log level to event dict
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt='iso'),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()  # JSON for machine parsing
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger_instance = structlog.get_logger()
    logger_instance.info("Logger initialized", log_level=config.system.get('log_level'))
    return logger_instance


# Global logger instance
logger = configure_logger()


def log_exception(e, context=None):
    """Enhanced exception logging with optional context"""
    extra = context or {}
    logger.error(
        "Unhandled Exception",
        exc_info=sys.exc_info(),
        **extra
    )
