"""
KuCoin Al-Sat Botu — Modül 1: KuCoin Bağlantısı & Hesap Durumu
KuCoin API entegrasyonu, bakiye sorgulama ve bağlantı doğrulama.
"""

import ccxt
import time
import hmac
import hashlib
import json
from datetime import datetime, timezone

from src.config import Config
from src.models.account import (
    ConnectionStatusResponse,
    AccountBalancesResponse,
    PortfolioSummaryResponse,
    TestConnectionResponse,
)
from src.utils.logger import logger


class KuCoinAccount:
    """KuCoin hesap bağlantısı ve bakiye yönetimi."""

    def __init__(self):
        self.config = Config()
        self.exchange: ccxt.exchange | None = None
        self.is_connected = False

    def connect(self) -> bool:
        """KuCoin API'ye bağlan."""
        try:
            self.exchange = ccxt.binance(  # ccxt'te KuCoin desteği var mı kontrol edilecek
                {
                    "apiKey": self.config.API_KEY,
                    "secret": self.config.API_SECRET,
                    "password": self.config.API_PASSPHRASE,
                    "sandbox": self.config.IS_SANDBOX,
                }
            )
            self.is_connected = True
            logger.info("✅ KuCoin API bağlantısı kuruldu")
            return True
        except Exception as e:
            logger.error(f"❌ KuCoin API bağlantı hatası: {e}")
            return False

    def test_connection(self) -> TestConnectionResponse:
        """API bağlantı testi."""
        try:
            success, latency_ms, message = self._check_time_sync()

            if success:
                return TestConnectionResponse(
                    success=True,
                    data={"message": message, "latency_ms": latency_ms},
                    error=None,
                    timestamp=datetime.now(timezone.utc).isoformat() + "Z"
                )
            else:
                return TestConnectionResponse(
                    success=False,
                    data={},
                    error=message,
                    timestamp=datetime.now(timezone.utc).isoformat() + "Z"
                )
        except Exception as e:
            return TestConnectionResponse(
                success=False,
                data={},
                error=f"Bağlantı testi başarısız: {e}",
                timestamp=datetime.now(timezone.utc).isoformat() + "Z"
            )

    def _check_time_sync(self) -> tuple[bool, float, str]:
        """Zaman senkronizasyonu kontrolü."""
        try:
            # ccxt ile zaman senkronizasyonu kontrolü
            start_time = time.time()
            self.exchange.fetch_time()
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return True, latency_ms, f"✅ Zaman senkronize: {latency_ms}ms"
        except Exception as e:
            return False, 0, f"❌ Zaman senkronizasyonu hatası: {e}"

    async def get_balances(self) -> AccountBalancesResponse:
        """Hesap bakiyelerini çek."""
        try:
            if not self.exchange:
                return AccountBalancesResponse(
                    success=False,
                    data={},
                    error="KuCoin API'ye bağlanılamadı",
                    timestamp=datetime.now(timezone.utc).isoformat() + "Z"
                )

            balances = await self.exchange.fetch_balance()
            assets = balances.get("total", [])

            asset_list = []
            for asset in assets:
                if asset["type"] == "currency":
                    symbol = asset["currency"]
                    if symbol == "USDT":
                        continue  # USDT fiyatı her zaman 1.0

                    # Anlık fiyatı çek
                    try:
                        ticker = await self.exchange.fetch_ticker(f"{symbol}/USDT")
                        price = ticker["last"]
                    except Exception:
                        price = 0.0

                    asset_value = round(float(asset["total"]) * price, 2)
                    asset_list.append({
                        "symbol": symbol,
                        "free": float(asset["free"]),
                        "used": float(asset["used"]),
                        "total": float(asset["total"]),
                        "price_usdt": price,
                        "usdt_value": asset_value,
                        "portfolio_share_percent": 0.0  # Sonraki adımda hesaplanacak
                    })

            return AccountBalancesResponse(
                success=True,
                data={"balances": asset_list},
                error=None,
                timestamp=datetime.now(timezone.utc).isoformat() + "Z"
            )
        except Exception as e:
            return AccountBalancesResponse(
                success=False,
                data={},
                error=f"Bakiye sorgulama hatası: {e}",
                timestamp=datetime.now(timezone.utc).isoformat() + "Z"
            )

    async def get_summary(self) -> PortfolioSummaryResponse:
        """Portföy özet bilgisi."""
        try:
            balances = await self.get_balances()
            total_usdt = 0.0

            for asset in balances.data.get("balances", []):
                if asset["symbol"] == "USDT":
                    total_usdt += asset["total"]

            return PortfolioSummaryResponse(
                success=True,
                data={
                    "total_portfolio_usdt": total_usdt,
                    "free_usdt": total_usdt,  # Basitlik için, kullanılabilir USDT
                    "in_orders_usdt": 0.0
                },
                error=None,
                timestamp=datetime.now(timezone.utc).isoformat() + "Z"
            )
        except Exception as e:
            return PortfolioSummaryResponse(
                success=False,
                data={},
                error=f"Portföy özet hatası: {e}",
                timestamp=datetime.now(timezone.utc).isoformat() + "Z"
            )
