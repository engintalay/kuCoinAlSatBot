"""
KuCoin Al-Sat Botu — Logging Yapısı
"""

import logging
import os
from datetime import datetime

# Log dizini
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def setup_logger(name: str = "kucoin_bot", level: str = "INFO") -> logging.Logger:
    """Logging ayarları."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Format
    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Konsol handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # Dosya handler
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger()
