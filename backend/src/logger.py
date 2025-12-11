"""
Logging configuration for the application.

This module provides a centralized logger setup function
for consistent logging across all modules.
"""
import logging


def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Create and configure a logger with specified name and level.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance with StreamHandler
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
