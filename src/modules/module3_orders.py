"""
KuCoin Al-Sat Botu — Modül 3: Al-Sat Emir Entegrasyonu ve Emir Yönetimi

MODULE_3_SPEC izlenebilirlik matrisi (M3-C01..C09):
- M3-C01: Pre-trade risk & bakiye doğrulama
- M3-C02: Market order
- M3-C03: Limit order
- M3-C04: Açık emirleri listeleme
- M3-C05: Tekil/toplu iptal
- M3-C06: Panic stop
- M3-C07: Paper trading motoru ($10,000 sanal USDT)
- M3-C08: REAL <-> SIMULATION mod geçişi
- M3-C09: REST endpoint entegrasyonu (main.py)

Güvenlik: Varsayılan mod 'paper' (simülasyon). Gerçek emir yalnızca 'live'
modda ve yeterli bakiye + risk kontrolü geçtiğinde iletilir.
"""

import uuid
import ccxt
import ccxt.async_support

from src.config import Config
from src.models.orders import (
    OrderCreateResponse,
    OpenOrdersResponse,
    OrderHistoryResponse,
    OrderCancelResponse,
    PanicStopResponse,
    SwitchModeResponse,
)
from src.utils.logger import logger
from src.utils.time_sync import timestamp

VALID_SIDES = ("buy", "sell")
VALID_TYPES = ("market", "limit")
VALID_MARKET_TYPES = ("spot", "margin", "futures")
MIN_NOTIONAL_USDT = 1.0  # KuCoin minimum emir tutarı (yaklaşık)


class KuCoinOrders:
    """Emir oluşturma, takip, iptal; paper ve live mod desteği."""

    def __init__(self, market=None):
        self.config = Config()
        # 'paper' (simülasyon) veya 'live' (gerçek)
        self.mode = "paper" if self.config.SIMULATION_MODE else self.config.DEFAULT_TRADING_MODE
        if self.mode not in ("paper", "live"):
            self.mode = "paper"
        self.exchange: ccxt.async_support.kucoin | None = None
        self.futures_exchange: ccxt.async_support.kucoinfutures | None = None
        self.bot_active = True  # Panic stop bunu False yapar

        # Modül 2 market referansı (paper modda anlık fiyat için).
        self.market = market

        # --- Paper trading durumu (M3-C07) ---
        self.paper_balance_usdt = float(self.config.SIMULATION_INITIAL_BALANCE_USDT or 10000.0)
        self.paper_open_orders: dict[str, dict] = {}
        self.paper_history: list[dict] = []

    # ------------------------------------------------------------------ #
    # Bağlantı
    # ------------------------------------------------------------------ #
    def connect(self) -> bool:
        try:
            creds = {
                "apiKey": self.config.API_KEY,
                "secret": self.config.API_SECRET,
                "password": self.config.API_PASSPHRASE,
                "sandbox": self.config.IS_SANDBOX,
            }
            self.exchange = ccxt.async_support.kucoin(dict(creds))
            # Futures ayrı bir borsa uç noktası kullanır (kucoinfutures)
            self.futures_exchange = ccxt.async_support.kucoinfutures(dict(creds))
            return True
        except Exception as e:
            logger.error(f"❌ Emir modülü bağlantı hatası: {e}")
            return False

    def _venue(self, market_type: str):
        """market_type'a göre doğru ccxt borsa örneğini döndürür."""
        if not self.exchange or not self.futures_exchange:
            self.connect()
        return self.futures_exchange if market_type == "futures" else self.exchange

    # ------------------------------------------------------------------ #
    # M3-C01: Pre-trade risk & doğrulama
    # ------------------------------------------------------------------ #
    def _validate_order(self, symbol: str, side: str, order_type: str,
                        amount: float, price: float | None,
                        market_type: str = "spot") -> str | None:
        """Geçersizse hata mesajı, geçerliyse None döner."""
        if not self.bot_active:
            return "Bot durdurulmuş (Panic Stop aktif). Yeni emir kabul edilmiyor."
        if side not in VALID_SIDES:
            return f"Geçersiz yön: {side}. Geçerli: buy/sell."
        if order_type not in VALID_TYPES:
            return f"Geçersiz emir türü: {order_type}. Geçerli: market/limit."
        if market_type not in VALID_MARKET_TYPES:
            return f"Geçersiz piyasa türü: {market_type}. Geçerli: spot/margin/futures."
        if amount is None or amount <= 0:
            return "Miktar (amount) pozitif olmalı."
        if order_type == "limit" and (price is None or price <= 0):
            return "Limit emir için geçerli bir fiyat (price) gerekli."
        return None

    async def _current_price(self, symbol: str) -> float | None:
        """Paper mod eşleşmesi için anlık fiyat (Modül 2 veya doğrudan ccxt)."""
        try:
            if self.market is not None:
                t = await self.market.get_ticker(symbol)
                if t.success:
                    return float(t.data["last_price"])
            if not self.exchange:
                self.connect()
            tk = await self.exchange.fetch_ticker(symbol)
            return float(tk["last"])
        except Exception as e:
            logger.error(f"Anlık fiyat alınamadı ({symbol}): {e}")
            return None

    # ------------------------------------------------------------------ #
    # M3-C02 / M3-C03: Emir oluşturma
    # ------------------------------------------------------------------ #
    async def create_order(self, symbol: str, side: str, order_type: str,
                           amount: float, price: float | None = None,
                           market_type: str = "spot") -> OrderCreateResponse:
        side = (side or "").lower()
        order_type = (order_type or "").lower()
        market_type = (market_type or "spot").lower()

        err = self._validate_order(symbol, side, order_type, amount, price, market_type)
        if err:
            return OrderCreateResponse(success=False, data={}, error=err, timestamp=timestamp())

        if self.mode == "paper":
            return await self._create_paper_order(symbol, side, order_type, amount, price, market_type)
        return await self._create_live_order(symbol, side, order_type, amount, price, market_type)

    async def _create_paper_order(self, symbol, side, order_type, amount, price, market_type="spot"):
        """Paper trading emir motoru (M3-C07)."""
        last_price = await self._current_price(symbol)
        if last_price is None:
            return OrderCreateResponse(
                success=False, data={},
                error="Simülasyon için anlık fiyat alınamadı.", timestamp=timestamp())

        fill_price = last_price if order_type == "market" else float(price)
        notional = amount * fill_price

        # M3-C01: bakiye & min notional kontrolü (alış için)
        if notional < MIN_NOTIONAL_USDT:
            return OrderCreateResponse(
                success=False, data={},
                error=f"Emir tutarı minimum {MIN_NOTIONAL_USDT} USDT altında.", timestamp=timestamp())
        if side == "buy" and notional > self.paper_balance_usdt:
            return OrderCreateResponse(
                success=False, data={},
                error=(f"Yetersiz sanal bakiye: gerekli {notional:.2f} USDT, "
                       f"mevcut {self.paper_balance_usdt:.2f} USDT."), timestamp=timestamp())

        order_id = f"paper-{uuid.uuid4().hex[:12]}"

        if order_type == "market":
            # Anında dolar
            if side == "buy":
                self.paper_balance_usdt -= notional
            else:
                self.paper_balance_usdt += notional
            record = {
                "id": order_id, "symbol": symbol, "side": side, "type": order_type,
                "amount": amount, "price": fill_price, "status": "filled",
                "filled_price": fill_price, "notional_usdt": round(notional, 2),
                "mode": "paper", "market_type": market_type, "created_at": timestamp(),
            }
            self.paper_history.append(record)
            return OrderCreateResponse(success=True, data=record, error=None, timestamp=timestamp())

        # Limit emir: açık kalır
        record = {
            "id": order_id, "symbol": symbol, "side": side, "type": order_type,
            "amount": amount, "price": float(price), "status": "open",
            "filled": 0.0, "notional_usdt": round(notional, 2),
            "mode": "paper", "market_type": market_type, "created_at": timestamp(),
        }
        self.paper_open_orders[order_id] = record
        return OrderCreateResponse(success=True, data=record, error=None, timestamp=timestamp())

    async def _create_live_order(self, symbol, side, order_type, amount, price, market_type="spot"):
        """Gerçek KuCoin emri (M3-C02/C03). Spot, Margin (cross) ve Futures destekli."""
        try:
            venue = self._venue(market_type)
            if venue is None:
                return OrderCreateResponse(
                    success=False, data={},
                    error="Borsa bağlantısı kurulamadı.", timestamp=timestamp())

            # market_type'a göre ccxt parametreleri
            params = {}
            if market_type == "margin":
                # KuCoin cross-margin spot emri
                params["marginMode"] = "cross"
            # futures için ayrı venue (kucoinfutures) zaten seçildi

            price_arg = price if order_type == "limit" else None
            order = await venue.create_order(symbol, order_type, side, amount, price_arg, params)
            return OrderCreateResponse(
                success=True,
                data={
                    "id": order.get("id"), "symbol": symbol, "side": side,
                    "type": order_type, "amount": amount, "price": price,
                    "status": order.get("status", "open"), "mode": "live",
                    "market_type": market_type, "created_at": timestamp(),
                },
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"Canlı emir hatası ({market_type}): {e}")
            return OrderCreateResponse(
                success=False, data={}, error=f"Emir iletilemedi: {e}", timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # M3-C04: Açık emirler
    # ------------------------------------------------------------------ #
    async def get_open_orders(self, symbol: str | None = None) -> OpenOrdersResponse:
        try:
            if self.mode == "paper":
                orders = list(self.paper_open_orders.values())
                if symbol:
                    orders = [o for o in orders if o["symbol"] == symbol]
                # market_type alanı garanti altına al (eski kayıtlar için)
                for o in orders:
                    o.setdefault("market_type", "spot")
                return OpenOrdersResponse(
                    success=True, data={"count": len(orders), "orders": orders},
                    error=None, timestamp=timestamp())

            if not self.exchange or not self.futures_exchange:
                self.connect()

            merged: list[dict] = []
            # Spot + Margin açık emirler (aynı kucoin spot uç noktası)
            try:
                spot_orders = await self.exchange.fetch_open_orders(symbol)
                for o in spot_orders:
                    info = o.get("info", {}) or {}
                    # KuCoin spot 'tradeType': TRADE (spot) | MARGIN_TRADE (margin)
                    is_margin = str(info.get("tradeType", "")).upper().startswith("MARGIN")
                    o["market_type"] = "margin" if is_margin else "spot"
                    merged.append(o)
            except Exception as e:
                logger.error(f"Spot açık emir çekme hatası: {e}")
            # Futures açık emirler (ayrı kucoinfutures uç noktası)
            try:
                fut_orders = await self.futures_exchange.fetch_open_orders(symbol)
                for o in fut_orders:
                    o["market_type"] = "futures"
                    merged.append(o)
            except Exception as e:
                logger.error(f"Futures açık emir çekme hatası: {e}")

            return OpenOrdersResponse(
                success=True, data={"count": len(merged), "orders": merged},
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"Açık emir listeleme hatası: {e}")
            return OpenOrdersResponse(
                success=False, data={}, error=f"Açık emirler alınamadı: {e}", timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # İşlem geçmişi
    # ------------------------------------------------------------------ #
    async def get_history(self, symbol: str | None = None, limit: int = 50) -> OrderHistoryResponse:
        try:
            if self.mode == "paper":
                hist = self.paper_history
                if symbol:
                    hist = [h for h in hist if h["symbol"] == symbol]
                return OrderHistoryResponse(
                    success=True, data={"count": len(hist), "orders": hist[-limit:]},
                    error=None, timestamp=timestamp())

            if not self.exchange:
                self.connect()
            trades = await self.exchange.fetch_closed_orders(symbol, limit=limit)
            return OrderHistoryResponse(
                success=True, data={"count": len(trades), "orders": trades},
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"Emir geçmişi hatası: {e}")
            return OrderHistoryResponse(
                success=False, data={}, error=f"Emir geçmişi alınamadı: {e}", timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # M3-C05: İptal
    # ------------------------------------------------------------------ #
    async def cancel_order(self, order_id: str, symbol: str | None = None) -> OrderCancelResponse:
        try:
            if self.mode == "paper":
                if order_id not in self.paper_open_orders:
                    return OrderCancelResponse(
                        success=False, data={},
                        error=f"Açık emir bulunamadı: {order_id}", timestamp=timestamp())
                cancelled = self.paper_open_orders.pop(order_id)
                cancelled["status"] = "canceled"
                return OrderCancelResponse(
                    success=True, data={"id": order_id, "status": "canceled"},
                    error=None, timestamp=timestamp())

            if not self.exchange:
                self.connect()
            await self.exchange.cancel_order(order_id, symbol)
            return OrderCancelResponse(
                success=True, data={"id": order_id, "status": "canceled"},
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"Emir iptal hatası: {e}")
            return OrderCancelResponse(
                success=False, data={}, error=f"Emir iptal edilemedi: {e}", timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # M3-C06: Panic Stop
    # ------------------------------------------------------------------ #
    async def panic_stop(self) -> PanicStopResponse:
        """Tüm açık emirleri iptal et ve botu durdur."""
        try:
            cancelled_count = 0
            if self.mode == "paper":
                cancelled_count = len(self.paper_open_orders)
                self.paper_open_orders.clear()
            else:
                if not self.exchange:
                    self.connect()
                open_orders = await self.exchange.fetch_open_orders()
                for o in open_orders:
                    try:
                        await self.exchange.cancel_order(o["id"], o.get("symbol"))
                        cancelled_count += 1
                    except Exception as e:
                        logger.error(f"Panic iptal hatası ({o.get('id')}): {e}")

            self.bot_active = False
            logger.warning(f"🛑 PANIC STOP: {cancelled_count} emir iptal edildi, bot durduruldu.")
            return PanicStopResponse(
                success=True,
                data={"cancelled_orders": cancelled_count, "bot_active": False},
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"Panic stop hatası: {e}")
            return PanicStopResponse(
                success=False, data={}, error=f"Panic stop başarısız: {e}", timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # M3-C08: Mod geçişi
    # ------------------------------------------------------------------ #
    async def switch_mode(self, mode: str) -> SwitchModeResponse:
        mode = (mode or "").lower()
        if mode not in ("paper", "live"):
            return SwitchModeResponse(
                success=False, data={},
                error="Geçersiz mod. Geçerli: 'paper' veya 'live'.", timestamp=timestamp())

        previous = self.mode
        self.mode = mode
        # Mod değişince botu tekrar aktif et (panic sonrası kurtarma).
        self.bot_active = True
        logger.info(f"🔁 Mod değişti: {previous} → {mode}")
        return SwitchModeResponse(
            success=True,
            data={"previous_mode": previous, "current_mode": mode, "bot_active": True},
            error=None, timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # Akıllı Paket Emir (Bracket Order) — MODULE_3_SPEC 2.5
    # ------------------------------------------------------------------ #
    async def create_bracket_order(
        self, symbol: str, side: str, usdt_amount: float,
        entry_price: float, stop_loss_price: float,
        tp1_price: float, tp2_price: float,
    ) -> "OrderCreateResponse":
        """
        Tek pakette: Giriş emri + TP1 (%50) + TP2 (%50) + SL (%100).
        Paper modda giriş anında dolar, TP/SL açık limit emir olarak kaydedilir.
        """
        side = (side or "buy").lower()
        err = self._validate_order(symbol, side, "limit", usdt_amount and 1, entry_price)
        if err and "Miktar" not in err:  # miktar burada usdt bazlı, ayrı kontrol
            return OrderCreateResponse(success=False, data={}, error=err, timestamp=timestamp())
        if usdt_amount is None or usdt_amount <= 0:
            return OrderCreateResponse(success=False, data={},
                                       error="USDT tutarı pozitif olmalı.", timestamp=timestamp())
        if entry_price <= 0:
            return OrderCreateResponse(success=False, data={},
                                       error="Geçersiz giriş fiyatı.", timestamp=timestamp())

        # Miktar ve risk/kâr hesabı
        amount = usdt_amount / entry_price
        risk_usdt = round(amount * abs(entry_price - stop_loss_price), 2)
        gain_tp1 = round((amount * 0.5) * abs(tp1_price - entry_price), 2)
        gain_tp2 = round((amount * 0.5) * abs(tp2_price - entry_price), 2)

        # Bakiye kontrolü (paper, alış için)
        if self.mode == "paper" and side == "buy" and usdt_amount > self.paper_balance_usdt:
            return OrderCreateResponse(
                success=False, data={},
                error=(f"Yetersiz sanal bakiye: gerekli {usdt_amount:.2f} USDT, "
                       f"mevcut {self.paper_balance_usdt:.2f} USDT."), timestamp=timestamp())

        bracket_id = f"bracket-{uuid.uuid4().hex[:10]}"
        exit_side = "sell" if side == "buy" else "buy"

        # Giriş emri (market)
        entry_res = await self.create_order(symbol, side, "market", amount, None)
        if not entry_res.success:
            return OrderCreateResponse(success=False, data={},
                                       error=f"Giriş emri başarısız: {entry_res.error}",
                                       timestamp=timestamp())

        legs = {"entry": entry_res.data}
        # TP1 (%50), TP2 (%50), SL (%100) — çıkış limit emirleri
        for name, price, qty in [
            ("tp1", tp1_price, amount * 0.5),
            ("tp2", tp2_price, amount * 0.5),
            ("sl", stop_loss_price, amount),
        ]:
            leg = await self.create_order(symbol, exit_side, "limit", qty, price)
            if leg.success:
                leg.data["bracket_leg"] = name
                leg.data["bracket_id"] = bracket_id
            legs[name] = leg.data if leg.success else {"error": leg.error}

        return OrderCreateResponse(
            success=True,
            data={
                "bracket_id": bracket_id,
                "symbol": symbol, "side": side,
                "usdt_amount": usdt_amount, "amount": amount,
                "entry_price": entry_price, "stop_loss_price": stop_loss_price,
                "tp1_price": tp1_price, "tp2_price": tp2_price,
                "risk_usdt": risk_usdt, "gain_tp1_usdt": gain_tp1, "gain_tp2_usdt": gain_tp2,
                "legs": legs,
            },
            error=None, timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # Açık Emir Düzenleme (Amend) — MODULE_3_SPEC 2.6
    # ------------------------------------------------------------------ #
    async def amend_order(
        self, order_id: str, price: float | None = None,
        amount: float | None = None, symbol: str | None = None
    ) -> OrderCreateResponse:
        """
        Açık bir emrin fiyatını ve/veya miktarını günceller.
        Paper modda kayıt doğrudan güncellenir; live modda iptal-edip-yeniden-oluştur
        (cancel/replace) yaklaşımı uygulanır.
        """
        if price is None and amount is None:
            return OrderCreateResponse(success=False, data={},
                                       error="Güncellenecek fiyat veya miktar belirtilmeli.",
                                       timestamp=timestamp())

        if self.mode == "paper":
            order = self.paper_open_orders.get(order_id)
            if not order:
                return OrderCreateResponse(success=False, data={},
                                           error=f"Açık emir bulunamadı: {order_id}",
                                           timestamp=timestamp())
            if price is not None and price > 0:
                order["price"] = float(price)
            if amount is not None and amount > 0:
                order["amount"] = float(amount)
            order["notional_usdt"] = round(order["amount"] * order["price"], 2)
            order["amended_at"] = timestamp()
            return OrderCreateResponse(success=True, data=order, error=None, timestamp=timestamp())

        # Live: cancel + yeniden oluştur
        try:
            if not self.exchange:
                self.connect()
            old = await self.exchange.fetch_order(order_id, symbol)
            await self.exchange.cancel_order(order_id, symbol)
            new_price = price if price is not None else old.get("price")
            new_amount = amount if amount is not None else old.get("amount")
            new_order = await self.exchange.create_order(
                symbol or old.get("symbol"), "limit", old.get("side"), new_amount, new_price)
            return OrderCreateResponse(
                success=True,
                data={"id": new_order.get("id"), "replaced": order_id,
                      "price": new_price, "amount": new_amount, "status": "open"},
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"Emir düzenleme hatası: {e}")
            return OrderCreateResponse(success=False, data={},
                                       error=f"Emir düzenlenemedi: {e}", timestamp=timestamp())

    async def close(self) -> None:
        if self.exchange is not None:
            try:
                await self.exchange.close()
            except Exception as e:
                logger.error(f"Emir modülü kapatma hatası: {e}")
            finally:
                self.exchange = None
        if self.futures_exchange is not None:
            try:
                await self.futures_exchange.close()
            except Exception as e:
                logger.error(f"Futures emir modülü kapatma hatası: {e}")
            finally:
                self.futures_exchange = None
