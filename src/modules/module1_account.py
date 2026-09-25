"""
KuCoin Al-Sat Botu — Modül 1: KuCoin Bağlantısı & Hesap Durumu
KuCoin API entegrasyonu, bakiye sorgulama ve bağlantı doğrulama.
"""

import ccxt
import ccxt.async_support
import ccxt.pro
import asyncio
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


from typing import Any


class KuCoinAccount:
    """KuCoin hesap bağlantısı ve bakiye yönetimi."""

    def __init__(self, orders: Any = None):
        self.config = Config()
        self.orders = orders
        self.exchange: ccxt.async_support.kucoin | None = None
        self.futures_exchange: ccxt.async_support.kucoinfutures | None = None
        self.is_connected = False

        # WebSocket canlı bakiye (ccxt.pro)
        self.ws_exchange: ccxt.pro.kucoin | None = None
        self._ws_task: asyncio.Task | None = None
        self._ws_running = False
        self.live_balances: dict[str, dict] = {}  # {symbol: {free, used, total}}
        self.ws_last_update: str | None = None

    def connect(self) -> bool:
        """KuCoin API'ye bağlan."""
        try:
            creds = {
                "apiKey": self.config.API_KEY,
                "secret": self.config.API_SECRET,
                "password": self.config.API_PASSPHRASE,
                "sandbox": self.config.IS_SANDBOX,
            }
            self.exchange = ccxt.async_support.kucoin(dict(creds))
            # Futures teminat bakiyesi ayrı uç noktadan (kucoinfutures) gelir
            self.futures_exchange = ccxt.async_support.kucoinfutures(dict(creds))
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

            # KuCoin fonları farklı hesaplarda tutulur:
            #   spot exchange: 'trade' (spot), 'main' (funding), 'margin' (cross margin)
            #   kucoinfutures: futures teminat cüzdanı (USDT/USDC)
            # Hepsini çekip varlık bazında birleştiriyoruz.
            combined_total: dict[str, float] = {}
            combined_free: dict[str, float] = {}
            combined_used: dict[str, float] = {}
            asset_accounts: dict[str, set] = {}  # {symbol: {"spot","funding","margin","futures"}}

            # Etiket eşlemesi: ccxt type -> okunabilir hesap adı
            spot_accounts = {"trade": "spot", "main": "funding", "margin": "margin"}
            per_account: dict[str, dict] = {}

            def _accumulate(bal: dict, label: str):
                totals = bal.get("total", {}) or {}
                frees = bal.get("free", {}) or {}
                useds = bal.get("used", {}) or {}
                acc = per_account.setdefault(label, {})
                for sym, amount in totals.items():
                    amt = float(amount or 0.0)
                    combined_total[sym] = combined_total.get(sym, 0.0) + amt
                    if amt > 0:
                        asset_accounts.setdefault(sym, set()).add(label)
                        acc.setdefault(sym, {"free": 0.0, "used": 0.0, "total": 0.0})
                        acc[sym]["total"] += amt
                        acc[sym]["free"] += float(frees.get(sym, 0.0) or 0.0)
                        acc[sym]["used"] += float(useds.get(sym, 0.0) or 0.0)
                for sym, amount in frees.items():
                    combined_free[sym] = combined_free.get(sym, 0.0) + float(amount or 0.0)
                for sym, amount in useds.items():
                    combined_used[sym] = combined_used.get(sym, 0.0) + float(amount or 0.0)

            # Spot / funding / margin (aynı kucoin spot uç noktası)
            for account_type, label in spot_accounts.items():
                try:
                    bal = await self.exchange.fetch_balance({"type": account_type})
                    _accumulate(bal, label)
                except Exception as e:
                    logger.error(f"'{account_type}' hesabı bakiye hatası: {e}")
                    continue

            # Futures teminat cüzdanı (ayrı kucoinfutures uç noktası)
            if self.futures_exchange is not None:
                try:
                    fbal = await self.futures_exchange.fetch_balance()
                    _accumulate(fbal, "futures")
                except Exception as e:
                    logger.error(f"Futures hesabı bakiye hatası: {e}")

            # Varlık maliyetlerini hesapla (varsa)
            holding_costs = {}
            if self.orders:
                try:
                    holding_costs = await self.orders.get_holding_costs()
                except Exception as e:
                    logger.debug(f"Bakiye için maliyet hesaplama hatası: {e}")

            asset_list = []
            price_cache: dict[str, float] = {}  # Fiyatları bir kez hesapla
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
                price_cache[symbol] = price

                asset_value = round(total_amount * price, 2)

                # Ortalama maliyet, toplam maliyet ve PnL hesabı
                hc = holding_costs.get(symbol)
                if symbol == "USDT":
                    avg_cost = 1.0
                    total_cost = asset_value
                    unrealized_pnl = 0.0
                    pnl_percent = 0.0
                elif hc and hc.get("avg_cost", 0) > 0:
                    avg_cost = hc["avg_cost"]
                    total_cost = round(total_amount * avg_cost, 2)
                    unrealized_pnl = round(asset_value - total_cost, 2)
                    pnl_percent = round(((price - avg_cost) / avg_cost) * 100.0, 2)
                else:
                    avg_cost = None
                    total_cost = None
                    unrealized_pnl = None
                    pnl_percent = None

                asset_list.append({
                    "symbol": symbol,
                    "free": free_amount,
                    "used": used_amount,
                    "total": total_amount,
                    "price_usdt": price,
                    "usdt_value": asset_value,
                    "avg_cost": avg_cost,
                    "total_cost": total_cost,
                    "unrealized_pnl": unrealized_pnl,
                    "pnl_percent": pnl_percent,
                    "accounts": sorted(asset_accounts.get(symbol, set())),
                    "portfolio_share_percent": 0.0  # Sonraki adımda hesaplanacak
                })

            # Hesap-bazlı kırılım oluştur
            account_breakdown = []
            for label in ("spot", "funding", "margin", "futures"):
                assets = per_account.get(label)
                if not assets:
                    continue
                acc_assets = []
                acc_total_usdt = 0.0
                for sym, amt in assets.items():
                    if amt["total"] <= 0:
                        continue
                    # price_cache'dan fiyat al
                    price = price_cache.get(sym, 1.0 if sym == "USDT" else 0.0)
                    val = round(amt["total"] * price, 2)
                    acc_total_usdt += val
                    acc_assets.append({
                        "symbol": sym,
                        "free": amt["free"],
                        "used": amt["used"],
                        "total": amt["total"],
                        "price_usdt": price,
                        "usdt_value": val,
                    })
                if acc_assets:
                    acc_assets.sort(key=lambda x: x["usdt_value"], reverse=True)
                    account_breakdown.append({
                        "account": label,
                        "total_usdt": round(acc_total_usdt, 2),
                        "assets": acc_assets,
                    })

            # Portföy payı yüzdesini hesapla
            grand_total = sum(a["usdt_value"] for a in asset_list)
            if grand_total > 0:
                for a in asset_list:
                    a["portfolio_share_percent"] = round(a["usdt_value"] / grand_total * 100, 2)

            return AccountBalancesResponse(
                success=True,
                data={"balances": asset_list, "accounts": account_breakdown},
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
                    "total_by_account": {a["account"]: a["total_usdt"] for a in balances.data.get("accounts", [])},
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

    async def get_permissions(self) -> dict:
        """
        API anahtarının yetkilerini (Read/Trade/Withdrawal) denetler.

        MODULE_1_SPEC 3.1 Permission Audit:
        - Okuma (Read) ve İşlem (Trade) yetkileri doğrulanır.
        - Para Çekme (Withdrawal) yetkisi tespit edilirse güvenlik uyarısı üretilir.

        KuCoin `permission` alanı örn: "General,Futures,Spot,Margin"
        - General  -> Read (okuma)
        - Spot/Margin/Futures/Trade -> Trade (işlem)
        - Withdrawal/Transfer -> Para çekme (güvenlik riski)

        Returns:
            {
              "permissions": [...],       # normalize edilmiş liste: read, trade, ...
              "has_read": bool,
              "has_trade": bool,
              "has_withdraw": bool,
              "warning": str | None
            }
        """
        if not self.exchange:
            self.connect()
        if not self.exchange:
            return {
                "permissions": [],
                "has_read": False,
                "has_trade": False,
                "has_withdraw": False,
                "warning": "KuCoin API'ye bağlanılamadı",
            }

        try:
            response = await self.exchange.private_get_user_api_key()
            raw_perms = response.get("data", {}).get("permission", "") or ""
            perms_lower = [p.strip().lower() for p in raw_perms.split(",") if p.strip()]

            has_read = "general" in perms_lower
            has_trade = any(p in perms_lower for p in ("spot", "margin", "futures", "trade"))
            has_withdraw = any(p in perms_lower for p in ("withdrawal", "withdraw", "transfer"))

            normalized = []
            if has_read:
                normalized.append("read")
            if has_trade:
                normalized.append("trade")
            if has_withdraw:
                normalized.append("withdraw")

            warning = None
            if has_withdraw:
                warning = (
                    "⚠️ Güvenlik uyarısı: API anahtarınızda Para Çekme (Withdrawal) "
                    "yetkisi açık. Al-Sat botu için bu yetki gerekli değildir; "
                    "güvenlik için KuCoin panelinden kapatmanız önerilir."
                )
            elif not has_trade:
                warning = (
                    "⚠️ API anahtarınızda İşlem (Trade/Spot) yetkisi yok. "
                    "Emir gönderimi çalışmayacaktır."
                )

            return {
                "permissions": normalized,
                "raw_permission": raw_perms,
                "has_read": has_read,
                "has_trade": has_trade,
                "has_withdraw": has_withdraw,
                "warning": warning,
            }
        except Exception as e:
            logger.error(f"Yetki denetimi hatası: {e}")
            return {
                "permissions": [],
                "has_read": False,
                "has_trade": False,
                "has_withdraw": False,
                "warning": f"Yetki bilgisi alınamadı: {e}",
            }

    async def get_status(self) -> ConnectionStatusResponse:
        """
        Bağlantı durumu, gecikme (ms), sandbox modu ve API yetkilerini döndürür.
        MODULE_1_SPEC 3.1 & Bölüm 6: /api/v1/account/status
        """
        try:
            # 1. Kimlik bilgisi kontrolü
            if not self.config.validate_credentials():
                return ConnectionStatusResponse(
                    success=False,
                    data={"status": "HATALI_KEY"},
                    error="API kimlik bilgileri eksik (.env dosyasını kontrol edin).",
                    timestamp=timestamp()
                )

            # 2. Zaman senkronizasyonu & gecikme
            sync_ok, latency_ms, sync_msg = check_time_sync()
            if not sync_ok:
                return ConnectionStatusResponse(
                    success=False,
                    data={
                        "status": "BAGLANTI_KOPTU",
                        "is_sandbox": self.config.IS_SANDBOX,
                        "latency_ms": latency_ms,
                        "permissions": [],
                    },
                    error=sync_msg,
                    timestamp=timestamp()
                )

            # 3. Yetki denetimi
            perms = await self.get_permissions()

            return ConnectionStatusResponse(
                success=True,
                data={
                    "status": "CONNECTED",
                    "is_sandbox": self.config.IS_SANDBOX,
                    "latency_ms": latency_ms,
                    "permissions": perms["permissions"],
                    "has_read": perms["has_read"],
                    "has_trade": perms["has_trade"],
                    "has_withdraw": perms["has_withdraw"],
                    "warning": perms["warning"],
                },
                error=None,
                timestamp=timestamp()
            )
        except Exception as e:
            logger.error(f"Bağlantı durumu hatası: {e}")
            return ConnectionStatusResponse(
                success=False,
                data={"status": "HATA"},
                error=f"Bağlantı durumu alınamadı: {e}",
                timestamp=timestamp()
            )

    async def start_balance_stream(self) -> bool:
        """
        KuCoin Private WebSocket kanalına abone olup canlı bakiye
        güncellemelerini `self.live_balances` içine yazar.
        MODULE_1_SPEC 3.3: İlk REST çekimi sonrası WebSocket aboneliği.

        Auto-reconnect: GLOBAL_STANDARDS 4.1 gereği bağlantı koparsa
        5 saniyede bir yeniden denenir.
        """
        if self._ws_running:
            logger.info("WebSocket bakiye akışı zaten çalışıyor")
            return True

        if not self.config.validate_credentials():
            logger.error("WebSocket başlatılamadı: API kimlik bilgileri eksik")
            return False

        self.ws_exchange = ccxt.pro.kucoin(
            {
                "apiKey": self.config.API_KEY,
                "secret": self.config.API_SECRET,
                "password": self.config.API_PASSPHRASE,
                "sandbox": self.config.IS_SANDBOX,
            }
        )
        self._ws_running = True
        self._ws_task = asyncio.create_task(self._balance_stream_loop())
        logger.info("✅ WebSocket canlı bakiye akışı başlatıldı")
        return True

    async def _balance_stream_loop(self) -> None:
        """WebSocket bakiye dinleme döngüsü (auto-reconnect'li)."""
        while self._ws_running:
            try:
                balance = await self.ws_exchange.watch_balance()
                total = balance.get("total", {})
                free = balance.get("free", {})
                used = balance.get("used", {})
                for symbol, amount in total.items():
                    if amount is None:
                        continue
                    self.live_balances[symbol] = {
                        "free": float(free.get(symbol, 0.0) or 0.0),
                        "used": float(used.get(symbol, 0.0) or 0.0),
                        "total": float(amount or 0.0),
                    }
                self.ws_last_update = timestamp()
                logger.info("🔄 Canlı bakiye güncellendi (WebSocket)")
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._ws_running:
                    break
                logger.error(f"WebSocket bakiye hatası: {e}. 5 sn sonra yeniden denenecek.")
                await asyncio.sleep(5)  # GLOBAL_STANDARDS 4.1: auto-reconnect

    async def stop_balance_stream(self) -> None:
        """WebSocket bakiye akışını durdur ve kaynakları serbest bırak."""
        self._ws_running = False
        if self._ws_task is not None:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except (asyncio.CancelledError, Exception):
                pass
            self._ws_task = None
        if self.ws_exchange is not None:
            try:
                await self.ws_exchange.close()
            except Exception as e:
                logger.error(f"WebSocket exchange kapatma hatası: {e}")
            finally:
                self.ws_exchange = None
        logger.info("⏹️ WebSocket canlı bakiye akışı durduruldu")

    async def close(self) -> None:
        """
        ccxt async exchange kaynaklarını serbest bırak.
        ccxt.async_support, aiohttp client session'ının açıkça kapatılmasını
        gerektirir; aksi halde "Unclosed client session" uyarısı ve kaynak
        sızıntısı oluşur.
        """
        # Önce WebSocket akışını durdur
        await self.stop_balance_stream()

        if self.exchange is not None:
            try:
                await self.exchange.close()
            except Exception as e:
                logger.error(f"Exchange kapatma hatası: {e}")
            finally:
                self.exchange = None
                self.is_connected = False
        if self.futures_exchange is not None:
            try:
                await self.futures_exchange.close()
            except Exception as e:
                logger.error(f"Futures exchange kapatma hatası: {e}")
            finally:
                self.futures_exchange = None
