"""
Centralized logging configuration for the Acoustic Analysis Tool.

This module provides a consistent logging setup that:
1. Configures logging levels based on environment
2. Provides module-specific loggers
3. Supports both console and file output
4. Integrates with existing debug_logger for HVAC calculations

Usage:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Message")
    logger.debug("Debug message")
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


# Application name for log files
APP_NAME = "AcousticAnalysis"

# Default log level (can be overridden by environment)
DEFAULT_LOG_LEVEL = "INFO"

# Environment variables for configuration
ENV_LOG_LEVEL = "ACOUSTIC_LOG_LEVEL"
ENV_LOG_FILE = "ACOUSTIC_LOG_FILE"
ENV_DEBUG = "DEBUG"


def _get_log_level() -> int:
    """Get the logging level from environment or default."""
    level_str = os.environ.get(ENV_LOG_LEVEL, "").upper()
    if not level_str:
        # Check generic DEBUG flag
        if os.environ.get(ENV_DEBUG, "").lower() in ("1", "true", "yes", "on"):
            level_str = "DEBUG"
        else:
            level_str = DEFAULT_LOG_LEVEL

    return getattr(logging, level_str, logging.INFO)


def _get_log_file_path() -> Optional[Path]:
    """Get the log file path if file logging is enabled."""
    log_file = os.environ.get(ENV_LOG_FILE)
    if log_file:
        return Path(log_file)

    # Check if file logging is requested
    if os.environ.get(ENV_DEBUG, "").lower() in ("1", "true", "yes", "on"):
        # Use user data directory
        try:
            from utils import get_user_data_directory
            user_dir = get_user_data_directory()
        except ImportError:
            user_dir = Path.home() / "Documents" / "AcousticAnalysis"

        log_dir = Path(user_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / f"{APP_NAME}.log"

    return None


def configure_logging():
    """Configure the application-wide logging.

    This should be called once at application startup.
    """
    log_level = _get_log_level()
    log_file = _get_log_file_path()

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler - always enabled
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        "%(levelname)s [%(name)s]: %(message)s"
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler - only if debug mode or explicitly requested
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always capture debug in file
        file_format = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s:%(lineno)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

    # Set specific module levels
    # Reduce noise from third-party libraries
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Auto-configure on import if not already done
if not logging.getLogger().handlers:
    configure_logging()
