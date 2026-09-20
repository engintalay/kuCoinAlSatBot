"""
KuCoin Al-Sat Botu — Modül 2 Analiz Motoru Testleri
Composite Scoring Engine ve MTF hiyerarşisi.
"""

import pytest


def _bullish_indicators():
    return {
        "trend": {"regime": "BULLISH", "cross": "GOLDEN_CROSS",
                  "supertrend": {"direction": 1}, "ichimoku": {"position": "ABOVE_CLOUD"}},
        "momentum": {"rsi": {"value": 62.0, "slope_3_bars": 2.0},
                     "macd": {"histogram": 50.0}},
        "strength": {"adx": {"value": 30.0, "regime": "STRONG_TREND",
                             "plus_di": 30.0, "minus_di": 12.0},
                     "choppiness": {"regime": "TRENDING"}},
        "volatility": {"bollinger_keltner": {"squeeze": "SQUEEZE_OFF"}},
        "structure": {"bos": "BULLISH", "fvg": [{"type": "BULLISH"}]},
    }


def _bearish_indicators():
    return {
        "trend": {"regime": "BEARISH", "cross": "DEATH_CROSS",
                  "supertrend": {"direction": -1}, "ichimoku": {"position": "BELOW_CLOUD"}},
        "momentum": {"rsi": {"value": 38.0, "slope_3_bars": -2.0},
                     "macd": {"histogram": -50.0}},
        "strength": {"adx": {"value": 30.0, "regime": "STRONG_TREND",
                             "plus_di": 12.0, "minus_di": 30.0},
                     "choppiness": {"regime": "TRENDING"}},
        "volatility": {"bollinger_keltner": {"squeeze": "SQUEEZE_OFF"}},
        "structure": {"bos": "BEARISH", "fvg": [{"type": "BEARISH"}]},
    }


class TestScoringEngine:
    def test_strong_bullish(self):
        from src.modules.analysis.scoring_engine import compute_score
        result = compute_score(_bullish_indicators())
        assert result["bull_score"] > result["bear_score"]
        assert result["signal"] in ("STRONG_BULLISH", "BULLISH")
        assert len(result["reasons"]) > 0

    def test_strong_bearish(self):
        from src.modules.analysis.scoring_engine import compute_score
        result = compute_score(_bearish_indicators())
        assert result["bear_score"] > result["bull_score"]
        assert result["signal"] in ("STRONG_BEARISH", "BEARISH")

    def test_choppiness_forces_neutral(self):
        from src.modules.analysis.scoring_engine import compute_score
        ind = _bullish_indicators()
        ind["strength"]["choppiness"] = {"regime": "CONSOLIDATION"}
        result = compute_score(ind)
        assert result["signal"] == "NEUTRAL"
        assert any("Konsolidasyon" in w or "Choppiness" in w for w in result["warnings"])

    def test_empty_indicators_neutral(self):
        from src.modules.analysis.scoring_engine import compute_score
        result = compute_score({})
        assert result["signal"] == "NEUTRAL"
        assert result["bull_score"] == 0.0
        assert result["bear_score"] == 0.0

    def test_scores_capped_at_100(self):
        from src.modules.analysis.scoring_engine import compute_score
        result = compute_score(_bullish_indicators())
        assert 0 <= result["bull_score"] <= 100
        assert 0 <= result["bear_score"] <= 100

    def test_simple_summary_and_educational_reasons(self):
        from src.modules.analysis.scoring_engine import compute_score
        ind = _bullish_indicators()
        result = compute_score(ind, market_type="spot")

        # Basit Özet Kontrolleri
        assert "simple_summary" in result
        sm = result["simple_summary"]
        assert "status" in sm and ("Yükseliş" in sm["status"] or "🟢" in sm["status"])
        assert "advice" in sm and len(sm["advice"]) > 10
        assert "risk_level" in sm and sm["risk_level"] in ("Düşük", "Orta", "Yüksek")
        assert "risk_text" in sm
        assert sm["market_label"] == "KuCoin Spot"

        # Detaylı Gerekçeler (4 Alan: indicator, condition, meaning, impact)
        assert "reasons_detail" in result
        assert len(result["reasons_detail"]) > 0
        for rd in result["reasons_detail"]:
            assert "indicator" in rd and len(rd["indicator"]) > 0
            assert "condition" in rd and len(rd["condition"]) > 0
            assert "meaning" in rd and len(rd["meaning"]) > 0
            assert "impact" in rd and len(rd["impact"]) > 0
            assert rd["type"] in ("bullish", "bearish")
            assert "summary" in rd

    def test_educational_warnings_and_market_types(self):
        from src.modules.analysis.scoring_engine import compute_score
        ind = _bullish_indicators()
        # ADX < 20 ve Choppiness ekle
        ind["strength"]["adx"] = {"value": 15, "regime": "WEAK"}
        ind["strength"]["choppiness"] = {"regime": "CONSOLIDATION"}

        res_futures = compute_score(ind, market_type="futures")
        assert "warnings_detail" in res_futures
        assert len(res_futures["warnings_detail"]) >= 2
        for wd in res_futures["warnings_detail"]:
            assert "warning" in wd
            assert "why" in wd
            assert "meaning" in wd
            assert "impact" in wd
            assert "advice" in wd
            assert "summary" in wd

        # Marjin riski kontrolü
        res_margin = compute_score(ind, market_type="margin")
        assert any("Marjin" in w for w in res_margin["warnings"])
        margin_wd = next((w for w in res_margin["warnings_detail"] if "Marjin" in w["warning"]), None)
        assert margin_wd is not None
        assert "Kaldıraç" in margin_wd["meaning"] or "teminat" in margin_wd["advice"].lower()


class TestMTFEngine:
    def test_aligned_bullish_long_setup(self):
        from src.modules.analysis.mtf_engine import evaluate_mtf
        bull = {"signal": "BULLISH"}
        result = evaluate_mtf(bull, bull, bull)
        assert result["final_signal"] == "LONG_SETUP"
        assert result["aligned"] is True

    def test_aligned_bearish_short_setup(self):
        from src.modules.analysis.mtf_engine import evaluate_mtf
        bear = {"signal": "BEARISH"}
        result = evaluate_mtf(bear, bear, bear)
        assert result["final_signal"] == "SHORT_SETUP"

    def test_misaligned_no_trade(self):
        from src.modules.analysis.mtf_engine import evaluate_mtf
        result = evaluate_mtf({"signal": "BULLISH"}, {"signal": "NEUTRAL"}, {"signal": "BULLISH"})
        assert result["final_signal"] == "NO_TRADE"
        assert result["aligned"] is False

    def test_neutral_4h_no_trade(self):
        from src.modules.analysis.mtf_engine import evaluate_mtf
        result = evaluate_mtf({"signal": "NEUTRAL"}, {"signal": "BULLISH"}, {"signal": "BULLISH"})
        assert result["final_signal"] == "NO_TRADE"
        assert result["regime"] == "NEUTRAL"


class TestScoreIntegration:
    @pytest.mark.asyncio
    async def test_get_score_unavailable_when_few(self):
        from unittest.mock import AsyncMock
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        candles = [{"timestamp": i, "open": 100, "high": 101, "low": 99,
                    "close": 100, "volume": 100, "confirmed": True} for i in range(10)]
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True, data={"candles": candles}, error=None,
            timestamp="2026-01-01T00:00:00Z"))
        result = await m.get_score("BTC/USDT", "1h", 300)
        assert result.success is False
        assert result.data["data_quality"] == "UNAVAILABLE"
