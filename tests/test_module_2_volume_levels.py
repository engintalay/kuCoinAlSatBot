"""
KuCoin Al-Sat Botu — Modül 2 Hacim & Seviye Katmanı Testleri
Volume (RVOL, OBV, VWAP, MFI, CMF, Volume Profile) ve Levels (Pivot, Fib, Donchian).
"""

import pandas as pd


def _make_df(closes, highs=None, lows=None, volumes=None):
    n = len(closes)
    highs = highs or [c + 1 for c in closes]
    lows = lows or [c - 1 for c in closes]
    volumes = volumes or [100.0] * n
    return pd.DataFrame({
        "timestamp": list(range(n)),
        "open": closes,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })


class TestVolume:
    def test_rvol_high_on_volume_spike(self):
        """Son mumda hacim patlaması RVOL HIGH vermeli."""
        from src.modules.indicators.volume import compute_volume
        closes = [100.0 + i * 0.1 for i in range(30)]
        vols = [100.0] * 29 + [500.0]  # son barda spike
        result = compute_volume(_make_df(closes, volumes=vols))
        assert result["rvol"] is not None
        assert result["rvol"]["regime"] == "HIGH"

    def test_obv_rises_in_uptrend(self):
        """Yükselen fiyatta OBV EMA20 üzerinde olmalı."""
        from src.modules.indicators.volume import compute_volume
        closes = [100.0 + i for i in range(30)]
        result = compute_volume(_make_df(closes))
        assert result["obv"] is not None
        assert result["obv"]["above_ema20"] is True

    def test_vwap_and_profile_present(self):
        """VWAP ve Volume Profile hesaplanmalı."""
        from src.modules.indicators.volume import compute_volume
        closes = [100.0 + (i % 5) for i in range(40)]
        result = compute_volume(_make_df(closes))
        assert result["vwap"] is not None
        assert result["vwap"]["value"] > 0
        vp = result["volume_profile"]
        assert vp is not None
        assert vp["val"] <= vp["poc"] <= vp["vah"]

    def test_mfi_cmf_ranges(self):
        """MFI 0-100, CMF -1..1 aralığında olmalı."""
        from src.modules.indicators.volume import compute_volume
        closes = [100.0 + (i % 7) - 3 for i in range(40)]
        result = compute_volume(_make_df(closes))
        assert 0 <= result["mfi"]["value"] <= 100
        assert -1 <= result["cmf"]["value"] <= 1

    def test_insufficient_data(self):
        """20'den az mumda tüm alanlar None dönmeli."""
        from src.modules.indicators.volume import compute_volume
        closes = [100.0] * 10
        result = compute_volume(_make_df(closes))
        assert result["rvol"] is None
        assert result["vwap"] is None


class TestLevels:
    def test_pivots_computed(self):
        """Pivot noktaları hesaplanmalı ve S1<Pivot<R1 olmalı."""
        from src.modules.indicators.levels import compute_levels
        closes = [100.0 + i for i in range(30)]
        result = compute_levels(_make_df(closes))
        p = result["pivots"]
        assert p is not None
        assert p["s1"] < p["pivot"] < p["r1"]

    def test_fibonacci_levels_ordered(self):
        """Fibonacci seviyeleri swing_low..swing_high arasında sıralı olmalı."""
        from src.modules.indicators.levels import compute_levels
        closes = [100.0 + i for i in range(50)]
        result = compute_levels(_make_df(closes))
        fib = result["fibonacci"]
        assert fib is not None
        assert fib["swing_low"] <= fib["0.618"] <= fib["swing_high"]
        # 0.236 seviyesi 0.786'dan daha yüksek fiyatta (high'a daha yakın)
        assert fib["0.236"] > fib["0.786"]

    def test_donchian_channel(self):
        """Donchian upper >= lower ve middle ortada olmalı."""
        from src.modules.indicators.levels import compute_levels
        closes = [100.0 + (i % 10) for i in range(30)]
        result = compute_levels(_make_df(closes))
        dc = result["donchian"]
        assert dc is not None
        assert dc["lower"] <= dc["middle"] <= dc["upper"]

    def test_insufficient_data(self):
        """Tek mumda seviyeler None dönmeli, çökmemeli."""
        from src.modules.indicators.levels import compute_levels
        result = compute_levels(_make_df([100.0]))
        assert result["pivots"] is None


class TestVolumeScoring:
    def test_volume_bullish_contributes(self):
        """Yüksek RVOL + VWAP üstü + CMF inflow + OBV üstü boğa puanı eklemeli."""
        from src.modules.analysis.scoring_engine import _score_volume
        vol = {
            "rvol": {"regime": "HIGH"},
            "vwap": {"price_above_vwap": True},
            "cmf": {"regime": "INFLOW"},
            "obv": {"above_ema20": True},
        }
        bull, bear, reasons = _score_volume(vol)
        assert bull == 20.0
        assert bear == 0.0
        assert len(reasons) == 3
