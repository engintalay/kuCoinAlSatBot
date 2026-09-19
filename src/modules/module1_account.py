"""
KuCoin Al-Sat Botu — Modül 1: KuCoin Bağlantısı & Hesap Durumu
KuCoin API entegrasyonu, bakiye sorgulama ve bağlantı doğrulama.
"""

import ccxt
import ccxt.async_support
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
from src.utils.time_sync import timestamp, check_time_sync


class KuCoinAccount:
    """KuCoin hesap bağlantısı ve bakiye yönetimi."""

    def __init__(self):
        self.config = Config()
        self.exchange: ccxt.async_support.kucoin | None = None
        self.is_connected = False

    def connect(self) -> bool:
        """KuCoin API'ye bağlan."""
        try:
            self.exchange = ccxt.async_support.kucoin(
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
        """
        API bağlantı testi.

        `.env` şifrelerinin varlığını doğrular ve KuCoin sunucu saati ile
        yerel saat arasındaki senkronizasyonu kontrol eder. Bu kontrol borsa
        (exchange) nesnesine bağlı değildir; doğrudan KuCoin public zaman
        endpoint'ine HTTP isteği atan `check_time_sync()` kullanılır.
        """
        try:
            # 1. Kimlik bilgisi (.env) kontrolü
            if not self.config.validate_credentials():
                return TestConnectionResponse(
                    success=False,
                    data={},
                    error=(
                        "API kimlik bilgileri eksik. Lütfen .env dosyasında "
                        "KUCOIN_API_KEY, KUCOIN_API_SECRET ve "
                        "KUCOIN_API_PASSPHRASE değerlerini doldurun."
                    ),
                    timestamp=timestamp()
                )

            # 2. Zaman senkronizasyonu kontrolü (exchange gerektirmez)
            success, latency_ms, message = check_time_sync()

            if success:
                return TestConnectionResponse(
                    success=True,
                    data={"message": message, "latency_ms": latency_ms},
                    error=None,
                    timestamp=timestamp()
                )
            else:
                return TestConnectionResponse(
                    success=False,
                    data={"latency_ms": latency_ms},
                    error=message,
                    timestamp=timestamp()
                )
        except Exception as e:
            return TestConnectionResponse(
                success=False,
                data={},
                error=f"Bağlantı testi başarısız: {e}",
                timestamp=timestamp()
            )

    def _check_time_sync(self) -> tuple[bool, float, str]:
        """Zaman senkronizasyonu kontrolü."""
        try:
            if not self.exchange:
                return False, 0, "❌ Exchange bağlantısı yok"
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
            # Exchange henüz oluşturulmadıysa otomatik bağlan (lazy connect)
            if not self.exchange:
                self.connect()

            if not self.exchange:
                return AccountBalancesResponse(
                    success=False,
                    data={},
                    error="KuCoin API'ye bağlanılamadı",
                    timestamp=timestamp()
                )

            # KuCoin fonları farklı hesaplarda tutar: 'trade' (spot) ve 'main'
            # (funding). Her ikisini de çekip varlık bazında birleştiriyoruz.
            combined_total: dict[str, float] = {}
            combined_free: dict[str, float] = {}
            combined_used: dict[str, float] = {}

            for account_type in ("trade", "main"):
                try:
                    bal = await self.exchange.fetch_balance({"type": account_type})
                except Exception as e:
                    logger.error(f"'{account_type}' hesabı bakiye hatası: {e}")
                    continue

                for symbol, amount in bal.get("total", {}).items():
                    combined_total[symbol] = combined_total.get(symbol, 0.0) + float(amount or 0.0)
                for symbol, amount in bal.get("free", {}).items():
                    combined_free[symbol] = combined_free.get(symbol, 0.0) + float(amount or 0.0)
                for symbol, amount in bal.get("used", {}).items():
                    combined_used[symbol] = combined_used.get(symbol, 0.0) + float(amount or 0.0)

            asset_list = []
            for symbol, total_amount in combined_total.items():
                # Sıfır bakiyeli varlıkları atla
                if total_amount <= 0:
                    continue

                free_amount = combined_free.get(symbol, 0.0)
                used_amount = combined_used.get(symbol, 0.0)

                # USDT'nin USDT karşılığı her zaman 1.0'dır; diğerleri için
                # anlık fiyatı çek.
                if symbol == "USDT":
                    price = 1.0
                else:
                    try:
                        ticker = await self.exchange.fetch_ticker(f"{symbol}/USDT")
                        price = float(ticker["last"])
                    except Exception:
                        price = 0.0

                asset_value = round(total_amount * price, 2)
                asset_list.append({
                    "symbol": symbol,
                    "free": free_amount,
                    "used": used_amount,
                    "total": total_amount,
                    "price_usdt": price,
                    "usdt_value": asset_value,
                    "portfolio_share_percent": 0.0  # Sonraki adımda hesaplanacak
                })

            # Portföy payı yüzdesini hesapla
            grand_total = sum(a["usdt_value"] for a in asset_list)
            if grand_total > 0:
                for a in asset_list:
                    a["portfolio_share_percent"] = round(a["usdt_value"] / grand_total * 100, 2)

            return AccountBalancesResponse(
                success=True,
                data={"balances": asset_list},
                error=None,
                timestamp=timestamp()
            )
        except Exception as e:
            return AccountBalancesResponse(
                success=False,
                data={},
                error=f"Bakiye sorgulama hatası: {e}",
                timestamp=timestamp()
            )

    async def get_summary(self) -> PortfolioSummaryResponse:
        """Portföy özet bilgisi."""
        try:
            balances = await self.get_balances()

            # Bakiye çekimi başarısızsa özet de hata dönmeli
            if not balances.success:
                return PortfolioSummaryResponse(
                    success=False,
                    data={},
                    error=balances.error or "Bakiye bilgisi alınamadı",
                    timestamp=timestamp()
                )

            total_usdt = 0.0
            free_usdt = 0.0

            for asset in balances.data.get("balances", []):
                if asset["symbol"] == "USDT":
                    continue
                total_usdt += asset["usdt_value"]
                free_usdt += asset["free"] * asset["price_usdt"]

            # USDT bakiyesini de ekle
            usdt_balance = balances.data.get("balances", [])
            for asset in usdt_balance:
                if asset["symbol"] == "USDT":
                    total_usdt += asset["usdt_value"]
                    free_usdt += asset["free"]

            return PortfolioSummaryResponse(
                success=True,
                data={
                    "total_portfolio_usdt": total_usdt,
                    "free_usdt": free_usdt,
                    "in_orders_usdt": 0.0
                },
                error=None,
                timestamp=timestamp()
            )
        except Exception as e:
            return PortfolioSummaryResponse(
                success=False,
                data={},
                error=f"Portföy özet hatası: {e}",
                timestamp=timestamp()
            )

    async def close(self) -> None:
        """
        ccxt async exchange kaynaklarını serbest bırak.
        ccxt.async_support, aiohttp client session'ının açıkça kapatılmasını
        gerektirir; aksi halde "Unclosed client session" uyarısı ve kaynak
        sızıntısı oluşur.
        """
        if self.exchange is not None:
            try:
                await self.exchange.close()
            except Exception as e:
                logger.error(f"Exchange kapatma hatası: {e}")
            finally:
                self.exchange = None
                self.is_connected = False
