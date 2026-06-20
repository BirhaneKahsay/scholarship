"""
Logging configuration and utilities.
Provides structured logging for all components.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

from app.config import settings


def setup_logging():
    """
    Configure logging for the application.
    Sets up both file and console handlers with appropriate formatters.
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Define formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (simpler format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.log_level))
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # File handler (detailed format)
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Agent-specific logger
    agent_logger = logging.getLogger("agents")
    agent_log_file = log_dir / f"agents_{datetime.now().strftime('%Y%m%d')}.log"
    agent_file_handler = logging.handlers.RotatingFileHandler(
        agent_log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
    )
    agent_file_handler.setLevel(logging.DEBUG)
    agent_file_handler.setFormatter(detailed_formatter)
    agent_logger.addHandler(agent_file_handler)

    # Database logger
    db_logger = logging.getLogger("sqlalchemy")
    db_logger.setLevel(logging.WARNING if not settings.debug else logging.DEBUG)

    root_logger.info(f"Logging initialized in {settings.environment} environment")
    root_logger.info(f"Log level: {settings.log_level}")
    root_logger.info(f"Log directory: {log_dir.absolute()}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Message")
    """
    return logging.getLogger(name)


# Initialize logging on module import
logger = setup_logging()

