"""
Katman 3: Trend Gücü İndikatörleri (Faz 2b)
MODULE_2_SPEC 3.3: ADX 14 (Wilder), Aroon 25, Choppiness Index 14.
"""

import numpy as np
import pandas as pd


def _wilder(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def compute_strength(df: pd.DataFrame) -> dict:
    """
    Trend gücü feature'ları.

    Returns:
        {
          "adx": {"value":.., "regime":.., "plus_di":.., "minus_di":..},
          "aroon": {"up":.., "down":.., "oscillator":..},
          "choppiness": {"value":.., "regime":..}
        }
    """
    result: dict = {"adx": None, "aroon": None, "choppiness": None}
    if len(df) < 28:
        return result

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    # --- ADX / DI (Wilder, period 14) ---
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low, (high - prev_close).abs(), (low - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = _wilder(tr, 14)
    plus_di = 100 * _wilder(plus_dm, 14) / atr.replace(0.0, np.nan)
    minus_di = 100 * _wilder(minus_dm, 14) / atr.replace(0.0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = _wilder(dx, 14)

    adx_val = adx.iloc[-1]
    if pd.notna(adx_val):
        v = float(adx_val)
        if v < 20:
            regime = "NO_TREND"
        elif v <= 25:
            regime = "DEVELOPING"
        elif v < 40:
            regime = "STRONG_TREND"
        else:
            regime = "OVEREXTENDED"
        result["adx"] = {
            "value": round(v, 2),
            "regime": regime,
            "plus_di": round(float(plus_di.iloc[-1]), 2) if pd.notna(plus_di.iloc[-1]) else None,
            "minus_di": round(float(minus_di.iloc[-1]), 2) if pd.notna(minus_di.iloc[-1]) else None,
        }

    # --- Aroon (period 25) ---
    if len(df) >= 26:
        period = 25
        recent_high = high.rolling(period + 1)
        recent_low = low.rolling(period + 1)
        # periyot içindeki en yüksek/düşükten bu yana geçen bar sayısı
        aroon_up = recent_high.apply(lambda x: (period - (len(x) - 1 - int(np.argmax(x)))) / period * 100, raw=True).iloc[-1]
        aroon_down = recent_low.apply(lambda x: (period - (len(x) - 1 - int(np.argmin(x)))) / period * 100, raw=True).iloc[-1]
        if pd.notna(aroon_up) and pd.notna(aroon_down):
            result["aroon"] = {
                "up": round(float(aroon_up), 2),
                "down": round(float(aroon_down), 2),
                "oscillator": round(float(aroon_up - aroon_down), 2),
            }

    # --- Choppiness Index (period 14) ---
    if len(df) >= 15:
        n = 14
        atr_sum = tr.rolling(n).sum()
        max_high = high.rolling(n).max()
        min_low = low.rolling(n).min()
        rng = (max_high - min_low).replace(0.0, np.nan)
        ci = 100 * np.log10(atr_sum / rng) / np.log10(n)
        ci_val = ci.iloc[-1]
        if pd.notna(ci_val):
            v = float(ci_val)
            if v > 61.8:
                regime = "CONSOLIDATION"
            elif v < 38.2:
                regime = "TRENDING"
            else:
                regime = "NEUTRAL"
            result["choppiness"] = {"value": round(v, 2), "regime": regime}

    return result
