"""
KuCoin Al-Sat Botu — Çoklu Piyasa (Spot, Margin, Futures) ve Sub-15m Analiz Testleri
MODULE_2_SPEC M2-C18 (Sub-15m: 1m, 3m, 5m), M2-C19 (Spot/Margin/Futures) ve M2-C20 (Trade Setup & Grafik)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.modules.module2_market import KuCoinMarket, SUPPORTED_TIMEFRAMES
from src.modules.analysis.scoring_engine import compute_score


@pytest.fixture
def client():
    return TestClient(app)


def _make_candles(count=50, base_price=50000.0):
    return [
        [
            1600000000000 + i * 60000,
            base_price + i * 2,
            base_price + i * 2 + 5,
            base_price + i * 2 - 5,
            base_price + i * 2 + 1,
            100 + i,
        ]
        for i in range(count)
    ]


class TestSub15mTimeframes:
    """15 dakikanın altındaki zaman dilimleri testleri (M2-C18)."""

    def test_supported_timeframes_contains_sub15m(self):
        assert "1m" in SUPPORTED_TIMEFRAMES
        assert "3m" in SUPPORTED_TIMEFRAMES
        assert "5m" in SUPPORTED_TIMEFRAMES

    @pytest.mark.asyncio
    async def test_get_candles_sub15m_success(self):
        m = KuCoinMarket()
        mock_ex = AsyncMock()
        mock_ex.fetch_ohlcv.return_value = _make_candles(10)
        m.exchange = mock_ex

        res_1m = await m.get_candles("BTC/USDT", "1m", limit=10)
        assert res_1m.success is True
        assert res_1m.data["timeframe"] == "1m"

        res_5m = await m.get_candles("BTC/USDT", "5m", limit=10)
        assert res_5m.success is True
        assert res_5m.data["timeframe"] == "5m"

    @pytest.mark.asyncio
    async def test_dynamic_mtf_sub15m_chain(self):
        """15m altı zaman dilimi seçildiğinde MTF zinciri (1h, 15m, base) olmalı."""
        m = KuCoinMarket()
        m._all_features = AsyncMock(return_value={
            "confirmed_candles": 50,
            "trend": {"price": 50000.0, "ema20": 49900.0, "ema50": 49800.0, "direction": 1},
            "momentum": {"rsi": {"value": 55.0}},
            "volatility": {"atr": 200.0},
            "strength": {"adx": {"value": 28.0, "plus_di": 25.0, "minus_di": 15.0}},
            "volume": {},
            "levels": {},
            "structure": {},
        })

        res = await m.get_mtf("BTC/USDT", base_timeframe="5m")
        assert res.success is True
        assert res.data["timeframe_chain"] == ["1h", "15m", "5m"]
        assert "5m" in res.data["timeframes"]


class TestMarketTypes:
    """Spot, Margin ve Futures piyasa türleri testleri (M2-C19)."""

    @pytest.mark.asyncio
    async def test_futures_ticker(self):
        m = KuCoinMarket()
        m.derivatives = MagicMock()
        m.derivatives.get_futures_ticker = AsyncMock(return_value={
            "last": 65400.0,
            "high": 66000.0,
            "low": 64800.0,
            "baseVolume": 1500.0,
            "quoteVolume": 98000000.0,
            "percentage": 1.25,
            "bid": 65399.0,
            "ask": 65401.0,
        })

        res = await m.get_ticker("BTC/USDT", market_type="futures")
        assert res.success is True
        assert res.data["market_type"] == "futures"
        assert res.data["last_price"] == 65400.0

    @pytest.mark.asyncio
    async def test_futures_candles_and_derivatives(self):
        m = KuCoinMarket()
        m.derivatives = MagicMock()
        m.derivatives.get_futures_ohlcv = AsyncMock(return_value=_make_candles(40))
        m.derivatives.get_derivatives = AsyncMock(return_value={
            "available": True,
            "funding_rate": {"value": 0.0001, "status": "NORMAL"},
            "open_interest": {"amount": 50000000.0},
        })

        res = await m.get_candles("BTC/USDT", "15m", limit=40, market_type="futures")
        assert res.success is True
        assert res.data["market_type"] == "futures"
        assert res.data["count"] == 40

        feats = await m._all_features("BTC/USDT", "15m", 40, market_type="futures")
        assert feats is not None
        assert "derivatives" in feats
        assert feats["derivatives"]["available"] is True

    @pytest.mark.asyncio
    async def test_scoring_with_futures_and_margin(self):
        indicators = {
            "trend": {"ema50": 50000.0, "ema200": 48000.0, "price": 51000.0},
            "momentum": {"rsi": {"value": 58.0}},
            "strength": {"adx": {"value": 26.0, "plus_di": 22.0, "minus_di": 12.0}},
            "volume": {},
            "structure": {},
            "derivatives": {
                "available": True,
                "funding_rate": {"value": -0.0005, "status": "OVERHEATED_SHORT"},
                "open_interest": {"amount": 25000000.0},
            },
        }

        # Futures skoru: negatif fonlama short squeeze nedeniyle boğa puanı ekler
        fut_score = compute_score(indicators, market_type="futures")
        assert fut_score["market_type"] == "futures"
        assert any("fonlama" in r.lower() for r in fut_score["reasons"])

        # Margin skoru: marjin risk uyarısı eklenir
        margin_score = compute_score(indicators, market_type="margin")
        assert margin_score["market_type"] == "margin"
        assert any("marjin" in w.lower() for w in margin_score["warnings"])

    @pytest.mark.asyncio
    async def test_trade_setup_liquidation_calculation(self):
        """Futures/Margin için kaldıraç ve tahmini likidasyon seviyesi hesaplanmalı."""
        m = KuCoinMarket()
        m._all_features = AsyncMock(return_value={
            "confirmed_candles": 60,
            "trend": {"price": 60000.0},
            "volatility": {"atr": 1000.0},
            "momentum": {},
            "strength": {},
            "volume": {},
            "levels": {},
            "structure": {},
            "derivatives": {"available": True},
        })

        # Long Futures (5x kaldıraç): Likidasyon ~%18 aşağıda olmalı (60000 * 0.82 = 49200)
        res_long = await m.get_trade_setup("BTC/USDT", "1h", side="buy", market_type="futures", leverage=5.0)
        assert res_long.success is True
        ts_long = res_long.data["trade_setup"]
        assert ts_long["entry_price"] == 60000.0
        assert ts_long["stop_loss_price"] == 58500.0  # 60000 - 1.5 * 1000
        assert ts_long["tp1_price"] == 62250.0        # 60000 + 1.5 * 1500
        assert ts_long["est_liquidation_price"] == 49200.0
        assert ts_long["liquidation_distance_percent"] == 18.0

        # Short Margin (10x kaldıraç): Likidasyon yukarıda olmalı (60000 * 1.09 = 65400)
        res_short = await m.get_trade_setup("BTC/USDT", "1h", side="sell", market_type="margin", leverage=10.0)
        assert res_short.success is True
        ts_short = res_short.data["trade_setup"]
        assert ts_short["est_liquidation_price"] == 65400.0
        assert ts_short["liquidation_distance_percent"] == 9.0


class TestMarketAPIEndpoints:
    """REST API endpoint'lerinde market_type ve timeframe parametreleri testleri."""

    def test_api_candles_sub15m_and_market_type(self, client):
        r = client.get("/api/v1/market/candles?symbol=BTC/USDT&timeframe=5m&market_type=futures&limit=10")
        assert r.status_code == 200
        body = r.json()
        assert "success" in body

    def test_api_score_with_market_type(self, client):
        r = client.get("/api/v1/market/analysis/score?symbol=BTC/USDT&timeframe=1h&market_type=margin")
        assert r.status_code == 200
        body = r.json()
        assert "success" in body

    def test_api_trade_setup_with_market_type_and_leverage(self, client):
        r = client.get("/api/v1/market/trade-setup?symbol=BTC/USDT&timeframe=1h&side=buy&market_type=futures&leverage=5.0")
        assert r.status_code == 200
        body = r.json()
        assert "success" in body
