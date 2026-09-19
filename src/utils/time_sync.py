"""
KuCoin Al-Sat Botu — Zaman Senkronizasyonu
KuCoin sunucu saati ile lokal saat arasındaki farkı kontrol eder.
"""

import time
import requests
from datetime import datetime, timezone

from src.utils.logger import logger


def timestamp() -> str:
    """
    Merkezi zaman damgası üretici.
    Her çağrıda tutarlı ISO 8601 formatı döndürür.
    """
    now = datetime.now(timezone.utc)
    return now.isoformat()


def check_time_sync(timeout: int = 5) -> tuple[bool, float, str]:
    """
    KuCoin sunucu saati ile lokal saat arasındaki farkı kontrol et.
    Fark 3 saniyeden fazla ise yanlış zaman uyarısı döner.

    Returns:
        (success: bool, latency_ms: float, message: str)
    """
    try:
        # KuCoin sunucu saatini çek (data: milisaniye cinsinden epoch)
        response = requests.get(
            "https://api.kucoin.com/api/v1/timestamp",
            timeout=timeout
        )
        response.raise_for_status()

        server_time_ms = response.json()["data"]
        server_dt = datetime.fromtimestamp(server_time_ms / 1000, tz=timezone.utc)
        local_dt = datetime.now(timezone.utc)

        # Farkı hesapla (saniye cinsinden)
        diff_seconds = abs((server_dt - local_dt).total_seconds())
        latency_ms = round(diff_seconds * 1000, 2)

        if diff_seconds > 3:
            message = (
                f"⚠️ Zaman uyumsuzluğu: Lokal saat ile KuCoin sunucu saati "
                f"arasında {diff_seconds:.1f} saniyelik fark var. "
                f"Lütfen bilgisayarınızın saatini güncelleyin."
            )
            return False, latency_ms, message

        message = f"✅ Zaman senkronize: Gecikme {latency_ms}ms"
        return True, latency_ms, message

    except requests.exceptions.RequestException as e:
        return False, 0, f"❌ İnternet bağlantısı hatası: {e}"
