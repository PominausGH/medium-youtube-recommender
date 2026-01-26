# logging_config.py
"""Centralized logging configuration with optional Sentry integration."""

import logging
import os
import sys
from pathlib import Path

# Optional Sentry integration
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


def setup_logging(
    level: str = None,
    log_file: str = None,
    enable_sentry: bool = True
) -> logging.Logger:
    """Configure application-wide logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO or LOG_LEVEL env var.
        log_file: Optional file path for logging. Defaults to logs/app.log in production.
        enable_sentry: Whether to initialize Sentry if DSN is configured.
    
    Returns:
        Root logger instance.
    """
    # Determine log level
    log_level = level or os.getenv('LOG_LEVEL', 'INFO')
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logs directory if needed
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    handlers = []
    
    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    handlers.append(console_handler)
    
    # File handler for production
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True
    )
    
    # Initialize Sentry if available and configured
    sentry_dsn = os.getenv('SENTRY_DSN')
    if enable_sentry and SENTRY_AVAILABLE and sentry_dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[sentry_logging],
            traces_sample_rate=0.1,
            environment=os.getenv('ENVIRONMENT', 'production'),
            release=os.getenv('APP_VERSION', '1.0.0'),
        )
        logging.info('Sentry error tracking initialized')
    
    return logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Module name (typically __name__).
    
    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


# Initialize logging on import if running in production
if os.getenv('ENVIRONMENT') == 'production':
    setup_logging(log_file='logs/app.log')
