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
    HOST = os.getenv("HOST", "0.0.0.0")

    # KuCoin API URL'leri
    BASE_URL = "https://api.kucoin.com" if not IS_SANDBOX else "https://test-api.kucoin.com"
    WEBSOCKET_URL = "wss://ws-api.kucoin.com" if not IS_SANDBOX else "wss://ws-test-api.kucoin.com"

    # Simülasyon Modu
    SIMULATION_MODE = False  # Varsayılan: Gerçek mod

    def validate_credentials(self) -> bool:
        """API anahtarlarının mevcut olup olmadığını doğrula."""
        return bool(self.API_KEY and self.API_SECRET and self.API_PASSPHRASE)
