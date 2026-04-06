"""
Logger Utility
Centralized logging configuration with file + console output.
"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a named logger with console and rotating file handlers.

    Args:
        name: Logger name (usually app name).
        level: Logging level (default INFO).

    Returns:
        Configured logger instance.
    """
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{name}.log"

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # Already configured

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s.%(module)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    ch.setLevel(level)
    logger.addHandler(ch)

    # File handler
    try:
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=2)
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
    except Exception:
        pass  # If file logging fails, console is enough

    return logger
