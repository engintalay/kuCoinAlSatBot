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
