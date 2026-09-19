"""
KuCoin Al-Sat Botu — Yapılandırma Modülü
.env dosyasından API anahtarları ve yapılandırma bilgilerini okur.
"""

import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()


class Config:
    """Uygulama yapılandırması."""

    # KuCoin API Ayarları
    API_KEY = os.getenv("KUCOIN_API_KEY")
    API_SECRET = os.getenv("KUCOIN_API_SECRET")
    API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")

    # Çalışma Modu
    IS_SANDBOX = os.getenv("KUCOIN_IS_SANDBOX", "false").lower() == "true"

    # Uygulama Ayarları
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    PORT = int(os.getenv("PORT", "8000"))
    HOST = os.getenv("HOST", "127.0.0.1")

    # KuCoin API URL'leri
    BASE_URL = "https://api.kucoin.com" if not IS_SANDBOX else "https://test-api.kucoin.com"
    WEBSOCKET_URL = "wss://ws-api.kucoin.com" if not IS_SANDBOX else "wss://ws-test-api.kucoin.com"

    # Simülasyon Modu
    DEFAULT_TRADING_MODE = os.getenv("DEFAULT_TRADING_MODE", "real")  # "real" veya "paper"
    SIMULATION_INITIAL_BALANCE_USDT = float(os.getenv("SIMULATION_INITIAL_BALANCE_USDT", "0.0"))
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "BTC/USDT")
    DEFAULT_TIMEFRAME = os.getenv("DEFAULT_TIMEFRAME", "1h")
    SIMULATION_MODE = DEFAULT_TRADING_MODE == "paper"  # .env'den okunur

    def validate_credentials(self) -> bool:
        """API anahtarlarının mevcut olup olmadığını doğrula."""
        return bool(self.API_KEY and self.API_SECRET and self.API_PASSPHRASE)
