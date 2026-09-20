"""
KuCoin Al-Sat Botu — Emir Düzenleme (Amend) & Dinamik Öneri Motoru Testleri
MODULE_3_SPEC 2.6 & 2.7.
"""

import pytest
from unittest.mock import AsyncMock


def _paper_orders(price=50000.0):
    from src.modules.module3_orders import KuCoinOrders
    o = KuCoinOrders()
    o.mode = "paper"
    o.paper_balance_usdt = 100000.0
    o.bot_active = True
    o._current_price = AsyncMock(return_value=price)
    return o


class TestAmendOrder:
    @pytest.mark.asyncio
    async def test_amend_price_and_amount(self):
        o = _paper_orders()
        r = await o.create_order("BTC/USDT", "buy", "limit", 0.01, 48000)
        oid = r.data["id"]
        a = await o.amend_order(oid, price=47000, amount=0.02)
        assert a.success is True
        assert a.data["price"] == 47000
        assert a.data["amount"] == 0.02
        assert a.data["notional_usdt"] == pytest.approx(940.0)

    @pytest.mark.asyncio
    async def test_amend_price_only(self):
        o = _paper_orders()
        r = await o.create_order("BTC/USDT", "buy", "limit", 0.01, 48000)
        a = await o.amend_order(r.data["id"], price=49000)
        assert a.success is True
        assert a.data["price"] == 49000
        assert a.data["amount"] == 0.01  # değişmedi

    @pytest.mark.asyncio
    async def test_amend_nonexistent(self):
        o = _paper_orders()
        a = await o.amend_order("paper-yok", price=1)
        assert a.success is False

    @pytest.mark.asyncio
    async def test_amend_requires_field(self):
        o = _paper_orders()
        r = await o.create_order("BTC/USDT", "buy", "limit", 0.01, 48000)
        a = await o.amend_order(r.data["id"])  # ne fiyat ne miktar
        assert a.success is False


class TestRecommendationEngine:
    @pytest.mark.asyncio
    async def test_sl_near_warning(self):
        """Fiyat SL'ye <%1 yakınsa SL_NEAR uyarısı üretilmeli."""
        from src.modules.recommendations import RecommendationEngine
        from src.models.market import TickerResponse
        from src.models.orders import OpenOrdersResponse
        orders = AsyncMock()
        orders.get_open_orders.return_value = OpenOrdersResponse(
            success=True,
            data={"count": 1, "orders": [
                {"id": "o1", "symbol": "BTC/USDT", "side": "sell", "price": 50000.0,
                 "bracket_leg": "sl"}]},
            error=None, timestamp="2026-01-01T00:00:00Z")
        market = AsyncMock()
        market.get_ticker.return_value = TickerResponse(
            success=True, data={"last_price": 50200.0}, error=None,
            timestamp="2026-01-01T00:00:00Z")  # %0.4 yakın
        rec = RecommendationEngine(orders=orders, market=market)
        res = await rec.get_recommendations()
        assert res["success"] is True
        assert any(r["type"] == "SL_NEAR" for r in res["data"]["recommendations"])

    @pytest.mark.asyncio
    async def test_no_recommendations_when_far(self):
        """Fiyat hedeflerden uzaksa öneri üretilmemeli."""
        from src.modules.recommendations import RecommendationEngine
        from src.models.market import TickerResponse
        from src.models.orders import OpenOrdersResponse
        orders = AsyncMock()
        orders.get_open_orders.return_value = OpenOrdersResponse(
            success=True,
            data={"count": 1, "orders": [
                {"id": "o1", "symbol": "BTC/USDT", "side": "sell", "price": 60000.0,
                 "bracket_leg": "sl"}]},
            error=None, timestamp="2026-01-01T00:00:00Z")
        market = AsyncMock()
        market.get_ticker.return_value = TickerResponse(
            success=True, data={"last_price": 50000.0}, error=None,
            timestamp="2026-01-01T00:00:00Z")  # uzak
        rec = RecommendationEngine(orders=orders, market=market)
        res = await rec.get_recommendations()
        assert res["data"]["count"] == 0

    @pytest.mark.asyncio
    async def test_apply_recommendation_calls_amend(self):
        from src.modules.recommendations import RecommendationEngine
        from src.models.orders import OrderCreateResponse
        orders = AsyncMock()
        orders.amend_order.return_value = OrderCreateResponse(
            success=True, data={"id": "o1", "price": 49000}, error=None,
            timestamp="2026-01-01T00:00:00Z")
        rec = RecommendationEngine(orders=orders, market=AsyncMock())
        res = await rec.apply_recommendation("o1", new_price=49000)
        assert res["success"] is True
        orders.amend_order.assert_awaited_once()
