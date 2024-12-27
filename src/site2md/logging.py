import logging
from typing import Optional

def setup_logger(name: str = "html2md", level: Optional[str] = None) -> logging.Logger:
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
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if level:
        logger.setLevel(getattr(logging, level.upper()))

    return logger

logger = setup_logger()
