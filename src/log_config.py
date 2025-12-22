# src/log_config.py
import sys
from pathlib import Path

from loguru import logger


def setup_logging():
    """
    Configures loguru for structured logging with file rotation and retention.
    """
    log_path = Path("logs")
    log_path.mkdir(parents=True, exist_ok=True)

    logger.remove()  # Remove default handler

    # Console logging
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # File logging with rotation and retention
    logger.add(
        log_path / "file.log",
        rotation="10 MB",  # Rotate every 10 MB
        retention="7 days",  # Keep logs for 7 days
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        compression="zip",  # Compress rotated files
        serialize=False,  # Set to True for JSON logs
    )

    logger.info("Logging configured successfully.")
