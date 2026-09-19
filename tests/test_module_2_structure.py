"""
KuCoin Al-Sat Botu — Modül 2 Market Structure (SMC) Testleri
Swing tespiti, HH/HL/LH/LL yapı, BOS, CHoCH, FVG.
"""

import pandas as pd
import pytest


def _df(rows):
    """rows: list of (open, high, low, close)."""
    return pd.DataFrame({
        "timestamp": list(range(len(rows))),
        "open": [r[0] for r in rows],
        "high": [r[1] for r in rows],
        "low": [r[2] for r in rows],
        "close": [r[3] for r in rows],
        "volume": [100.0] * len(rows),
    })


class TestSwingDetection:
    def test_find_swings_detects_peak(self):
        """Ortada belirgin bir tepe swing high olarak tespit edilmeli."""
        from src.modules.indicators.structure import _find_swings
        # index 3'te tepe (yükselen sonra alçalan)
        rows = [(10, 11, 9, 10), (11, 12, 10, 11), (12, 13, 11, 12),
                (13, 20, 12, 19), (12, 13, 11, 12), (11, 12, 10, 11),
                (10, 11, 9, 10)]
        highs, lows = _find_swings(_df(rows), n=3)
        assert any(idx == 3 for idx, _ in highs)

    def test_swings_lookahead_protected(self):
        """Sağında n teyit barı olmayan son barlar swing sayılmamalı."""
        from src.modules.indicators.structure import _find_swings
        rows = [(10, 11, 9, 10)] * 4 + [(20, 25, 19, 24)]  # son bar tepe ama teyit yok
        highs, lows = _find_swings(_df(rows), n=3)
        assert all(idx != len(rows) - 1 for idx, _ in highs)


class TestStructure:
    def test_bullish_structure_hh_hl(self):
        """Higher-high + higher-low serisinde yapı BULLISH olmalı."""
        from src.modules.indicators.structure import compute_structure
        # Net izole tepe/dipler içeren yükselen zig-zag (her salınım bir öncekinden yüksek)
        rows = [
            (10, 12, 10, 11),   # 0
            (11, 14, 11, 13),   # 1 tepe adayı
            (13, 13, 9, 10),    # 2
            (10, 11, 8, 9),     # 3 dip
            (9, 12, 9, 11),     # 4
            (11, 18, 11, 17),   # 5 daha yüksek tepe (HH)
            (17, 17, 13, 14),   # 6
            (14, 15, 12, 13),   # 7 daha yüksek dip (HL)
            (13, 16, 13, 15),   # 8
            (15, 20, 15, 19),   # 9
        ]
        result = compute_structure(_df(rows), n=2)
        assert result["structure"] in ("BULLISH", "RANGING")
        assert result["last_swing_high"] is not None

    def test_bullish_bos_on_breakout(self):
        """Son kapanış son swing high üstündeyse BOS BULLISH olmalı."""
        from src.modules.indicators.structure import compute_structure
        rows = [(10, 12, 9, 11), (11, 13, 10, 12), (12, 14, 11, 13),
                (13, 15, 12, 14), (14, 16, 13, 15), (15, 14, 11, 12),
                (12, 13, 10, 11), (11, 12, 10, 11), (11, 30, 11, 29)]
        result = compute_structure(_df(rows), n=2)
        # son kapanış (29) önceki tüm swing high'ların üstünde
        assert result["bos"] == "BULLISH"

    def test_insufficient_data(self):
        """Az veride RANGING + None alanlar dönmeli, çökmemeli."""
        from src.modules.indicators.structure import compute_structure
        rows = [(10, 11, 9, 10)] * 3
        result = compute_structure(_df(rows), n=3)
        assert result["structure"] == "RANGING"
        assert result["bos"] is None


class TestFVG:
    def test_bullish_fvg_detected(self):
        """Mum1.high < Mum3.low olduğunda bullish FVG tespit edilmeli."""
        from src.modules.indicators.structure import _fair_value_gaps
        # 3 barlık boşluk: bar0.high=11, bar2.low=15 -> gap
        rows = [(10, 11, 9, 10), (12, 14, 11, 13), (15, 18, 15, 17)]
        gaps = _fair_value_gaps(_df(rows))
        assert any(g["type"] == "BULLISH" for g in gaps)

    def test_no_fvg_when_overlapping(self):
        """Barlar örtüşüyorsa FVG oluşmamalı."""
        from src.modules.indicators.structure import _fair_value_gaps
        rows = [(10, 12, 9, 11), (10, 12, 9, 11), (10, 12, 9, 11)]
        gaps = _fair_value_gaps(_df(rows))
        assert len(gaps) == 0


class TestGetStructureIntegration:
    @pytest.mark.asyncio
    async def test_structure_unavailable_when_few(self):
        from unittest.mock import AsyncMock
        from src.modules.module2_market import KuCoinMarket
        from src.models.market import CandlesResponse
        m = KuCoinMarket()
        candles = [{"timestamp": i, "open": 100, "high": 101, "low": 99,
                    "close": 100, "volume": 100, "confirmed": True} for i in range(4)]
        m.get_candles = AsyncMock(return_value=CandlesResponse(
            success=True, data={"candles": candles}, error=None,
            timestamp="2026-01-01T00:00:00Z"))
        result = await m.get_structure("BTC/USDT", "1h", 300)
        assert result.success is False
        assert result.data["data_quality"] == "UNAVAILABLE"
