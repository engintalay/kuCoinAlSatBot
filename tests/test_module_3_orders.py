"""
KuCoin Al-Sat Botu — Modül 3 Testleri (Emir Yönetimi & Paper Trading)
İzlenebilirlik: M3-C01 (risk), C02 (market), C03 (limit), C04 (open),
C05 (cancel), C06 (panic), C07 (paper), C08 (mode switch).
"""

import pytest
from unittest.mock import AsyncMock


def _paper_orders(balance=10000.0, price=50000.0):
    """Paper modda, sabit fiyat veren market mock'lu KuCoinOrders üretir."""
    from src.modules.module3_orders import KuCoinOrders
    o = KuCoinOrders()
    o.mode = "paper"
    o.paper_balance_usdt = balance
    o.bot_active = True
    o._current_price = AsyncMock(return_value=price)
    return o


class TestOrderValidation:
    """M3-C01: Pre-trade risk & doğrulama."""

    @pytest.mark.asyncio
    async def test_invalid_side(self):
        o = _paper_orders()
        r = await o.create_order("BTC/USDT", "hold", "market", 0.001)
        assert r.success is False
        assert "yön" in r.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_market_type(self):
        """Geçersiz piyasa türü reddedilmeli (spot/margin/futures dışı)."""
        o = _paper_orders()
        r = await o.create_order("BTC/USDT", "buy", "market", 0.001, None, "perp")
        assert r.success is False
        assert "piyasa türü" in r.error.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mtype", ["spot", "margin", "futures"])
    async def test_paper_order_records_market_type(self, mtype):
        """Paper emir kaydı seçilen market_type'ı içermeli (spot/margin/futures)."""
        o = _paper_orders()
        r = await o.create_order("BTC/USDT", "buy", "limit", 0.01, 50000.0, mtype)
        assert r.success is True
        assert r.data["market_type"] == mtype

    @pytest.mark.asyncio
    async def test_open_orders_expose_market_type(self):
        """Açık emirler her kayıtta market_type alanını sunmalı."""
        o = _paper_orders()
        await o.create_order("BTC/USDT", "buy", "limit", 0.01, 50000.0, "futures")
        await o.create_order("ETH/USDT", "buy", "limit", 0.1, 3000.0, "margin")
        res = await o.get_open_orders()
        assert res.success is True
        types = sorted({x["market_type"] for x in res.data["orders"]})
        assert types == ["futures", "margin"]

    @pytest.mark.asyncio
    async def test_futures_symbol_normalized(self):
        """
        Futures emri sembolü BASE/QUOTE:SETTLE biçimine çevrilmeli.
        (KuCoin Futures 'kucoinfutures does not have market symbol PEPE/USDT' hatası fix'i)
        """
        from unittest.mock import MagicMock, AsyncMock
        o = _paper_orders()
        # markets'ta normalize hedefi var → aday geçerli kabul edilir
        fake_fut = MagicMock()
        fake_fut.markets = {"PEPE/USDT:USDT": {}}
        fake_fut.load_markets = AsyncMock()
        o.futures_exchange = fake_fut
        o.exchange = MagicMock()
        norm = await o._normalize_symbol("PEPE/USDT", "futures")
        assert norm == "PEPE/USDT:USDT"
        # spot/margin değişmemeli
        assert await o._normalize_symbol("PEPE/USDT", "spot") == "PEPE/USDT"
        assert await o._normalize_symbol("PEPE/USDT", "margin") == "PEPE/USDT"

    @pytest.mark.asyncio
    async def test_live_futures_order_uses_normalized_symbol(self):
        """Canlı futures emri ccxt'e normalize edilmiş sembolle gitmeli."""
        from unittest.mock import MagicMock, AsyncMock
        o = _paper_orders()
        o.mode = "live"
        fake_fut = MagicMock()
        fake_fut.markets = {"PEPE/USDT:USDT": {}}
        fake_fut.load_markets = AsyncMock()
        fake_fut.create_order = AsyncMock(return_value={"id": "F1", "status": "open"})
        o.futures_exchange = fake_fut
        o.exchange = MagicMock()
        r = await o.create_order("PEPE/USDT", "buy", "market", 1000000, None, "futures")
        assert r.success is True
        # create_order ilk argümanı (sembol) normalize edilmiş olmalı
        called_symbol = fake_fut.create_order.call_args[0][0]
        assert called_symbol == "PEPE/USDT:USDT"
        assert r.data["venue_symbol"] == "PEPE/USDT:USDT"

    @pytest.mark.asyncio
    async def test_futures_margin_mode_sent_and_fallback_on_330005(self):
        """
        Futures emrinde marginMode gönderilmeli; 330005 (mod uyuşmazlığı)
        alınırsa diğer modla otomatik yeniden denenmeli.
        (KuCoin hata: 'order's margin mode does not match the selected one')
        """
        from unittest.mock import MagicMock, AsyncMock
        o = _paper_orders()
        o.mode = "live"
        fake_fut = MagicMock()
        fake_fut.markets = {"PEPE/USDT:USDT": {}}
        fake_fut.load_markets = AsyncMock()
        # 1. çağrı (cross) 330005 fırlatır, 2. çağrı (isolated) başarılı
        fake_fut.create_order = AsyncMock(side_effect=[
            Exception('kucoinfutures {"msg":"...does not match...","code":"330005"}'),
            {"id": "F2", "status": "open"},
        ])
        o.futures_exchange = fake_fut
        o.exchange = MagicMock()
        r = await o.create_order("PEPE/USDT", "buy", "market", 1000000, None,
                                 "futures", "cross")
        assert r.success is True
        assert fake_fut.create_order.call_count == 2
        # ilk çağrı marginMode=cross, ikinci çağrı marginMode=isolated olmalı
        first_params = fake_fut.create_order.call_args_list[0][0][5]
        second_params = fake_fut.create_order.call_args_list[1][0][5]
        assert first_params.get("marginMode") == "cross"
        assert second_params.get("marginMode") == "isolated"
        assert r.data["margin_mode"] == "isolated"

    @pytest.mark.asyncio
    async def test_limit_requires_price(self):
        o = _paper_orders()
        r = await o.create_order("BTC/USDT", "buy", "limit", 0.001, None)
        assert r.success is False
        assert "fiyat" in r.error.lower()

    @pytest.mark.asyncio
    async def test_insufficient_balance(self):
        o = _paper_orders(balance=10.0, price=50000.0)
        r = await o.create_order("BTC/USDT", "buy", "market", 1.0)  # 50000 USDT gerekli
        assert r.success is False
        assert "yetersiz" in r.error.lower()

    @pytest.mark.asyncio
    async def test_below_min_notional(self):
        o = _paper_orders(price=50000.0)
        r = await o.create_order("BTC/USDT", "buy", "market", 0.00000001)
        assert r.success is False
        assert "minimum" in r.error.lower()

    @pytest.mark.asyncio
    async def test_rejected_when_bot_stopped(self):
        o = _paper_orders()
        o.bot_active = False
        r = await o.create_order("BTC/USDT", "buy", "market", 0.001)
        assert r.success is False
        assert "panic" in r.error.lower() or "durdurul" in r.error.lower()


class TestMarketOrder:
    """M3-C02 & M3-C07: Market order + paper motoru."""

    @pytest.mark.asyncio
    async def test_market_buy_fills_and_reduces_balance(self):
        o = _paper_orders(balance=10000.0, price=50000.0)
        r = await o.create_order("BTC/USDT", "buy", "market", 0.1)  # 5000 USDT
        assert r.success is True
        assert r.data["status"] == "filled"
        assert o.paper_balance_usdt == pytest.approx(5000.0)
        assert len(o.paper_history) == 1

    @pytest.mark.asyncio
    async def test_market_sell_increases_balance(self):
        o = _paper_orders(balance=1000.0, price=50000.0)
        r = await o.create_order("BTC/USDT", "sell", "market", 0.1)  # +5000
        assert r.success is True
        assert o.paper_balance_usdt == pytest.approx(6000.0)


class TestLimitOrder:
    """M3-C03 & M3-C04: Limit order açık kalır, listelenir."""

    @pytest.mark.asyncio
    async def test_limit_order_stays_open(self):
        o = _paper_orders(price=50000.0)
        r = await o.create_order("BTC/USDT", "buy", "limit", 0.01, 45000.0)
        assert r.success is True
        assert r.data["status"] == "open"
        oo = await o.get_open_orders()
        assert oo.data["count"] == 1

    @pytest.mark.asyncio
    async def test_open_orders_filter_by_symbol(self):
        o = _paper_orders(price=50000.0)
        await o.create_order("BTC/USDT", "buy", "limit", 0.01, 45000.0)
        oo = await o.get_open_orders("ETH/USDT")
        assert oo.data["count"] == 0


class TestCancel:
    """M3-C05: İptal."""

    @pytest.mark.asyncio
    async def test_cancel_open_order(self):
        o = _paper_orders(price=50000.0)
        r = await o.create_order("BTC/USDT", "buy", "limit", 0.01, 45000.0)
        c = await o.cancel_order(r.data["id"])
        assert c.success is True
        oo = await o.get_open_orders()
        assert oo.data["count"] == 0

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self):
        o = _paper_orders()
        c = await o.cancel_order("paper-does-not-exist")
        assert c.success is False


class TestPanicStop:
    """M3-C06: Panic stop."""

    @pytest.mark.asyncio
    async def test_panic_cancels_all_and_stops_bot(self):
        o = _paper_orders(price=50000.0)
        await o.create_order("BTC/USDT", "buy", "limit", 0.01, 45000.0)
        await o.create_order("BTC/USDT", "buy", "limit", 0.01, 44000.0)
        p = await o.panic_stop()
        assert p.success is True
        assert p.data["cancelled_orders"] == 2
        assert p.data["bot_active"] is False
        assert o.bot_active is False


class TestSwitchMode:
    """M3-C08: Mod geçişi."""

    @pytest.mark.asyncio
    async def test_switch_to_live(self):
        o = _paper_orders()
        r = await o.switch_mode("live")
        assert r.success is True
        assert r.data["current_mode"] == "live"
        assert o.mode == "live"

    @pytest.mark.asyncio
    async def test_switch_invalid_mode(self):
        o = _paper_orders()
        r = await o.switch_mode("turbo")
        assert r.success is False

    @pytest.mark.asyncio
    async def test_switch_reactivates_bot_after_panic(self):
        o = _paper_orders()
        o.bot_active = False
        await o.switch_mode("paper")
        assert o.bot_active is True


class TestHistory:
    """İşlem geçmişi (paper)."""

    @pytest.mark.asyncio
    async def test_history_records_filled_market_orders(self):
        o = _paper_orders(price=50000.0)
        await o.create_order("BTC/USDT", "buy", "market", 0.01)
        h = await o.get_history()
        assert h.success is True
        assert h.data["count"] == 1


class TestOpenOrdersCurrentPrice:
    """Açık emirlerde anlık fiyat ve fark hesaplama testleri."""

    @pytest.mark.asyncio
    async def test_open_orders_with_market_ticker(self):
        from unittest.mock import MagicMock
        from src.modules.module3_orders import KuCoinOrders
        from src.models.market import TickerResponse

        mock_market = MagicMock()
        mock_market.get_ticker = AsyncMock(return_value=TickerResponse(
            success=True,
            data={"symbol": "BTC/USDT", "last_price": 60000.0},
            error=None,
            timestamp="2026-09-21T00:00:00Z"
        ))

        orders = KuCoinOrders(market=mock_market)
        orders.mode = "paper"

        # Limit emir: 50,000 USDT (Piyasa 60,000 USDT)
        await orders.create_order("BTC/USDT", "buy", "limit", 0.01, 50000.0)
        res = await orders.get_open_orders()
        assert res.success is True
        assert res.data["count"] == 1

        ord0 = res.data["orders"][0]
        assert ord0["current_price"] == 60000.0
        assert ord0["price_diff"] == 10000.0
        assert ord0["price_diff_percent"] == 20.0

    @pytest.mark.asyncio
    async def test_open_orders_negative_diff(self):
        from unittest.mock import MagicMock
        from src.modules.module3_orders import KuCoinOrders
        from src.models.market import TickerResponse

        mock_market = MagicMock()
        mock_market.get_ticker = AsyncMock(return_value=TickerResponse(
            success=True,
            data={"symbol": "ETH/USDT", "last_price": 2500.0},
            error=None,
            timestamp="2026-09-21T00:00:00Z"
        ))

        orders = KuCoinOrders(market=mock_market)
        orders.mode = "paper"

        # Satış emri: 3,000 USDT (Piyasa 2,500 USDT -> fark: -500 USDT, %-16.6667)
        await orders.create_order("ETH/USDT", "sell", "limit", 1.0, 3000.0)
        res = await orders.get_open_orders()
        ord0 = res.data["orders"][0]
        assert ord0["current_price"] == 2500.0
        assert ord0["price_diff"] == -500.0
        assert round(ord0["price_diff_percent"], 2) == -16.67

    @pytest.mark.asyncio
    async def test_open_orders_no_market_graceful(self):
        from src.modules.module3_orders import KuCoinOrders

        orders = KuCoinOrders(market=None)
        orders.mode = "paper"
        await orders.create_order("BTC/USDT", "buy", "limit", 0.01, 50000.0)
        res = await orders.get_open_orders()
        assert res.success is True
        ord0 = res.data["orders"][0]
        assert ord0["current_price"] is None
        assert ord0["price_diff"] is None
        assert ord0["price_diff_percent"] is None


class TestPositionsAndEntryStopPrices:
    """Giriş fiyatları, stop fiyatları ve açık pozisyonlar testleri."""

    @pytest.mark.asyncio
    async def test_bracket_order_tracks_position_and_entry_stop_prices(self):
        from unittest.mock import MagicMock
        from src.modules.module3_orders import KuCoinOrders
        from src.models.market import TickerResponse

        mock_market = MagicMock()
        mock_market.get_ticker = AsyncMock(return_value=TickerResponse(
            success=True,
            data={"symbol": "BTC/USDT", "last_price": 62000.0},
            error=None,
            timestamp="2026-09-21T00:00:00Z"
        ))

        orders = KuCoinOrders(market=mock_market)
        orders.mode = "paper"
        orders._current_price = AsyncMock(return_value=60000.0)

        # 100 USDT bracket order: Giriş 60,000, SL 58,000, TP1 63,000, TP2 65,000
        res = await orders.create_bracket_order(
            symbol="BTC/USDT", side="buy", usdt_amount=100.0,
            entry_price=60000.0, stop_loss_price=58000.0,
            tp1_price=63000.0, tp2_price=65000.0, market_type="spot"
        )
        assert res.success is True

        # 1. Pozisyonları sorgula
        pos_res = await orders.get_positions()
        assert pos_res["success"] is True
        assert pos_res["data"]["count"] == 1
        pos = pos_res["data"]["positions"][0]
        assert pos["symbol"] == "BTC/USDT"
        assert pos["entry_price"] == 60000.0
        assert pos["stop_loss_price"] == 58000.0
        assert pos["current_price"] == 62000.0
        assert pos["tp1_price"] == 63000.0
        assert pos["tp2_price"] == 65000.0
        assert pos["unrealized_pnl"] > 0
        assert round(pos["pnl_percent"], 2) == 3.33

        # 2. Açık emirlerde giriş ve stop fiyatlarını kontrol et
        oo_res = await orders.get_open_orders()
        assert oo_res.success is True
        assert oo_res.data["count"] == 3  # TP1, TP2, SL
        for o in oo_res.data["orders"]:
            assert o["entry_price"] == 60000.0
            assert o["stop_loss_price"] == 58000.0
            assert "bracket_leg" in o
            assert o["bracket_leg"] in ("tp1", "tp2", "sl")
            assert o["current_price"] == 62000.0

    @pytest.mark.asyncio
    async def test_panic_stop_clears_positions(self):
        from unittest.mock import MagicMock
        from src.modules.module3_orders import KuCoinOrders
        from src.models.market import TickerResponse

        mock_market = MagicMock()
        mock_market.get_ticker = AsyncMock(return_value=TickerResponse(
            success=True,
            data={"symbol": "BTC/USDT", "last_price": 60000.0},
            error=None,
            timestamp="2026-09-21T00:00:00Z"
        ))

        orders = KuCoinOrders(market=mock_market)
        orders.mode = "paper"
        orders._current_price = AsyncMock(return_value=60000.0)

        await orders.create_bracket_order(
            symbol="BTC/USDT", side="buy", usdt_amount=100.0,
            entry_price=60000.0, stop_loss_price=58000.0,
            tp1_price=63000.0, tp2_price=65000.0, market_type="spot"
        )
        assert len(orders.paper_positions) == 1

        p = await orders.panic_stop()
        assert p.success is True
        assert len(orders.paper_positions) == 0




class TestPnLReport:
    """Kar/Zarar (P&L) raporu — ortalama maliyet yöntemi."""

    @pytest.mark.asyncio
    async def test_realized_pnl_average_cost(self):
        """Al 1@100, al 1@200 (ort 150), sat 1@300 => realized (300-150)*1 = 150."""
        o = _paper_orders()
        o.paper_history = [
            {"symbol": "BTC/USDT", "side": "buy", "amount": 1, "filled_price": 100.0, "status": "filled", "created_at": "t1"},
            {"symbol": "BTC/USDT", "side": "buy", "amount": 1, "filled_price": 200.0, "status": "filled", "created_at": "t2"},
            {"symbol": "BTC/USDT", "side": "sell", "amount": 1, "filled_price": 300.0, "status": "filled", "created_at": "t3"},
        ]
        r = await o.get_pnl_report()
        assert r.success is True
        assert r.data["total_realized_pnl"] == 150.0
        sym = r.data["symbols"][0]
        assert sym["symbol"] == "BTC/USDT"
        assert sym["realized_pnl"] == 150.0
        assert sym["open_qty"] == 1.0  # 2 alım - 1 satım

    @pytest.mark.asyncio
    async def test_pnl_loss(self):
        """Al 1@200, sat 1@100 => realized -100."""
        o = _paper_orders()
        o.paper_history = [
            {"symbol": "ETH/USDT", "side": "buy", "amount": 1, "filled_price": 200.0, "status": "filled", "created_at": "t1"},
            {"symbol": "ETH/USDT", "side": "sell", "amount": 1, "filled_price": 100.0, "status": "filled", "created_at": "t2"},
        ]
        r = await o.get_pnl_report()
        assert r.data["total_realized_pnl"] == -100.0

    @pytest.mark.asyncio
    async def test_pnl_ignores_open_orders(self):
        """Dolmayan (open) emirler P&L'e dahil edilmemeli."""
        o = _paper_orders()
        o.paper_history = [
            {"symbol": "BTC/USDT", "side": "buy", "amount": 1, "price": 100.0, "status": "open", "created_at": "t1"},
        ]
        r = await o.get_pnl_report()
        assert r.success is True
        assert r.data["total_realized_pnl"] == 0.0
        assert r.data["symbol_count"] == 0

    @pytest.mark.asyncio
    async def test_pnl_fee_deducted(self):
        """Komisyon (fee) realized P&L'den düşülmeli."""
        o = _paper_orders()
        o.paper_history = [
            {"symbol": "BTC/USDT", "side": "buy", "amount": 1, "filled_price": 100.0, "status": "filled", "created_at": "t1"},
            {"symbol": "BTC/USDT", "side": "sell", "amount": 1, "filled_price": 200.0, "status": "filled", "created_at": "t2", "fee": {"cost": 5.0}},
        ]
        r = await o.get_pnl_report()
        # (200-100)*1 - 5 fee = 95
        assert r.data["total_realized_pnl"] == 95.0
