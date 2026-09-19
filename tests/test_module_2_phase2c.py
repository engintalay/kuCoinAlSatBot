"""
KuCoin Al-Sat Botu — Modül 2 Faz 2c Testleri
Ek momentum osilatörleri (StochRSI, CCI, Williams %R, ROC) ve türev veriler.
"""

import pandas as pd
import pytest
from unittest.mock import AsyncMock


def _make_df(closes, highs=None, lows=None):
    n = len(closes)
    highs = highs or [c + 1 for c in closes]
    lows = lows or [c - 1 for c in closes]
    return pd.DataFrame({
        "timestamp": list(range(n)),
        "open": closes, "high": highs, "low": lows,
        "close": closes, "volume": [100.0] * n,
    })


class TestExtraMomentum:
    def test_stoch_rsi_present(self):
        from src.modules.indicators.momentum import compute_momentum
        closes = [100.0 + (i % 10) for i in range(60)]
        result = compute_momentum(_make_df(closes))
        assert result["stoch_rsi"] is not None
        assert 0 <= result["stoch_rsi"]["k"] <= 100

    def test_cci_ranges(self):
        from src.modules.indicators.momentum import compute_momentum
        closes = [100.0 + (i % 7) for i in range(40)]
        result = compute_momentum(_make_df(closes))
        assert result["cci"] is not None
        assert result["cci"]["regime"] in ("OVERBOUGHT", "OVERSOLD", "NEUTRAL")

    def test_williams_r_range(self):
        from src.modules.indicators.momentum import compute_momentum
        closes = [100.0 + i for i in range(30)]
        result = compute_momentum(_make_df(closes))
        assert result["williams_r"] is not None
        # Williams %R her zaman -100..0 aralığında
        assert -100 <= result["williams_r"]["value"] <= 0

    def test_roc_direction(self):
        from src.modules.indicators.momentum import compute_momentum
        closes = [100.0 + i for i in range(30)]  # sürekli artış
        result = compute_momentum(_make_df(closes))
        assert result["roc"]["regime"] == "POSITIVE"

    def test_extra_none_when_insufficient(self):
        from src.modules.indicators.momentum import compute_momentum
        closes = [100.0] * 10
        result = compute_momentum(_make_df(closes))
        assert result["stoch_rsi"] is None
        assert result["cci"] is None


class TestDerivatives:
    @pytest.mark.asyncio
    async def test_funding_status_classification(self):
        """Yüksek pozitif funding OVERHEATED_LONG olarak sınıflanmalı."""
        from src.modules.indicators.derivatives import DerivativesData
        d = DerivativesData()
        mock_ex = AsyncMock()
        mock_ex.fetch_funding_rate.return_value = {"fundingRate": 0.0005}  # > 0.0003
        mock_ex.fetch_open_interest.return_value = {"openInterestAmount": 12345.0}
        d.exchange = mock_ex
        result = await d.get_derivatives("BTC/USDT")
        assert result["available"] is True
        assert result["funding_rate"]["status"] == "OVERHEATED_LONG"
        assert result["open_interest"]["amount"] == 12345.0

    @pytest.mark.asyncio
    async def test_funding_normal(self):
        from src.modules.indicators.derivatives import DerivativesData
        d = DerivativesData()
        mock_ex = AsyncMock()
        mock_ex.fetch_funding_rate.return_value = {"fundingRate": 0.00001}
        mock_ex.fetch_open_interest.return_value = {"openInterestAmount": 100.0}
        d.exchange = mock_ex
        result = await d.get_derivatives("BTC/USDT")
        assert result["funding_rate"]["status"] == "NORMAL"

    def test_swap_symbol_conversion(self):
        from src.modules.indicators.derivatives import _to_swap_symbol
        assert _to_swap_symbol("BTC/USDT") == "BTC/USDT:USDT"
        assert _to_swap_symbol("ETH/USDT:USDT") == "ETH/USDT:USDT"


class TestDerivativesIntegration:
    @pytest.mark.asyncio
    async def test_indicators_include_derivatives_flag(self):
        """include_derivatives=True indikatör çıktısına derivatives eklemeli."""
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        candles = [{"timestamp": i, "open": 100, "high": 101, "low": 99,
                    "close": 100 + (i % 5), "volume": 100, "confirmed": True}
                   for i in range(60)]
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True, data={"candles": candles}, error=None,
            timestamp="2026-01-01T00:00:00Z"))
        m.derivatives.get_derivatives = AsyncMock(return_value={
            "available": True, "funding_rate": {"value": 0.0001, "status": "NORMAL"},
            "open_interest": {"amount": 5000.0}, "error": None})
        result = await m.get_indicators("BTC/USDT", "1h", 300, include_derivatives=True)
        assert result.success is True
        assert "derivatives" in result.data["indicators"]
        assert result.data["indicators"]["derivatives"]["available"] is True

    @pytest.mark.asyncio
    async def test_indicators_exclude_derivatives_by_default(self):
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        candles = [{"timestamp": i, "open": 100, "high": 101, "low": 99,
                    "close": 100 + (i % 5), "volume": 100, "confirmed": True}
                   for i in range(60)]
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True, data={"candles": candles}, error=None,
            timestamp="2026-01-01T00:00:00Z"))
        result = await m.get_indicators("BTC/USDT", "1h", 300)
        assert "derivatives" not in result.data["indicators"]
