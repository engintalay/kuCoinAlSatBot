"""
KuCoin Al-Sat Botu — Akıllı Paket Emir (Bracket Order) & Trade Setup Testleri
MODULE_3_SPEC 2.5.
"""

import pytest
from unittest.mock import AsyncMock


def _paper_orders(balance=10000.0, price=50000.0):
    from src.modules.module3_orders import KuCoinOrders
    o = KuCoinOrders()
    o.mode = "paper"
    o.paper_balance_usdt = balance
    o.bot_active = True
    o._current_price = AsyncMock(return_value=price)
    return o


class TestBracketOrder:
    @pytest.mark.asyncio
    async def test_bracket_creates_four_legs(self):
        """Bracket: giriş + TP1 + TP2 + SL legs oluşturmalı."""
        o = _paper_orders(price=50000.0)
        r = await o.create_bracket_order(
            "BTC/USDT", "buy", 1000.0,
            entry_price=50000.0, stop_loss_price=49000.0,
            tp1_price=51500.0, tp2_price=53000.0)
        assert r.success is True
        assert r.data["bracket_id"].startswith("bracket-")
        assert set(r.data["legs"].keys()) == {"entry", "tp1", "tp2", "sl"}
        # 3 çıkış emri açık kalmalı (TP1, TP2, SL)
        oo = await o.get_open_orders()
        assert oo.data["count"] == 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mtype", ["spot", "margin", "futures"])
    async def test_bracket_propagates_market_type(self, mtype):
        """Bracket seçilen market_type'ı hem pakete hem tüm bacaklara yaymalı."""
        o = _paper_orders(price=50000.0)
        r = await o.create_bracket_order(
            "BTC/USDT", "buy", 1000.0,
            entry_price=50000.0, stop_loss_price=49000.0,
            tp1_price=51500.0, tp2_price=53000.0, market_type=mtype)
        assert r.success is True
        assert r.data["market_type"] == mtype
        assert r.data["legs"]["entry"]["market_type"] == mtype
        # açık çıkış emirleri de aynı market_type ile etiketli olmalı
        oo = await o.get_open_orders()
        assert all(x["market_type"] == mtype for x in oo.data["orders"])

    @pytest.mark.asyncio
    async def test_bracket_futures_with_leverage(self):
        """Bracket futures modunda kaldıraç ve margin_mode bilgisini taşımalı."""
        o = _paper_orders(price=50000.0)
        r = await o.create_bracket_order(
            "BTC/USDT", "buy", 1000.0,
            entry_price=50000.0, stop_loss_price=49000.0,
            tp1_price=51500.0, tp2_price=53000.0,
            market_type="futures", margin_mode="cross", leverage=10.0,
        )
        assert r.success is True
        assert r.data["market_type"] == "futures"
        assert r.data["leverage"] == 10.0
        assert r.data["margin_mode"] == "cross"
        assert r.data["legs"]["entry"]["leverage"] == 10.0
        assert o.paper_positions["BTC/USDT-futures"]["leverage"] == 10.0
        pos_res = await o.get_positions()
        assert pos_res["data"]["positions"][0]["leverage"] == 10.0

    @pytest.mark.asyncio
    async def test_single_order_futures_with_leverage(self):
        """Tekil emir futures modunda kaldıraç ve margin_mode taşımalı."""
        o = _paper_orders(price=50000.0)
        r = await o.create_order(
            "BTC/USDT", "buy", "limit", 0.01, 50000.0,
            market_type="futures", margin_mode="isolated", leverage=20.0,
        )
        assert r.success is True
        assert r.data["market_type"] == "futures"
        assert r.data["margin_mode"] == "isolated"
        assert r.data["leverage"] == 20.0

    @pytest.mark.asyncio
    async def test_bracket_invalid_market_type(self):
        """Geçersiz market_type ile bracket reddedilmeli."""
        o = _paper_orders(price=50000.0)
        r = await o.create_bracket_order(
            "BTC/USDT", "buy", 1000.0,
            entry_price=50000.0, stop_loss_price=49000.0,
            tp1_price=51500.0, tp2_price=53000.0, market_type="perp")
        assert r.success is False
        assert "piyasa türü" in r.error.lower()

    @pytest.mark.asyncio
    async def test_bracket_risk_reward_calc(self):
        """Risk ve kâr tutarları doğru hesaplanmalı."""
        o = _paper_orders(price=50000.0)
        # amount = 1000/50000 = 0.02; risk = 0.02*(50000-49000)=20
        r = await o.create_bracket_order(
            "BTC/USDT", "buy", 1000.0, 50000.0, 49000.0, 51500.0, 53000.0)
        assert r.data["risk_usdt"] == pytest.approx(20.0, abs=0.01)
        # gain_tp1 = (0.02*0.5)*(51500-50000) = 15
        assert r.data["gain_tp1_usdt"] == pytest.approx(15.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_bracket_insufficient_balance(self):
        o = _paper_orders(balance=50.0, price=50000.0)
        r = await o.create_bracket_order(
            "BTC/USDT", "buy", 1000.0, 50000.0, 49000.0, 51500.0, 53000.0)
        assert r.success is False
        assert "yetersiz" in r.error.lower()

    @pytest.mark.asyncio
    async def test_bracket_invalid_usdt(self):
        o = _paper_orders()
        r = await o.create_bracket_order("BTC/USDT", "buy", 0, 50000, 49000, 51500, 53000)
        assert r.success is False

    @pytest.mark.asyncio
    async def test_bracket_live_futures_single_contract(self):
        """Live futures 1 kontrat olduğunda TP1 tüm pozisyonu almalı, TP2 atlanmalı ve SL stop_market olmalı."""
        o = _paper_orders()
        o.mode = "live"
        calls = []

        async def mock_create_live_order(symbol, side, order_type, amount, price, market_type="spot",
                                         margin_mode="cross", leverage=None, stop_loss_price=None,
                                         is_stop=False, reduce_only=False):
            calls.append({
                "symbol": symbol, "side": side, "type": order_type,
                "amount": amount, "price": price, "is_stop": is_stop,
                "reduce_only": reduce_only, "stop_loss_price": stop_loss_price,
            })
            from src.models.orders import OrderCreateResponse
            from src.utils.time_sync import timestamp
            return OrderCreateResponse(
                success=True,
                data={
                    "id": f"live-{len(calls)}", "symbol": symbol, "side": side,
                    "type": order_type, "amount": amount, "price": price,
                    "market_type": market_type, "created_at": timestamp()
                },
                error=None, timestamp=timestamp()
            )

        o._create_live_order = mock_create_live_order
        r = await o.create_bracket_order(
            "SUI/USDT", "buy", usdt_amount=1.25,
            entry_price=1.25, stop_loss_price=1.15,
            tp1_price=1.35, tp2_price=1.45,
            market_type="futures", margin_mode="cross", leverage=3.0
        )
        assert r.success is True
        legs = r.data["legs"]
        assert "entry" in legs
        assert "tp1" in legs
        assert "tp2" in legs
        assert "sl" in legs
        # TP1 1 kontrat ve reduce_only
        assert legs["tp1"]["amount"] == 1
        # TP2 atlanmış olmalı
        assert legs["tp2"].get("status") == "skipped"
        # SL is_stop ve reduce_only ile çağrılmış olmalı
        sl_call = [c for c in calls if c["is_stop"] is True][0]
        assert sl_call["amount"] == 1
        assert sl_call["stop_loss_price"] == 1.15
        assert sl_call["reduce_only"] is True

    @pytest.mark.asyncio
    async def test_set_position_tp_sl(self):
        """set_position_tp_sl metodu açık pozisyona TP ve SL bağlayabilmeli."""
        o = _paper_orders()
        calls = []

        async def mock_create_order(symbol, side, order_type, amount, price, market_type="spot",
                                    margin_mode="cross", leverage=None, entry_price=None,
                                    stop_loss_price=None, is_stop=False, reduce_only=False):
            calls.append({
                "symbol": symbol, "side": side, "type": order_type, "amount": amount,
                "price": price, "is_stop": is_stop, "reduce_only": reduce_only,
                "stop_loss_price": stop_loss_price
            })
            from src.models.orders import OrderCreateResponse
            from src.utils.time_sync import timestamp
            return OrderCreateResponse(
                success=True,
                data={"id": "pos-tp-sl-1", "symbol": symbol, "side": side, "amount": amount},
                error=None, timestamp=timestamp()
            )

        o.create_order = mock_create_order
        res = await o.set_position_tp_sl(
            "SUI/USDT:USDT", market_type="futures",
            tp_price=1.35, sl_price=1.15, amount=1.0, side="long", leverage=3.0
        )
        assert res["success"] is True
        assert len(calls) == 2
        tp_call = calls[0]
        sl_call = calls[1]
        assert tp_call["price"] == 1.35
        assert tp_call["reduce_only"] is True
        assert sl_call["is_stop"] is True
        assert sl_call["stop_loss_price"] == 1.15
        assert sl_call["reduce_only"] is True


class TestTradeSetup:
    @pytest.mark.asyncio
    async def test_trade_setup_long_levels(self):
        """Long setup: SL < entry < TP1 < TP2 sıralı olmalı."""
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        # 60 mum, ATR hesaplanabilir
        candles = [{"timestamp": i, "open": 100, "high": 105, "low": 95,
                    "close": 100 + (i % 5), "volume": 100, "confirmed": True}
                   for i in range(60)]
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True, data={"candles": candles}, error=None,
            timestamp="2026-01-01T00:00:00Z"))
        res = await m.get_trade_setup("BTC/USDT", "1h", "buy")
        assert res.success is True
        s = res.data["trade_setup"]
        assert s["stop_loss_price"] < s["entry_price"] < s["tp1_price"] < s["tp2_price"]
        assert s["risk_reward_ratio"] == 3.0

    @pytest.mark.asyncio
    async def test_trade_setup_short_levels(self):
        """Short setup: TP2 < TP1 < entry < SL sıralı olmalı."""
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        candles = [{"timestamp": i, "open": 100, "high": 105, "low": 95,
                    "close": 100 + (i % 5), "volume": 100, "confirmed": True}
                   for i in range(60)]
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True, data={"candles": candles}, error=None,
            timestamp="2026-01-01T00:00:00Z"))
        res = await m.get_trade_setup("BTC/USDT", "1h", "sell")
        s = res.data["trade_setup"]
        assert s["tp2_price"] < s["tp1_price"] < s["entry_price"] < s["stop_loss_price"]

    @pytest.mark.asyncio
    async def test_trade_setup_insufficient(self):
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        candles = [{"timestamp": i, "open": 100, "high": 101, "low": 99,
                    "close": 100, "volume": 100, "confirmed": True} for i in range(10)]
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True, data={"candles": candles}, error=None,
            timestamp="2026-01-01T00:00:00Z"))
        res = await m.get_trade_setup("BTC/USDT", "1h", "buy")
        assert res.success is False
