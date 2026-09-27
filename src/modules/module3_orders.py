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
from datetime import datetime, timezone
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
    PnLReportResponse,
)
from src.utils.logger import logger
from src.utils.time_sync import timestamp

VALID_SIDES = ("buy", "sell")
VALID_TYPES = ("market", "limit", "stop", "stop_market", "stop_loss")
VALID_MARKET_TYPES = ("spot", "margin", "futures")
MIN_NOTIONAL_USDT = 1.0  # KuCoin minimum emir tutarı (yaklaşık)


class KuCoinOrders:
    """Emir oluşturma, takip, iptal; paper ve live mod desteği."""

    def __init__(self, market=None, credentials: dict | None = None):
        self.config = Config()
        # İsteğe bağlı kullanıcı-bazlı kimlik bilgileri (request-scoped).
        # Verilmezse .env/Config kullanılır (geriye uyumlu).
        self.credentials = credentials
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
        self.paper_positions: dict[str, dict] = {}


    # ------------------------------------------------------------------ #
    # Bağlantı
    # ------------------------------------------------------------------ #
    def connect(self) -> bool:
        try:
            c = self.credentials or {}
            creds = {
                "apiKey": c.get("api_key") or self.config.API_KEY,
                "secret": c.get("api_secret") or self.config.API_SECRET,
                "password": c.get("api_passphrase") or self.config.API_PASSPHRASE,
                "sandbox": c.get("is_sandbox", self.config.IS_SANDBOX),
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

    async def _normalize_symbol(self, symbol: str, market_type: str) -> str:
        """
        Sembolü market_type'a uygun ccxt formatına çevirir.

        KuCoin Futures perpetual sözleşmeleri `BASE/QUOTE:SETTLE` biçimindedir
        (ör. spot `PEPE/USDT` -> futures `PEPE/USDT:USDT`). Spot/margin için
        sembol olduğu gibi kullanılır. Dönüşüm sonrası borsa piyasalarında
        geçerlilik doğrulanır.
        """
        if market_type != "futures":
            return symbol
        # Zaten settle eki varsa dokunma
        if ":" in symbol:
            return symbol
        base_quote = symbol
        quote = symbol.split("/")[-1] if "/" in symbol else "USDT"
        candidate = f"{base_quote}:{quote}"
        # Geçerlilik kontrolü (markets yüklüyse)
        try:
            ex = self._venue("futures")
            if ex is not None:
                if not ex.markets:
                    await ex.load_markets()
                if candidate in ex.markets:
                    return candidate
                # USDT-margined perpetual varsayılanı yoksa hata net dönsün
        except Exception as e:
            logger.error(f"Futures sembol doğrulama hatası ({symbol}): {e}")
        return candidate

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
            return f"Geçersiz emir türü: {order_type}."
        if market_type not in VALID_MARKET_TYPES:
            return f"Geçersiz piyasa türü: {market_type}. Geçerli: spot/margin/futures."
        if amount is None or amount <= 0:
            return "Miktar (amount) pozitif olmalı."
        if order_type in ("limit", "stop_limit") and (price is None or price <= 0):
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
                           market_type: str = "spot",
                           margin_mode: str = "cross", leverage: float | None = None,
                           entry_price: float | None = None,
                           stop_loss_price: float | None = None,
                           is_stop: bool = False, reduce_only: bool = False) -> OrderCreateResponse:
        side = (side or "").lower()
        order_type = (order_type or "").lower()
        market_type = (market_type or "spot").lower()

        validate_price = price if price is not None else (stop_loss_price if is_stop else None)
        err = self._validate_order(symbol, side, order_type, amount, validate_price, market_type)
        if err:
            return OrderCreateResponse(success=False, data={}, error=err, timestamp=timestamp())

        if self.mode == "paper":
            return await self._create_paper_order(
                symbol, side, order_type, amount, price, market_type,
                margin_mode=margin_mode, leverage=leverage,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                is_stop=is_stop, reduce_only=reduce_only,
            )
        return await self._create_live_order(
            symbol, side, order_type, amount, price,
            market_type, margin_mode, leverage,
            stop_loss_price=stop_loss_price, is_stop=is_stop, reduce_only=reduce_only,
        )

    async def _create_paper_order(self, symbol, side, order_type, amount, price, market_type="spot",
                                  margin_mode="cross", leverage=None,
                                  entry_price=None, stop_loss_price=None,
                                  is_stop=False, reduce_only=False):
        """Paper trading emir motoru (M3-C07)."""
        last_price = await self._current_price(symbol)
        if last_price is None:
            return OrderCreateResponse(
                success=False, data={},
                error="Simülasyon için anlık fiyat alınamadı.", timestamp=timestamp())

        fill_price = last_price if order_type == "market" else float(price or stop_loss_price or last_price)
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

        # Stop emir: açık stop emri olarak bekler (tetiklenene kadar)
        if is_stop:
            record = {
                "id": order_id, "symbol": symbol, "side": side, "type": "stop_market" if order_type == "market" else "stop_limit",
                "amount": amount, "price": float(stop_loss_price or price or fill_price), "status": "open",
                "filled": 0.0, "notional_usdt": round(notional, 2),
                "mode": "paper", "market_type": market_type,
                "margin_mode": margin_mode if market_type in ("margin", "futures") else None,
                "leverage": leverage if market_type == "futures" else (5.0 if market_type == "margin" else None),
                "entry_price": float(entry_price) if entry_price is not None else None,
                "stop_loss_price": float(stop_loss_price) if stop_loss_price is not None else float(price or fill_price),
                "bracket_leg": "sl",
                "created_at": timestamp(),
            }
            self.paper_open_orders[order_id] = record
            return OrderCreateResponse(success=True, data=record, error=None, timestamp=timestamp())

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
                "mode": "paper", "market_type": market_type,
                "margin_mode": margin_mode if market_type in ("margin", "futures") else None,
                "leverage": leverage if market_type == "futures" else (5.0 if market_type == "margin" else None),
                "entry_price": fill_price,
                "stop_loss_price": float(stop_loss_price) if stop_loss_price is not None else None,
                "created_at": timestamp(),
            }
            self.paper_history.append(record)
            return OrderCreateResponse(success=True, data=record, error=None, timestamp=timestamp())

        # Limit emir: açık kalır
        record = {
            "id": order_id, "symbol": symbol, "side": side, "type": order_type,
            "amount": amount, "price": float(price), "status": "open",
            "filled": 0.0, "notional_usdt": round(notional, 2),
            "mode": "paper", "market_type": market_type,
            "margin_mode": margin_mode if market_type in ("margin", "futures") else None,
            "leverage": leverage if market_type == "futures" else (5.0 if market_type == "margin" else None),
            "entry_price": float(entry_price) if entry_price is not None else (float(price) if side == "buy" else None),
            "stop_loss_price": float(stop_loss_price) if stop_loss_price is not None else None,
            "created_at": timestamp(),
        }
        self.paper_open_orders[order_id] = record
        return OrderCreateResponse(success=True, data=record, error=None, timestamp=timestamp())

    async def _create_live_order(self, symbol, side, order_type, amount, price,
                                 market_type="spot", margin_mode="cross", leverage=None,
                                 stop_loss_price=None, is_stop=False, reduce_only=False):
        """Gerçek KuCoin emri (M3-C02/C03). Spot, Margin (cross) ve Futures destekli.

        Futures'ta KuCoin, emrin margin modunun (cross/isolated) sembolün hesapta
        ayarlı moduyla eşleşmesini ister (aksi halde 330005). marginMode gönderilir;
        330005 alınırsa diğer modla bir kez daha denenir.
        """
        try:
            venue = self._venue(market_type)
            if venue is None:
                return OrderCreateResponse(
                    success=False, data={},
                    error="Borsa bağlantısı kurulamadı.", timestamp=timestamp())

            # Futures sembolünü BASE/QUOTE:SETTLE biçimine çevir (ör. PEPE/USDT -> PEPE/USDT:USDT)
            venue_symbol = await self._normalize_symbol(symbol, market_type)

            # KuCoin Futures kontrat bazlı integer lot kontrolü
            if market_type == "futures":
                amount_arg = max(1, int(round(amount)))
            else:
                amount_arg = amount

            # Stop-market emirlerde limit price None olmalıdır
            price_arg = price if (order_type == "limit" and not is_stop) else None
            effective_type = "market" if (is_stop and order_type == "market") else order_type

            def _params(mm: str) -> dict:
                p = {}
                if market_type == "margin":
                    p["marginMode"] = "cross"
                elif market_type == "futures":
                    p["marginMode"] = mm  # cross | isolated
                    if leverage is not None:
                        try:
                            lev_f = float(leverage)
                            p["leverage"] = int(lev_f) if lev_f.is_integer() else lev_f
                        except (ValueError, TypeError):
                            p["leverage"] = leverage
                    if reduce_only:
                        p["reduceOnly"] = True
                    if is_stop or stop_loss_price is not None:
                        stop_p = stop_loss_price if stop_loss_price is not None else price
                        if stop_p is not None:
                            try:
                                stop_p = float(stop_p)
                            except (ValueError, TypeError):
                                pass
                        p["stop"] = "down" if side == "sell" else "up"
                        p["stopPrice"] = stop_p
                        p["triggerPrice"] = stop_p
                        p["stopPriceType"] = "MP"
                        p["reduceOnly"] = True
                        p["closeOrder"] = True
                elif market_type == "spot":
                    if is_stop or (stop_loss_price is not None and order_type in ("market", "stop", "stop_market")):
                        stop_p = stop_loss_price if stop_loss_price is not None else price
                        if stop_p is not None:
                            try:
                                stop_p = float(stop_p)
                            except (ValueError, TypeError):
                                pass
                        p["stop"] = "loss"
                        p["stopPrice"] = stop_p
                        p["triggerPrice"] = stop_p
                        p["stopLossPrice"] = stop_p
                return p

            # Futures için önceden borsa üzerinde marjin modu ve kaldıraç ayarla
            if market_type == "futures":
                if leverage is not None:
                    try:
                        lev_int = int(round(float(leverage)))
                        if hasattr(venue, "set_leverage"):
                            await venue.set_leverage(lev_int, venue_symbol)
                            logger.info(f"Futures kaldıraç ayarlandı: {venue_symbol} -> {lev_int}x")
                    except Exception as lev_e:
                        logger.debug(f"KuCoin set_leverage uyarısı ({venue_symbol} -> {leverage}x): {lev_e}")

                if margin_mode and hasattr(venue, "set_margin_mode"):
                    try:
                        mm_clean = margin_mode.lower()
                        if mm_clean in ("cross", "isolated"):
                            await venue.set_margin_mode(mm_clean, venue_symbol)
                            logger.info(f"Futures marjin modu ayarlandı: {venue_symbol} -> {mm_clean.upper()}")
                    except Exception as mm_e:
                        logger.debug(f"KuCoin set_margin_mode uyarısı ({venue_symbol} -> {margin_mode}): {mm_e}")

            used_mode = margin_mode
            warning_msg = None
            try:
                order = await venue.create_order(
                    venue_symbol, effective_type, side, amount_arg, price_arg, _params(margin_mode))
            except Exception as e:
                # 330005: margin modu uyuşmazlığı → diğer modla bir kez daha dene
                if market_type == "futures" and "330005" in str(e):
                    alt = "isolated" if margin_mode == "cross" else "cross"
                    logger.warning(f"Futures margin modu borsa ayarıyla uyuşmadı ({margin_mode}), {alt} deneniyor.")
                    order = await venue.create_order(
                        venue_symbol, effective_type, side, amount_arg, price_arg, _params(alt))
                    used_mode = alt
                    warning_msg = (
                        f"KuCoin hesabınızda bu sembol önceden {alt.upper()} modunda ayarlı olduğu için "
                        f"emir {alt.upper()} modunda açıldı. Mod değiştirmek için KuCoin'de açık emir veya pozisyon bulunmamalıdır."
                    )
                else:
                    raise
            return OrderCreateResponse(
                success=True,
                data={
                    "id": order.get("id"), "symbol": symbol, "side": side,
                    "type": effective_type, "amount": amount_arg, "price": price or stop_loss_price,
                    "status": order.get("status", "open"), "mode": "live",
                    "market_type": market_type, "venue_symbol": venue_symbol,
                    "margin_mode": used_mode if market_type == "futures" else None,
                    "leverage": leverage if market_type == "futures" else None,
                    "stop_loss_price": stop_loss_price if is_stop else None,
                    "is_stop": is_stop,
                    "warning": warning_msg,
                    "created_at": timestamp(),
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
                await self._attach_current_prices(orders)
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
                fut_symbol = await self._normalize_symbol(symbol, "futures") if symbol else None
                fut_orders = await self.futures_exchange.fetch_open_orders(fut_symbol)
                for o in fut_orders:
                    o["market_type"] = "futures"
                    merged.append(o)
            except Exception as e:
                logger.error(f"Futures açık emir çekme hatası: {e}")

            # Spot stop/tetik emirleri çek
            try:
                spot_stops_parsed = []
                try:
                    spot_stops_parsed = await self.exchange.fetch_open_orders(symbol, params={"trigger": True})
                except Exception as ex_trig_spot:
                    logger.debug(f"Spot CCXT trigger fetch: {ex_trig_spot}")

                if spot_stops_parsed:
                    for o in spot_stops_parsed:
                        oid = o.get("id")
                        if any(m.get("id") == oid for m in merged):
                            continue
                        sl_val = float(o.get("stopPrice") or 0.0)
                        o["market_type"] = "spot"
                        o["is_stop"] = True
                        o["bracket_leg"] = "sl"
                        if sl_val > 0:
                            o["stop_loss_price"] = sl_val
                        merged.append(o)
                else:
                    spot_id = symbol.replace("/", "-") if symbol else None
                    spot_stops = await self.exchange.privateGetStopOrder({"symbol": spot_id} if spot_id else {})
                    items = (spot_stops.get("data") or {}).get("items", []) if isinstance(spot_stops, dict) else []
                    for item in items:
                        oid = item.get("id")
                        if any(o.get("id") == oid for o in merged):
                            continue
                        sym = item.get("symbol", "").replace("-", "/")
                        price_val = float(item.get("price") or 0.0) if item.get("price") else None
                        stop_val = float(item.get("stopPrice") or 0.0) if item.get("stopPrice") else None
                        size_val = float(item.get("size") or 0.0)
                        merged.append({
                            "id": oid,
                            "clientOrderId": item.get("clientOid"),
                            "symbol": sym,
                            "side": item.get("side", "").lower(),
                            "type": "stop_loss" if item.get("stop") == "loss" else "stop",
                            "price": price_val,
                            "stopPrice": stop_val,
                            "stop_loss_price": stop_val,
                            "amount": size_val,
                            "filled": 0.0,
                            "remaining": size_val,
                            "status": "open",
                            "bracket_leg": "sl",
                            "market_type": "spot",
                            "is_stop": True,
                            "info": item,
                            "timestamp": item.get("createdAt"),
                        })
            except Exception as e:
                logger.debug(f"Spot stop emir listeleme hatası: {e}")

            # Futures stop/tetik emirleri çek
            try:
                fut_symbol = await self._normalize_symbol(symbol, "futures") if symbol else None
                fut_stops_parsed = []
                try:
                    fut_stops_parsed = await self.futures_exchange.fetch_open_orders(fut_symbol, params={"trigger": True})
                except Exception as ex_trig:
                    logger.debug(f"Futures CCXT trigger fetch: {ex_trig}")

                if fut_stops_parsed:
                    for o in fut_stops_parsed:
                        oid = o.get("id")
                        if any(m.get("id") == oid for m in merged):
                            continue
                        sl_val = float(o.get("stopPrice") or o.get("triggerPrice") or 0.0)
                        info = o.get("info") if isinstance(o.get("info"), dict) else {}
                        side = (o.get("side") or "").lower()
                        stop_dir = str(info.get("stop") or "").lower()
                        client_oid = str(o.get("clientOrderId") or info.get("clientOid") or "").lower()
                        o_type = str(o.get("type") or "").lower()

                        is_tp = False
                        if "tp" in client_oid or "take_profit" in o_type or "takeprofit" in o_type:
                            is_tp = True
                        elif side == "buy" and stop_dir == "down":
                            is_tp = True  # Short kâr alma emri
                        elif side == "sell" and stop_dir == "up":
                            is_tp = True  # Long kâr alma emri

                        o["market_type"] = "futures"
                        o["is_stop"] = True
                        if is_tp:
                            o["bracket_leg"] = "tp1"
                            if sl_val > 0:
                                o["tp1_price"] = sl_val
                        else:
                            o["bracket_leg"] = "sl"
                            if sl_val > 0:
                                o["stop_loss_price"] = sl_val
                        merged.append(o)
                else:
                    market_id = None
                    if fut_symbol:
                        if hasattr(self.futures_exchange, "markets") and self.futures_exchange.markets and fut_symbol in self.futures_exchange.markets:
                            market_id = self.futures_exchange.market_id(fut_symbol)
                        else:
                            clean_b = fut_symbol.split(":")[0].replace("/", "")
                            market_id = f"{clean_b}M" if not clean_b.endswith("M") else clean_b

                    fut_stops = await self.futures_exchange.futuresPrivateGetStopOrders({"symbol": market_id} if market_id else {})
                    items = (fut_stops.get("data") or {}).get("items", []) if isinstance(fut_stops, dict) else []
                    for item in items:
                        oid = item.get("id")
                        if any(o.get("id") == oid for o in merged):
                            continue
                        raw_sym = item.get("symbol", "")
                        norm_sym = None
                        if hasattr(self.futures_exchange, "markets") and self.futures_exchange.markets:
                            norm_sym = self.futures_exchange.safe_symbol(raw_sym)
                        if not norm_sym:
                            if raw_sym.endswith("USDTM"):
                                norm_sym = f"{raw_sym[:-5]}/USDT:USDT"
                            elif raw_sym.endswith("USDM"):
                                norm_sym = f"{raw_sym[:-4]}/USD:USD"
                            elif "/" in raw_sym:
                                norm_sym = raw_sym if ":" in raw_sym else f"{raw_sym}:USDT"
                            else:
                                norm_sym = raw_sym

                        sl_val = float(item.get("stopPrice") or item.get("triggerStopDownPrice") or item.get("triggerStopUpPrice") or 0.0)
                        price_val = float(item.get("price") or 0.0) if item.get("price") else None
                        size_val = float(item.get("size") or 0.0)
                        side = item.get("side", "").lower()
                        stop_dir = str(item.get("stop") or "").lower()
                        client_oid = str(item.get("clientOid") or "").lower()
                        o_type = str(item.get("type") or "").lower()

                        is_tp = False
                        if "tp" in client_oid or "take_profit" in o_type or "takeprofit" in o_type:
                            is_tp = True
                        elif side == "buy" and stop_dir == "down":
                            is_tp = True  # Short kâr alma emri
                        elif side == "sell" and stop_dir == "up":
                            is_tp = True  # Long kâr alma emri

                        merged.append({
                            "id": oid,
                            "clientOrderId": item.get("clientOid"),
                            "symbol": norm_sym,
                            "side": side,
                            "type": "stop_market" if item.get("type") == "market" else "stop_limit",
                            "price": price_val or sl_val,
                            "stopPrice": sl_val if sl_val > 0 else None,
                            "stop_loss_price": None if is_tp else (sl_val if sl_val > 0 else None),
                            "tp1_price": sl_val if is_tp and sl_val > 0 else None,
                            "amount": size_val,
                            "filled": 0.0,
                            "remaining": size_val,
                            "status": "open",
                            "bracket_leg": "tp1" if is_tp else "sl",
                            "market_type": "futures",
                            "is_stop": True,
                            "info": item,
                            "timestamp": item.get("createdAt"),
                        })
            except Exception as e:
                logger.debug(f"Futures stop emir listeleme hatası: {e}")

            await self._attach_current_prices(merged)

            return OpenOrdersResponse(
                success=True, data={"count": len(merged), "orders": merged},
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"Açık emir listeleme hatası: {e}")
            return OpenOrdersResponse(
                success=False, data={}, error=f"Açık emirler alınamadı: {e}", timestamp=timestamp())

    async def _attach_current_prices(self, orders: list[dict]) -> None:
        """Açık emir listesindeki her bir emre anlık piyasa fiyatını ve fiyat farkını iliştirir."""
        if not orders:
            return

        price_cache: dict[tuple[str, str], float | None] = {}
        for o in orders:
            sym = o.get("symbol")
            mt = (o.get("market_type") or "spot").lower()
            clean_sym = sym.split(":")[0] if (mt != "futures" and sym and ":" in sym) else sym
            key = (clean_sym, mt)

            if key not in price_cache and clean_sym:
                curr_price = None
                try:
                    if self.market:
                        tk = await self.market.get_ticker(clean_sym, market_type=mt)
                        if tk and getattr(tk, "success", False) and tk.data:
                            lp = tk.data.get("last_price")
                            if lp is not None:
                                curr_price = float(lp)
                except Exception as e:
                    logger.debug(f"Açık emir için anlık fiyat alınamadı ({clean_sym} {mt}): {e}")
                price_cache[key] = curr_price

            curr_price = price_cache.get(key)
            o["current_price"] = curr_price

            # Fiyat farkı ve yüzdesi hesabı
            order_price = o.get("price")
            stop_price = o.get("stop_loss_price") or o.get("tp1_price") or o.get("tp2_price") or o.get("stopPrice")
            try:
                order_p = float(order_price) if order_price is not None else 0.0
            except (ValueError, TypeError):
                order_p = 0.0
            try:
                stop_p = float(stop_price) if stop_price is not None else 0.0
            except (ValueError, TypeError):
                stop_p = 0.0

            target_p = order_p if order_p > 0 else stop_p

            if curr_price is not None and target_p > 0:
                diff = curr_price - target_p
                diff_pct = (diff / target_p) * 100.0
                o["price_diff"] = round(diff, 6)
                o["price_diff_percent"] = round(diff_pct, 4)
            else:
                o["price_diff"] = None
                o["price_diff_percent"] = None

            # Giriş Fiyatı (entry_price):
            if o.get("entry_price") is None:
                if o.get("side") == "buy" and o.get("type") == "limit":
                    o["entry_price"] = o.get("price")
                pos_key = f"{sym}-{mt}"
                if pos_key in self.paper_positions:
                    o["entry_price"] = self.paper_positions[pos_key].get("entry_price")
                    if o.get("stop_loss_price") is None:
                        o["stop_loss_price"] = self.paper_positions[pos_key].get("stop_loss_price")

            # Stop Fiyatı (stop_loss_price):
            if o.get("stop_loss_price") is None:
                if o.get("bracket_leg") == "sl":
                    o["stop_loss_price"] = o.get("price")
                elif o.get("stopPrice"):
                    try:
                        o["stop_loss_price"] = float(o.get("stopPrice"))
                    except (ValueError, TypeError):
                        pass

            # Stop mesafesi (%):
            sl = o.get("stop_loss_price")
            if curr_price is not None and sl is not None and curr_price > 0:
                try:
                    sl_p = float(sl)
                    if sl_p > 0:
                        o["stop_distance_percent"] = round(((sl_p - curr_price) / curr_price) * 100.0, 2)
                    else:
                        o["stop_distance_percent"] = None
                except (ValueError, TypeError):
                    o["stop_distance_percent"] = None
            else:
                o["stop_distance_percent"] = None

    async def get_positions(self, symbol: str | None = None) -> dict:
        """Açık pozisyonları ve eldeki varlıkları, maliyet ve anlık değerler ile döner."""
        try:
            positions: list[dict] = []
            if self.mode == "paper":
                raw_pos = list(self.paper_positions.values())
                if symbol:
                    raw_pos = [p for p in raw_pos if p.get("symbol") == symbol]
                for p in raw_pos:
                    pos = dict(p)
                    sym = pos.get("symbol")
                    mt = pos.get("market_type", "spot")
                    curr_price = None
                    try:
                        if self.market:
                            tk = await self.market.get_ticker(sym, market_type=mt)
                            if tk and getattr(tk, "success", False) and tk.data:
                                curr_price = float(tk.data.get("last_price") or 0)
                    except Exception as e:
                        logger.debug(f"Pozisyon anlık fiyat hatası: {e}")
                    pos["current_price"] = curr_price

                    entry_p = float(pos.get("entry_price") or 0)
                    amt = float(pos.get("amount") or 0)
                    side = pos.get("side", "long").lower()

                    pos["total_cost"] = round(entry_p * amt, 2) if entry_p and amt else 0.0
                    pos["current_value"] = round(curr_price * amt, 2) if curr_price and amt else 0.0

                    if curr_price and entry_p > 0 and amt > 0:
                        if side in ("long", "buy", "spot"):
                            pnl = (curr_price - entry_p) * amt
                            pnl_pct = ((curr_price - entry_p) / entry_p) * 100
                        else:
                            pnl = (entry_p - curr_price) * amt
                            pnl_pct = ((entry_p - curr_price) / entry_p) * 100
                        pos["unrealized_pnl"] = round(pnl, 2)
                        pos["pnl_percent"] = round(pnl_pct, 2)
                    else:
                        pos["unrealized_pnl"] = 0.0
                        pos["pnl_percent"] = 0.0

                    sl = pos.get("stop_loss_price")
                    if sl and curr_price:
                        try:
                            pos["stop_distance_percent"] = round(((float(sl) - curr_price) / curr_price) * 100, 2)
                        except (ValueError, TypeError):
                            pos["stop_distance_percent"] = None
                    else:
                        pos["stop_distance_percent"] = None
                    positions.append(pos)
            else:
                # Live kucoinfutures positions
                if not self.futures_exchange:
                    self.connect()
                try:
                    raw_pos = await self.futures_exchange.fetch_positions()
                    for p in raw_pos:
                        amt = float(p.get("contracts") or p.get("currentQty") or 0)
                        if abs(amt) <= 0:
                            continue
                        entry_p = float(p.get("entryPrice") or 0)
                        mark_p = float(p.get("markPrice") or p.get("last") or 0)
                        raw_info = p.get("info") or {}
                        cross_flag = raw_info.get("crossMode") if isinstance(raw_info, dict) else None
                        margin_mode = p.get("marginMode") or ("cross" if cross_flag else ("isolated" if cross_flag is False else None))
                        pos_obj = {
                            "id": p.get("id") or f"live-pos-{p.get('symbol')}",
                            "symbol": p.get("symbol"),
                            "side": "long" if str(p.get("side", "")).lower() == "long" or amt > 0 else "short",
                            "market_type": "futures",
                            "margin_mode": margin_mode,
                            "amount": abs(amt),
                            "entry_price": entry_p,
                            "total_cost": round(entry_p * abs(amt), 2),
                            "current_price": mark_p,
                            "current_value": round(mark_p * abs(amt), 2),
                            "liquidation_price": float(p.get("liquidationPrice") or 0),
                            "unrealized_pnl": round(float(p.get("unrealizedPnl") or 0), 2),
                            "pnl_percent": round(float(p.get("percentage") or 0), 2),
                            "leverage": p.get("leverage"),
                            "stop_loss_price": float(p.get("stopPrice") or 0) or None,
                            "tp1_price": None,
                            "tp2_price": None,
                            "created_at": timestamp(),
                        }
                        if symbol and pos_obj["symbol"] != symbol:
                            continue
                        positions.append(pos_obj)
                except Exception as e:
                    logger.error(f"Live pozisyon çekme hatası: {e}")

            # Gerçekleşen emirler sonrasında elimizdeki coinlerin maliyetleri (holding costs)
            holding_costs = await self.get_holding_costs()
            for base_asset, hc in holding_costs.items():
                sym = hc["symbol"]
                if symbol and sym != symbol:
                    continue
                # Eğer zaten bu sembolde bir spot pozisyonu varsa (ör. paper spot bracket) tekrar ekleme
                if any(p.get("market_type") == "spot" and p.get("symbol") == sym for p in positions):
                    continue
                amt = hc["qty"]
                entry_p = hc["avg_cost"]
                curr_price = None
                try:
                    if self.market:
                        tk = await self.market.get_ticker(sym, market_type="spot")
                        if tk and getattr(tk, "success", False) and tk.data:
                            curr_price = float(tk.data.get("last_price") or 0)
                except Exception as e:
                    logger.debug(f"Spot varlık anlık fiyat hatası ({sym}): {e}")

                total_c = round(amt * entry_p, 2)
                curr_val = round(amt * curr_price, 2) if curr_price else 0.0
                if curr_price and entry_p > 0:
                    pnl = curr_val - total_c
                    pnl_pct = ((curr_price - entry_p) / entry_p) * 100.0
                else:
                    pnl = 0.0
                    pnl_pct = 0.0

                pos_obj = {
                    "id": f"holding-{base_asset}",
                    "symbol": sym,
                    "market_type": "spot",
                    "side": "long",
                    "amount": amt,
                    "entry_price": entry_p,
                    "total_cost": total_c,
                    "current_price": curr_price,
                    "current_value": curr_val,
                    "unrealized_pnl": round(pnl, 2),
                    "pnl_percent": round(pnl_pct, 2),
                    "stop_loss_price": None,
                    "tp1_price": None,
                    "tp2_price": None,
                    "created_at": timestamp(),
                }
                positions.append(pos_obj)

            # Açık emirleri (özellikle Stop-Loss ve Take-Profit emirlerini) pozisyonlarla eşleştir
            try:
                open_orders_resp = await self.get_open_orders()
                open_orders = (open_orders_resp.data or {}).get("orders", []) if open_orders_resp.success else []
            except Exception as oe_err:
                logger.debug(f"Pozisyonlara açık emirleri bağlama hatası: {oe_err}")
                open_orders = []

            for pos in positions:
                p_sym = pos.get("symbol", "")
                p_clean = p_sym.split(":")[0] if ":" in p_sym else p_sym
                p_mt = (pos.get("market_type") or "spot").lower()
                p_side = (pos.get("side") or "long").lower()
                p_entry = float(pos.get("entry_price") or 0.0)
                p_curr = float(pos.get("current_price") or p_entry or 0.0)

                # Bu pozisyonla eşleşen açık emirler (sembol varyasyonları dahil)
                matched = [
                    o for o in open_orders
                    if (
                        o.get("symbol") in (p_sym, p_clean)
                        or (o.get("symbol") or "").split(":")[0] == p_clean
                        or (p_clean and (o.get("symbol") or "").replace("/", "").replace("-", "").startswith(p_clean.replace("/", "").replace("-", "")))
                    )
                    and (o.get("market_type") or "spot").lower() == p_mt
                ]

                sl_candidates: list[tuple[float, dict]] = []
                tp_candidates: list[tuple[float, dict]] = []
                ref_price = p_entry if p_entry > 0 else p_curr

                for o in matched:
                    o_leg = str(o.get("bracket_leg") or "").lower()
                    if o_leg == "entry":
                        continue

                    o_side = str(o.get("side") or "").lower()
                    is_exit_side = (
                        (p_side in ("long", "buy", "spot") and o_side == "sell")
                        or (p_side in ("short", "sell") and o_side == "buy")
                        or o_leg in ("tp", "tp1", "tp2", "sl")
                    )
                    if not is_exit_side:
                        continue

                    raw_info = o.get("info") if isinstance(o.get("info"), dict) else {}
                    raw_stop = str(raw_info.get("stop") or "").lower()
                    client_oid = str(o.get("clientOrderId") or raw_info.get("clientOid") or "").lower()
                    o_type = str(o.get("type") or "").lower()

                    # Hedef fiyatı belirle: stopPrice, triggerPrice, tp1_price, stop_loss_price veya limit price
                    o_stop = float(o.get("stopPrice") or o.get("stop_loss_price") or o.get("tp1_price") or o.get("tp2_price") or raw_info.get("triggerStopUpPrice") or raw_info.get("triggerStopDownPrice") or 0.0)
                    o_price = float(o.get("price") or 0.0)
                    target_p = o_stop if o_stop > 0 else o_price
                    if target_p <= 0:
                        continue

                    is_tp = False
                    is_sl = False

                    # A. Açıkça belirtilmiş etiketler
                    if o_leg in ("tp", "tp1", "tp2") or "tp" in client_oid or "take_profit" in o_type or "takeprofit" in o_type:
                        is_tp = True
                    elif o_leg == "sl" or "sl" in client_oid or "stop_loss" in o_type or "stoploss" in o_type:
                        is_sl = True
                    # B. KuCoin stop yönü (raw_stop: 'up' veya 'down')
                    elif raw_stop:
                        if p_side in ("long", "buy", "spot"):
                            if raw_stop == "up":
                                is_tp = True
                            elif raw_stop == "down":
                                is_sl = True
                        else:
                            # Short pozisyon
                            if raw_stop == "down":
                                is_tp = True
                            elif raw_stop == "up":
                                is_sl = True

                    # C. Fiyat seviyesine göre tespit (giriş veya anlık fiyata göre konumu)
                    if not is_tp and not is_sl and ref_price > 0:
                        if p_side in ("long", "buy", "spot"):
                            if target_p > ref_price:
                                is_tp = True
                            elif target_p < ref_price:
                                is_sl = True
                        else:
                            # Short
                            if target_p < ref_price:
                                is_tp = True
                            elif target_p > ref_price:
                                is_sl = True

                    # D. Yedek: Anlık fiyata göre son kontrol
                    if not is_tp and not is_sl and p_curr > 0:
                        if p_side in ("long", "buy", "spot"):
                            if target_p > p_curr:
                                is_tp = True
                            elif target_p < p_curr:
                                is_sl = True
                        else:
                            if target_p < p_curr:
                                is_tp = True
                            elif target_p > p_curr:
                                is_sl = True

                    if is_tp:
                        tp_candidates.append((target_p, o))
                    elif is_sl:
                        sl_candidates.append((target_p, o))

                # 1. Stop-Loss ata
                if not pos.get("stop_loss_price") and sl_candidates:
                    # Pozisyon yönüne göre en yakın/birincil SL emrini seç
                    if p_side in ("short", "sell"):
                        sl_candidates.sort(key=lambda x: x[0])  # Short için yukarıdaki en düşük tetik
                    else:
                        sl_candidates.sort(key=lambda x: x[0], reverse=True)  # Long için aşağıdaki en yüksek tetik
                    pos["stop_loss_price"] = sl_candidates[0][0]
                    pos["stop_order_id"] = sl_candidates[0][1].get("id")

                # 2. Take-Profit (TP1 ve TP2) ata
                explicit_tp1 = next((item for item in tp_candidates if str(item[1].get("bracket_leg")).lower() in ("tp", "tp1")), None)
                explicit_tp2 = next((item for item in tp_candidates if str(item[1].get("bracket_leg")).lower() == "tp2"), None)

                if explicit_tp1 and not pos.get("tp1_price"):
                    pos["tp1_price"] = explicit_tp1[0]
                    pos["tp_order_id"] = explicit_tp1[1].get("id")
                if explicit_tp2 and not pos.get("tp2_price"):
                    pos["tp2_price"] = explicit_tp2[0]
                    pos["tp2_order_id"] = explicit_tp2[1].get("id")

                if not pos.get("tp1_price") and tp_candidates:
                    if p_side in ("short", "sell"):
                        tp_candidates.sort(key=lambda x: x[0], reverse=True)
                    else:
                        tp_candidates.sort(key=lambda x: x[0])

                    pos["tp1_price"] = tp_candidates[0][0]
                    pos["tp_order_id"] = tp_candidates[0][1].get("id")

                    if len(tp_candidates) > 1 and not pos.get("tp2_price"):
                        pos["tp2_price"] = tp_candidates[1][0]
                        pos["tp2_order_id"] = tp_candidates[1][1].get("id")

                # 3. Stop-Loss ve TP uzaklık yüzdelerini hesapla
                sl_val = pos.get("stop_loss_price")
                if sl_val and p_curr > 0:
                    try:
                        sl_f = float(sl_val)
                        pos["stop_distance_percent"] = round(((sl_f - p_curr) / p_curr) * 100.0, 2)
                    except (ValueError, TypeError):
                        pos["stop_distance_percent"] = None
                else:
                    pos["stop_distance_percent"] = None

                tp1_val = pos.get("tp1_price")
                if tp1_val and p_curr > 0:
                    try:
                        tp1_f = float(tp1_val)
                        pos["tp_distance_percent"] = round(((tp1_f - p_curr) / p_curr) * 100.0, 2)
                    except (ValueError, TypeError):
                        pos["tp_distance_percent"] = None
                else:
                    pos["tp_distance_percent"] = None

                tp2_val = pos.get("tp2_price")
                if tp2_val and p_curr > 0:
                    try:
                        tp2_f = float(tp2_val)
                        pos["tp2_distance_percent"] = round(((tp2_f - p_curr) / p_curr) * 100.0, 2)
                    except (ValueError, TypeError):
                        pos["tp2_distance_percent"] = None
                else:
                    pos["tp2_distance_percent"] = None

            return {"success": True, "data": {"count": len(positions), "positions": positions},
                    "error": None, "timestamp": timestamp()}
        except Exception as e:
            logger.error(f"Pozisyon listeleme hatası: {e}")
            return {"success": False, "data": {"count": 0, "positions": []}, "error": str(e),
                    "timestamp": timestamp()}

    # ------------------------------------------------------------------ #
    # Gerçekleşen emirlerden eldeki coinlerin maliyet ve miktar hesaplaması
    # ------------------------------------------------------------------ #
    def calculate_holding_costs(self, orders: list[dict]) -> dict[str, dict]:
        """
        Emir geçmişindeki dolan işlemleri kronolojik sırayla işleyerek,
        gerçekleşen emirler sonrasında elimizde kalan kripto paraların
        ortalama maliyetini (kaça mal olduklarını), toplam maliyetini
        ve miktarını hesaplar.
        """
        positions: dict[str, dict] = {}

        def _ts(o):
            return o.get("timestamp") or o.get("created_at") or 0

        for o in sorted(orders, key=_ts):
            status = str(o.get("status", "")).lower()
            if status not in ("filled", "closed", "done"):
                continue

            # Vadeli (Futures) emirlerini hariç tut - spot varlık değildir
            mt = str(o.get("market_type", "")).lower()
            if mt == "futures":
                continue

            sym = o.get("symbol")
            if not sym or "/" not in sym:
                continue

            # Vadeli sembol formatlarını hariç tut (örn: SUI/USDT:USDT)
            if ":" in sym:
                continue

            clean_sym = sym.split(":")[0] if ":" in sym else sym
            base_asset = clean_sym.split("/")[0].upper()
            quote_asset = clean_sym.split("/")[1].upper() if "/" in clean_sym else "USDT"

            if quote_asset not in ("USDT", "USD", "USDC"):
                continue

            side = str(o.get("side", "")).lower()
            qty = float(o.get("filled") or o.get("amount") or 0.0)
            price = float(o.get("average") or o.get("filled_price") or o.get("price") or 0.0)
            if qty <= 0 or price <= 0:
                continue

            pos = positions.setdefault(base_asset, {
                "symbol": clean_sym,
                "base_asset": base_asset,
                "qty": 0.0,
                "cost": 0.0,
                "avg_cost": 0.0,
            })

            if side == "buy":
                pos["qty"] += qty
                pos["cost"] += qty * price
                pos["avg_cost"] = pos["cost"] / pos["qty"] if pos["qty"] > 0 else 0.0
            elif side == "sell":
                avg_cost = pos["avg_cost"] if pos["avg_cost"] > 0 else (pos["cost"] / pos["qty"] if pos["qty"] > 0 else price)
                sell_qty = min(qty, pos["qty"]) if pos["qty"] > 0 else qty
                pos["qty"] -= sell_qty
                pos["cost"] -= avg_cost * sell_qty
                if pos["qty"] < 1e-12:
                    pos["qty"] = 0.0
                    pos["cost"] = 0.0
                    pos["avg_cost"] = 0.0
                else:
                    pos["avg_cost"] = pos["cost"] / pos["qty"]

        result = {}
        for base, data in positions.items():
            if data["qty"] > 1e-12 and data["avg_cost"] > 0:
                result[base] = {
                    "symbol": data["symbol"],
                    "base_asset": base,
                    "qty": round(data["qty"], 8),
                    "cost": round(data["cost"], 4),
                    "avg_cost": round(data["avg_cost"], 6) if data["avg_cost"] < 1 else round(data["avg_cost"], 4),
                }
        return result

    async def get_holding_costs(self) -> dict[str, dict]:
        """Tüm geçmiş emirlerden eldeki varlıkların maliyetlerini döndürür."""
        try:
            h = await self.get_history(limit=0)
            orders = h.data.get("orders", []) if h.success else []
            return self.calculate_holding_costs(orders)
        except Exception as e:
            logger.error(f"Eldeki varlık maliyetleri hesaplama hatası: {e}")
            return {}

    # ------------------------------------------------------------------ #
    # İşlem geçmişi (Tüm geçmiş emirler ve filtreleme)
    # ------------------------------------------------------------------ #
    async def get_history(self, symbol: str | None = None, limit: int | None = 50) -> OrderHistoryResponse:
        try:
            if self.mode == "paper":
                hist = list(self.paper_history)
                if symbol:
                    clean_sym = symbol.split(":")[0] if ":" in symbol else symbol
                    hist = [h for h in hist if h.get("symbol") in (symbol, clean_sym)]
                for h in hist:
                    h.setdefault("market_type", "spot")
                orders = hist if (limit is None or limit <= 0) else hist[-limit:]
                orders_sorted = sorted(orders, key=lambda x: x.get("timestamp") or x.get("created_at") or 0, reverse=True)
                return OrderHistoryResponse(
                    success=True, data={"count": len(orders_sorted), "orders": orders_sorted},
                    error=None, timestamp=timestamp())

            if not self.exchange:
                self.connect()

            merged: list[dict] = []
            fetch_limit = limit if (limit and limit > 0) else 200
            try:
                spot_orders = await self.exchange.fetch_closed_orders(symbol, limit=fetch_limit)
                for o in spot_orders:
                    info = o.get("info", {}) or {}
                    is_margin = str(info.get("tradeType", "")).upper().startswith("MARGIN")
                    o["market_type"] = "margin" if is_margin else "spot"
                    merged.append(o)
            except Exception as e:
                logger.error(f"Spot geçmiş emir çekme hatası: {e}")

            if self.futures_exchange:
                try:
                    fut_symbol = await self._normalize_symbol(symbol, "futures") if symbol else None
                    fut_orders = await self.futures_exchange.fetch_closed_orders(fut_symbol, limit=fetch_limit)
                    for o in fut_orders:
                        o["market_type"] = "futures"
                        merged.append(o)
                except Exception as e:
                    logger.error(f"Futures geçmiş emir çekme hatası: {e}")

            merged.sort(key=lambda x: x.get("timestamp") or x.get("created_at") or 0, reverse=True)
            if limit and limit > 0:
                merged = merged[:limit]

            return OrderHistoryResponse(
                success=True, data={"count": len(merged), "orders": merged},
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"Emir geçmişi hatası: {e}")
            return OrderHistoryResponse(
                success=False, data={}, error=f"Emir geçmişi alınamadı: {e}", timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # Kar/Zarar (P&L) Raporu — emir geçmişinden hesaplanır
    # ------------------------------------------------------------------ #
    async def get_pnl_report(self, symbol: str | None = None, limit: int = 200) -> PnLReportResponse:
        """
        Emir geçmişini (dolan emirler) çekip sembol bazında gerçekleşen kar/zararı
        (realized P&L) hesaplar. Ortalama maliyet (average cost) yöntemi kullanılır:
        alışlar pozisyon maliyetini artırır, satışlar o anki ortalama maliyete göre
        realize P&L üretir.
        """
        try:
            hist_res = await self.get_history(symbol, limit=limit)
            if not hist_res.success:
                return PnLReportResponse(
                    success=False, data={}, error=hist_res.error, timestamp=timestamp())

            orders = hist_res.data.get("orders", [])

            # Sembol bazında pozisyon: {symbol: {"qty": float, "cost": float}}
            positions: dict[str, dict] = {}
            per_symbol_pnl: dict[str, dict] = {}
            daily_pnl_map: dict[str, dict] = {}

            # Zaman sırasına göre işle (eski -> yeni)
            def _ts(o):
                return o.get("timestamp") or o.get("created_at") or 0

            def _date(o) -> str:
                raw = str(o.get("datetime") or o.get("created_at") or "")
                if len(raw) >= 10 and raw[:4].isdigit() and raw[4] == "-" and raw[7] == "-":
                    return raw[:10]
                ts_v = o.get("timestamp") or o.get("created_at")
                if isinstance(ts_v, (int, float)) and ts_v > 0:
                    if ts_v > 1e11:
                        ts_v = ts_v / 1000.0
                    return datetime.fromtimestamp(ts_v, tz=timezone.utc).strftime("%Y-%m-%d")
                return datetime.now(timezone.utc).strftime("%Y-%m-%d")

            for o in sorted(orders, key=_ts):
                # Yalnızca dolan (filled/closed) emirler P&L üretir
                status = str(o.get("status", "")).lower()
                if status not in ("filled", "closed", "done"):
                    continue
                sym = o.get("symbol")
                side = str(o.get("side", "")).lower()
                # Miktar: ccxt 'filled' veya paper 'amount'
                qty = float(o.get("filled") or o.get("amount") or 0.0)
                # Fiyat: ccxt 'average'/'price' veya paper 'filled_price'/'price'
                price = float(o.get("average") or o.get("filled_price") or o.get("price") or 0.0)
                if qty <= 0 or price <= 0 or not sym:
                    continue
                fee = 0.0
                fee_obj = o.get("fee") or {}
                if isinstance(fee_obj, dict):
                    fee = float(fee_obj.get("cost") or 0.0)

                d_key = _date(o)
                day_stat = daily_pnl_map.setdefault(d_key, {
                    "date": d_key, "realized_pnl": 0.0, "buy_count": 0,
                    "sell_count": 0, "total_fee": 0.0, "volume_usdt": 0.0,
                })
                day_stat["total_fee"] += fee
                day_stat["volume_usdt"] += qty * price

                pos = positions.setdefault(sym, {"qty": 0.0, "cost": 0.0})
                stats = per_symbol_pnl.setdefault(sym, {
                    "symbol": sym, "realized_pnl": 0.0, "buy_count": 0,
                    "sell_count": 0, "total_fee": 0.0, "volume_usdt": 0.0,
                })
                stats["total_fee"] += fee
                stats["volume_usdt"] += qty * price

                # Vadeli borsa siparişi kendi realizedPnl değerini dönüyorsa:
                raw_info = o.get("info") or {}
                fut_realized = raw_info.get("realisedPnl") if isinstance(raw_info, dict) else None
                if fut_realized is not None:
                    try:
                        fut_realized_val = float(fut_realized)
                    except (ValueError, TypeError):
                        fut_realized_val = None
                else:
                    fut_realized_val = None

                if side == "buy":
                    pos["qty"] += qty
                    pos["cost"] += qty * price
                    stats["buy_count"] += 1
                    day_stat["buy_count"] += 1
                    if fut_realized_val is not None and fut_realized_val != 0:
                        stats["realized_pnl"] += fut_realized_val
                        day_stat["realized_pnl"] += fut_realized_val
                elif side == "sell":
                    stats["sell_count"] += 1
                    day_stat["sell_count"] += 1
                    if fut_realized_val is not None and fut_realized_val != 0:
                        stats["realized_pnl"] += fut_realized_val
                        day_stat["realized_pnl"] += fut_realized_val
                    else:
                        avg_cost = (pos["cost"] / pos["qty"]) if pos["qty"] > 0 else price
                        sell_qty = min(qty, pos["qty"]) if pos["qty"] > 0 else qty
                        realized = (price - avg_cost) * sell_qty - fee
                        stats["realized_pnl"] += realized
                        day_stat["realized_pnl"] += realized
                        pos["qty"] -= sell_qty
                        pos["cost"] -= avg_cost * sell_qty
                        if pos["qty"] < 1e-12:
                            pos["qty"] = 0.0
                            pos["cost"] = 0.0

            # Sembol bazında özet
            symbols_report = []
            total_realized = 0.0
            total_fee = 0.0
            total_volume = 0.0
            for sym, stats in per_symbol_pnl.items():
                stats["realized_pnl"] = round(stats["realized_pnl"], 4)
                stats["total_fee"] = round(stats["total_fee"], 4)
                stats["volume_usdt"] = round(stats["volume_usdt"], 4)
                stats["open_qty"] = round(positions.get(sym, {}).get("qty", 0.0), 8)
                total_realized += stats["realized_pnl"]
                total_fee += stats["total_fee"]
                total_volume += stats["volume_usdt"]
                symbols_report.append(stats)

            symbols_report.sort(key=lambda x: x["realized_pnl"], reverse=True)

            # Günlük PnL listesini kronolojik olarak sırala ve kümülatif PnL hesapla
            sorted_days = sorted(daily_pnl_map.values(), key=lambda x: x["date"])
            cum_pnl = 0.0
            for d in sorted_days:
                d["realized_pnl"] = round(d["realized_pnl"], 4)
                d["total_fee"] = round(d["total_fee"], 4)
                d["volume_usdt"] = round(d["volume_usdt"], 4)
                cum_pnl += d["realized_pnl"]
                d["cumulative_pnl"] = round(cum_pnl, 4)
                d["trade_count"] = d["buy_count"] + d["sell_count"]

            return PnLReportResponse(
                success=True,
                data={
                    "total_realized_pnl": round(total_realized, 4),
                    "total_fee": round(total_fee, 4),
                    "total_volume_usdt": round(total_volume, 4),
                    "symbol_count": len(symbols_report),
                    "symbols": symbols_report,
                    "daily_pnl": sorted_days,
                },
                error=None, timestamp=timestamp())
        except Exception as e:
            logger.error(f"P&L raporu hatası: {e}")
            return PnLReportResponse(
                success=False, data={}, error=f"Kar/zarar raporu alınamadı: {e}", timestamp=timestamp())

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

            # 1. Normal spot/margin iptal dene
            try:
                await self.exchange.cancel_order(order_id, symbol)
                return OrderCancelResponse(
                    success=True, data={"id": order_id, "status": "canceled"},
                    error=None, timestamp=timestamp())
            except Exception as e_norm:
                logger.debug(f"Spot cancel_order yanıtı: {e_norm}, alternatif iptal deneniyor...")

            # 2. Futures normal iptal dene
            if self.futures_exchange:
                try:
                    await self.futures_exchange.cancel_order(order_id, symbol)
                    return OrderCancelResponse(
                        success=True, data={"id": order_id, "status": "canceled"},
                        error=None, timestamp=timestamp())
                except Exception as e_fut:
                    logger.debug(f"Futures normal cancel yanıtı: {e_fut}")

            # 3. KuCoin Futures Stop Order iptali (DELETE /api/v1/stopOrders)
            if self.futures_exchange:
                try:
                    await self.futures_exchange.futuresPrivateDeleteStopOrders({"orderId": order_id})
                    return OrderCancelResponse(
                        success=True, data={"id": order_id, "status": "canceled"},
                        error=None, timestamp=timestamp())
                except Exception as e_fstop:
                    logger.debug(f"Futures stop cancel yanıtı: {e_fstop}")

            # 4. KuCoin Spot Stop Order iptali (DELETE /api/v1/stop-order/cancel)
            if self.exchange:
                try:
                    await self.exchange.privateDeleteStopOrderCancel({"orderId": order_id})
                    return OrderCancelResponse(
                        success=True, data={"id": order_id, "status": "canceled"},
                        error=None, timestamp=timestamp())
                except Exception as e_sstop:
                    logger.debug(f"Spot stop cancel yanıtı: {e_sstop}")

            return OrderCancelResponse(
                success=False, data={}, error=f"Emir iptal edilemedi: {order_id}", timestamp=timestamp())
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
                self.paper_positions.clear()
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
        market_type: str = "spot",
        margin_mode: str = "cross", leverage: float | None = None,
    ) -> "OrderCreateResponse":
        """
        Tek pakette: Giriş emri + TP1 (%50) + TP2 (%50) + SL (%100).
        Paper modda giriş anında dolar, TP/SL açık limit emir olarak kaydedilir.
        Spot, Margin ve Futures piyasa türlerini destekler.
        """
        side = (side or "buy").lower()
        market_type = (market_type or "spot").lower()
        if market_type == "spot" and side in ("sell", "short"):
            return OrderCreateResponse(
                success=False, data={},
                error="Spot piyasada açığa satış (Short) veya satış yönlü bracket pozisyon açılamaz. Vadeli (Futures) veya Margin piyasayı seçiniz.",
                timestamp=timestamp()
            )
        err = self._validate_order(symbol, side, "limit", usdt_amount and 1, entry_price, market_type)
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
        entry_res = await self.create_order(symbol, side, "market", amount, None, market_type,
                                            margin_mode=margin_mode, leverage=leverage,
                                            entry_price=entry_price, stop_loss_price=stop_loss_price)
        if not entry_res.success:
            return OrderCreateResponse(success=False, data={},
                                       error=f"Giriş emri başarısız: {entry_res.error}",
                                       timestamp=timestamp())

        # Açık pozisyon kaydı (Paper)
        pos_key = f"{symbol}-{market_type}"
        self.paper_positions[pos_key] = {
            "id": bracket_id,
            "bracket_id": bracket_id,
            "symbol": symbol,
            "side": "long" if side == "buy" else "short",
            "market_type": market_type,
            "margin_mode": margin_mode if market_type in ("margin", "futures") else None,
            "leverage": leverage if market_type == "futures" else (5.0 if market_type == "margin" else None),
            "amount": amount,
            "notional_usdt": usdt_amount,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "tp1_price": tp1_price,
            "tp2_price": tp2_price,
            "status": "open",
            "created_at": timestamp(),
        }

        # Bacak miktarları ve kontrat hesaplaması
        if market_type == "futures" and self.mode == "live":
            tot_contracts = max(1, int(round(amount)))
            if tot_contracts == 1:
                tp1_qty = 1
                tp2_qty = None
            else:
                tp1_qty = tot_contracts // 2
                tp2_qty = tot_contracts - tp1_qty
            sl_qty = tot_contracts
        else:
            tp1_qty = amount * 0.5
            tp2_qty = amount * 0.5
            sl_qty = amount

        legs = {"entry": entry_res.data}
        failed_legs = []

        # 1. TP1 (%50 veya 1 kontrat) — Limit çıkış emri (reduceOnly)
        tp1_res = await self.create_order(
            symbol, exit_side, "limit", tp1_qty, tp1_price, market_type,
            margin_mode=margin_mode, leverage=leverage,
            entry_price=entry_price, stop_loss_price=stop_loss_price,
            reduce_only=True,
        )
        if tp1_res.success:
            tp1_res.data["bracket_leg"] = "tp1"
            tp1_res.data["bracket_id"] = bracket_id
            tp1_res.data["entry_price"] = entry_price
            tp1_res.data["stop_loss_price"] = stop_loss_price
            tp1_res.data["tp1_price"] = tp1_price
            tp1_res.data["tp2_price"] = tp2_price
            if self.mode == "paper" and tp1_res.data.get("id") in self.paper_open_orders:
                self.paper_open_orders[tp1_res.data["id"]].update({
                    "bracket_leg": "tp1", "bracket_id": bracket_id,
                    "entry_price": entry_price, "stop_loss_price": stop_loss_price,
                    "tp1_price": tp1_price, "tp2_price": tp2_price,
                })
            legs["tp1"] = tp1_res.data
        else:
            legs["tp1"] = {"error": tp1_res.error}
            failed_legs.append(f"TP1 ({tp1_res.error})")

        # 2. TP2 (%50 veya kalan kontratlar) — Limit çıkış emri (reduceOnly)
        if tp2_qty is not None and tp2_qty > 0:
            tp2_res = await self.create_order(
                symbol, exit_side, "limit", tp2_qty, tp2_price, market_type,
                margin_mode=margin_mode, leverage=leverage,
                entry_price=entry_price, stop_loss_price=stop_loss_price,
                reduce_only=True,
            )
            if tp2_res.success:
                tp2_res.data["bracket_leg"] = "tp2"
                tp2_res.data["bracket_id"] = bracket_id
                tp2_res.data["entry_price"] = entry_price
                tp2_res.data["stop_loss_price"] = stop_loss_price
                tp2_res.data["tp1_price"] = tp1_price
                tp2_res.data["tp2_price"] = tp2_price
                if self.mode == "paper" and tp2_res.data.get("id") in self.paper_open_orders:
                    self.paper_open_orders[tp2_res.data["id"]].update({
                        "bracket_leg": "tp2", "bracket_id": bracket_id,
                        "entry_price": entry_price, "stop_loss_price": stop_loss_price,
                        "tp1_price": tp1_price, "tp2_price": tp2_price,
                    })
                legs["tp2"] = tp2_res.data
            else:
                legs["tp2"] = {"error": tp2_res.error}
                failed_legs.append(f"TP2 ({tp2_res.error})")
        else:
            legs["tp2"] = {
                "bracket_leg": "tp2",
                "bracket_id": bracket_id,
                "status": "skipped",
                "note": "1 kontrat olduğu için TP1 tüm miktarı kapsar.",
            }

        # 3. Stop Loss (%100 - Stop Market emri, reduceOnly)
        sl_res = await self.create_order(
            symbol, exit_side, "market", sl_qty, None, market_type,
            margin_mode=margin_mode, leverage=leverage,
            entry_price=entry_price, stop_loss_price=stop_loss_price,
            is_stop=True, reduce_only=True,
        )
        if sl_res.success:
            sl_res.data["bracket_leg"] = "sl"
            sl_res.data["bracket_id"] = bracket_id
            sl_res.data["entry_price"] = entry_price
            sl_res.data["stop_loss_price"] = stop_loss_price
            sl_res.data["tp1_price"] = tp1_price
            sl_res.data["tp2_price"] = tp2_price
            if self.mode == "paper" and sl_res.data.get("id") in self.paper_open_orders:
                self.paper_open_orders[sl_res.data["id"]].update({
                    "bracket_leg": "sl", "bracket_id": bracket_id,
                    "entry_price": entry_price, "stop_loss_price": stop_loss_price,
                    "tp1_price": tp1_price, "tp2_price": tp2_price,
                })
            legs["sl"] = sl_res.data
        else:
            legs["sl"] = {"error": sl_res.error}
            failed_legs.append(f"SL ({sl_res.error})")

        warning = f"Giriş yapıldı fakat bazı çıkış emirleri iletilemedi: {', '.join(failed_legs)}" if failed_legs else None
        if warning:
            logger.warning(f"Bracket emir uyarısı: {warning}")

        return OrderCreateResponse(
            success=True,
            data={
                "bracket_id": bracket_id,
                "symbol": symbol, "side": side, "market_type": market_type,
                "margin_mode": margin_mode if market_type in ("margin", "futures") else None,
                "leverage": leverage if market_type == "futures" else (5.0 if market_type == "margin" else None),
                "usdt_amount": usdt_amount, "amount": amount,
                "entry_price": entry_price, "stop_loss_price": stop_loss_price,
                "tp1_price": tp1_price, "tp2_price": tp2_price,
                "risk_usdt": risk_usdt, "gain_tp1_usdt": gain_tp1, "gain_tp2_usdt": gain_tp2,
                "legs": legs,
                "failed_legs": failed_legs,
                "warning": warning,
            },
            error=None, timestamp=timestamp())

    # ------------------------------------------------------------------ #
    # Pozisyona TP / SL Bağlama veya Güncelleme
    # ------------------------------------------------------------------ #
    async def set_position_tp_sl(
        self, symbol: str, market_type: str = "futures",
        tp_price: float | None = None, sl_price: float | None = None,
        amount: float | None = None, side: str = "long",
        leverage: float | None = None, margin_mode: str = "cross"
    ) -> dict:
        """
        Açık bir pozisyona TP ve/veya SL bağlar veya günceller.
        Miktar belirtilmezse mevcut açık pozisyon miktarı otomatik kullanılır.
        """
        try:
            side_norm = (side or "long").lower()
            exit_side = "sell" if side_norm in ("long", "spot", "buy") else "buy"
            mt = (market_type or "futures").lower()

            # Miktar tespit et (verilmediyse açık pozisyondan çek)
            qty = amount
            if qty is None or qty <= 0:
                pos_resp = await self.get_positions(symbol)
                positions = (pos_resp.get("data") or {}).get("positions", [])
                matching = [p for p in positions if p.get("symbol") == symbol or p.get("symbol", "").startswith(symbol)]
                if matching:
                    qty = float(matching[0].get("amount") or 0.0)
                    if not leverage and matching[0].get("leverage"):
                        leverage = float(matching[0].get("leverage"))
                if not qty or qty <= 0:
                    qty = 1.0 if mt == "futures" else 0.01

            results = {"symbol": symbol, "market_type": mt, "amount": qty, "legs": {}}

            # TP Emri (Kâr Al - Limit Order, reduceOnly=True)
            if tp_price and float(tp_price) > 0:
                tp_res = await self.create_order(
                    symbol, exit_side, "limit", qty, float(tp_price), mt,
                    margin_mode=margin_mode, leverage=leverage, reduce_only=True
                )
                if tp_res.success:
                    tp_res.data["bracket_leg"] = "tp1"
                    results["legs"]["tp"] = tp_res.data
                else:
                    results["legs"]["tp"] = {"error": tp_res.error}

            # SL Emri (Zarar Durdur - Stop Market Order, is_stop=True, reduceOnly=True)
            if sl_price and float(sl_price) > 0:
                sl_res = await self.create_order(
                    symbol, exit_side, "market", qty, None, mt,
                    margin_mode=margin_mode, leverage=leverage,
                    stop_loss_price=float(sl_price), is_stop=True, reduce_only=True
                )
                if sl_res.success:
                    sl_res.data["bracket_leg"] = "sl"
                    results["legs"]["sl"] = sl_res.data
                else:
                    results["legs"]["sl"] = {"error": sl_res.error}

            errors = [f"{k}: {v['error']}" for k, v in results["legs"].items() if isinstance(v, dict) and "error" in v]
            if errors:
                return {"success": False, "data": results, "error": "; ".join(errors), "timestamp": timestamp()}

            return {"success": True, "data": results, "error": None, "timestamp": timestamp()}
        except Exception as e:
            logger.error(f"Pozisyon TP/SL bağlama hatası ({symbol}): {e}")
            return {"success": False, "data": {}, "error": str(e), "timestamp": timestamp()}

    # ------------------------------------------------------------------ #
    # Güvenli Pozisyon ve İlgili Emirleri Kapatma (Safe Close Position)
    # ------------------------------------------------------------------ #
    async def close_position_safe(
        self,
        symbol: str,
        market_type: str = "futures",
        side: str = "long",
        amount: float | None = None,
        cancel_order_ids: list[str] | None = None,
        close_position: bool = True,
    ) -> dict:
        """
        Güvenli Pozisyon ve Emir Kapatma:
        1. Sıra Kontrolü: Önce pozisyona ait seçili tüm açık emirler (SL, TP, limitler) iptal edilir.
        2. Uyum Kontrolü: İptal işlemleri doğrulanır (eski emirlerin kalması veya yetersiz bakiye engellenir).
        3. Pozisyon Kapatma: Pozisyon yönünün tersine Market emir iletilir (long -> sell, short -> buy).
        """
        try:
            mt = (market_type or "spot").lower()
            cancel_ids = list(cancel_order_ids or [])
            cancel_results = []
            cancel_errors = []

            # 1. Aşama: Açık emirlerin iptali (Önce emirler iptal edilmeli)
            for oid in cancel_ids:
                try:
                    res = await self.cancel_order(oid, symbol=symbol)
                    if getattr(res, "success", False):
                        cancel_results.append({"id": oid, "status": "cancelled"})
                    else:
                        cancel_errors.append(f"{oid}: {getattr(res, 'error', 'İptal edilemedi')}")
                except Exception as ex:
                    cancel_errors.append(f"{oid}: {ex}")

            # 2. Aşama: Pozisyonu piyasadan kapatma
            close_result = None
            close_error = None
            if close_position:
                try:
                    qty = amount
                    if not qty or qty <= 0:
                        pos_resp = await self.get_positions(symbol=symbol)
                        if pos_resp.get("success") and pos_resp.get("data", {}).get("positions"):
                            matching = [
                                p for p in pos_resp["data"]["positions"]
                                if (p.get("market_type") or "spot").lower() == mt
                            ]
                            if matching:
                                qty = float(matching[0].get("amount") or 0.0)

                    if not qty or qty <= 0:
                        close_error = "Kapatılacak geçerli bir pozisyon miktarı bulunamadı."
                    else:
                        pos_side = (side or "long").lower()
                        exit_side = "sell" if pos_side in ("long", "buy", "spot") else "buy"

                        if mt == "futures":
                            res_close = await self.create_order(
                                symbol=symbol,
                                side=exit_side,
                                order_type="market",
                                amount=qty,
                                price=None,
                                market_type="futures",
                                reduce_only=True,
                                params={"reduceOnly": True},
                            )
                        else:
                            res_close = await self.create_order(
                                symbol=symbol,
                                side=exit_side,
                                order_type="market",
                                amount=qty,
                                price=None,
                                market_type=mt,
                            )

                        if getattr(res_close, "success", False):
                            close_result = res_close.data
                        else:
                            close_error = getattr(res_close, "error", "Piyasa emri iletilemedi")
                except Exception as cex:
                    close_error = str(cex)

            overall_success = (not cancel_errors) and (not close_error if close_position else True)
            errors = cancel_errors + ([close_error] if close_error else [])

            return {
                "success": overall_success,
                "data": {
                    "symbol": symbol,
                    "market_type": mt,
                    "cancelled_orders": cancel_results,
                    "cancelled_count": len(cancel_results),
                    "position_closed": close_result,
                    "close_requested": close_position,
                    "execution_sequence": ["cancelled_open_orders", "closed_market_position"],
                },
                "error": "; ".join(errors) if errors else None,
                "timestamp": timestamp(),
            }
        except Exception as e:
            logger.error(f"Güvenli pozisyon kapatma hatası ({symbol}): {e}")
            return {"success": False, "data": {}, "error": str(e), "timestamp": timestamp()}

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
