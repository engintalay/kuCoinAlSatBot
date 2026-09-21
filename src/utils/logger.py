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


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    params: dict | None = None,
    body: dict | None = None,
    error: str | None = None,
):
    """
    API isteği loglama. Hata durumunda isteği kaydeder.

    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, PUT, DELETE)
        path: API endpoint path (ör. /api/v1/orders/create)
        params: Query params
        body: Request body
        error: Hata mesajı (varsa)
    """
    msg = f"[{method}] {path}"
    if params:
        msg += f"?{params}"
    if body:
        # Güvenlik: API key/secret içermeyenler
        safe_body = dict(body)
        for key in ["apiKey", "secret", "password", "api_key", "api_secret"]:
            safe_body.pop(key, None)
        msg += f" | body={safe_body}"
    if error:
        msg += f" | HATA: {error}"
    logger.error(msg)


# Global logger instance
logger = setup_logger()
