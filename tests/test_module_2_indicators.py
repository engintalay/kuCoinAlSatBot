"""
KuCoin Al-Sat Botu — Modül 2 İndikatör Katmanı Testleri
Trend (EMA/SMA), Momentum (RSI/MACD), Volatilite (ATR).
"""

import pandas as pd
import pytest


def _make_df(closes, highs=None, lows=None):
    """Test için OHLCV DataFrame üretir."""
    n = len(closes)
    highs = highs or [c + 1 for c in closes]
    lows = lows or [c - 1 for c in closes]
    return pd.DataFrame({
        "timestamp": list(range(n)),
        "open": closes,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [100.0] * n,
    })


class TestTrend:
    def test_bullish_golden_cross(self):
        """Sürekli artan fiyatta BULLISH + GOLDEN_CROSS beklenir."""
        from src.modules.indicators.trend import compute_trend
        closes = [float(i) for i in range(1, 261)]  # 1..260 artan
        result = compute_trend(_make_df(closes))
        assert result["regime"] == "BULLISH"
        assert result["cross"] == "GOLDEN_CROSS"
        assert result["ema"]["200"] is not None

    def test_bearish_death_cross(self):
        """Sürekli azalan fiyatta BEARISH + DEATH_CROSS beklenir."""
        from src.modules.indicators.trend import compute_trend
        closes = [float(i) for i in range(260, 0, -1)]  # 260..1 azalan
        result = compute_trend(_make_df(closes))
        assert result["regime"] == "BEARISH"
        assert result["cross"] == "DEATH_CROSS"

    def test_insufficient_data_returns_none_ema200(self):
        """Yetersiz veride EMA200 None dönmeli, çökmemeli."""
        from src.modules.indicators.trend import compute_trend
        closes = [float(i) for i in range(1, 30)]
        result = compute_trend(_make_df(closes))
        assert result["ema"]["200"] is None
        assert result["ema"]["20"] is not None


class TestMomentum:
    def test_rsi_all_gains_is_100(self):
        """Sürekli artışta RSI 100'e yakın olmalı."""
        from src.modules.indicators.momentum import compute_momentum
        closes = [float(i) for i in range(1, 40)]
        result = compute_momentum(_make_df(closes))
        assert result["rsi"] is not None
        assert result["rsi"]["value"] >= 99.0
        assert result["rsi"]["regime"] == "OVERBOUGHT"

    def test_rsi_all_losses_is_low(self):
        """Sürekli düşüşte RSI çok düşük (oversold) olmalı."""
        from src.modules.indicators.momentum import compute_momentum
        closes = [float(i) for i in range(40, 1, -1)]
        result = compute_momentum(_make_df(closes))
        assert result["rsi"]["value"] <= 1.0
        assert result["rsi"]["regime"] == "OVERSOLD"

    def test_macd_present_with_enough_data(self):
        """26+ mum ile MACD hesaplanmalı."""
        from src.modules.indicators.momentum import compute_momentum
        closes = [float(i) for i in range(1, 40)]
        result = compute_momentum(_make_df(closes))
        assert result["macd"] is not None
        assert "line" in result["macd"]
        assert "histogram" in result["macd"]

    def test_macd_none_when_insufficient(self):
        """26'dan az mumda MACD None dönmeli."""
        from src.modules.indicators.momentum import compute_momentum
        closes = [float(i) for i in range(1, 20)]
        result = compute_momentum(_make_df(closes))
        assert result["macd"] is None


class TestVolatility:
    def test_atr_constant_range(self):
        """Sabit H-L aralığında ATR o aralığa yakınsamalı."""
        from src.modules.indicators.volatility import compute_volatility
        n = 30
        closes = [100.0] * n
        highs = [101.0] * n   # H-L = 2, prev_close=100 -> TR=1..2
        lows = [99.0] * n
        result = compute_volatility(_make_df(closes, highs, lows))
        assert result["atr"] is not None
        assert 1.5 <= result["atr"] <= 2.5
        assert result["stop_loss_2x"] == round(2.0 * result["atr"], 8)

    def test_atr_insufficient_data(self):
        """15'ten az mumda ATR None dönmeli."""
        from src.modules.indicators.volatility import compute_volatility
        closes = [100.0] * 10
        result = compute_volatility(_make_df(closes))
        assert result["atr"] is None


class TestGetIndicatorsIntegration:
    """module2_market.get_indicators (mock'lu) testleri."""

    @pytest.mark.asyncio
    async def test_indicators_degraded_when_few_candles(self):
        """<250 kapanmış mumda data_quality DEGRADED olmalı."""
        from unittest.mock import AsyncMock
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        # 60 confirmed + 1 açık mum
        candles = [{"timestamp": i, "open": 100.0, "high": 101.0, "low": 99.0,
                    "close": 100.0 + i, "volume": 100.0, "confirmed": True}
                   for i in range(60)]
        candles.append({"timestamp": 60, "open": 100, "high": 101, "low": 99,
                        "close": 160.0, "volume": 100.0, "confirmed": False})
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True,
            data={"symbol": "BTC/USDT", "timeframe": "1h",
                  "count": len(candles), "candles": candles},
            error=None, timestamp="2026-01-01T00:00:00Z",
        ))
        result = await m.get_indicators("BTC/USDT", "1h", 300)
        assert result.success is True
        assert result.data["data_quality"] == "DEGRADED"
        assert result.data["confirmed_candles"] == 60
        assert "trend" in result.data["indicators"]

    @pytest.mark.asyncio
    async def test_indicators_unavailable_when_too_few(self):
        """30'dan az kapanmış mumda UNAVAILABLE + success False."""
        from unittest.mock import AsyncMock
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        candles = [{"timestamp": i, "open": 100.0, "high": 101.0, "low": 99.0,
                    "close": 100.0, "volume": 100.0, "confirmed": True}
                   for i in range(10)]
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True,
            data={"candles": candles}, error=None,
            timestamp="2026-01-01T00:00:00Z",
        ))
        result = await m.get_indicators("BTC/USDT", "1h", 300)
        assert result.success is False
        assert result.data["data_quality"] == "UNAVAILABLE"
