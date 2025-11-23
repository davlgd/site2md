import logging
from typing import Optional

def setup_logger(name: str = "site2md", level: str = "INFO") -> logging.Logger:
    """Configure and return a logger

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, etc)

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, level.upper()))

    return logger

logger = setup_logger()
