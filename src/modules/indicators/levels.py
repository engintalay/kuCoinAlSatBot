"""
Katman 6: Destek ve Direnç Seviyeleri (Faz 2b / Adım 3 tamamlama)
MODULE_2_SPEC 3.6: Klasik Pivot Points, Önceki Periyot High/Low, Fibonacci
Retracement, Donchian Channels.
"""

import pandas as pd


def compute_levels(df: pd.DataFrame, donchian_period: int = 20) -> dict:
    """
    Seviye feature'ları.

    Returns:
        {
          "pivots": {"pivot":.., "r1":.., "r2":.., "r3":.., "s1":.., "s2":.., "s3":..},
          "previous": {"high":.., "low":..},
          "fibonacci": {"0.236":.., "0.382":.., "0.5":.., "0.618":.., "0.786":..},
          "donchian": {"upper":.., "lower":.., "middle":..}
        }
    """
    result = {"pivots": None, "previous": None, "fibonacci": None, "donchian": None}
    if len(df) < 2:
        return result

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    # --- Klasik Pivot Points (önceki tam periyodun H/L/C'si üzerinden) ---
    ph, pl, pc = float(high.iloc[-2]), float(low.iloc[-2]), float(close.iloc[-2])
    pivot = (ph + pl + pc) / 3
    r1 = 2 * pivot - pl
    s1 = 2 * pivot - ph
    r2 = pivot + (ph - pl)
    s2 = pivot - (ph - pl)
    r3 = ph + 2 * (pivot - pl)
    s3 = pl - 2 * (ph - pivot)
    result["pivots"] = {
        "pivot": round(pivot, 8),
        "r1": round(r1, 8), "r2": round(r2, 8), "r3": round(r3, 8),
        "s1": round(s1, 8), "s2": round(s2, 8), "s3": round(s3, 8),
    }

    # --- Önceki periyot High/Low ---
    result["previous"] = {"high": round(ph, 8), "low": round(pl, 8)}

    # --- Fibonacci Retracement (son N mumun swing aralığı) ---
    lookback = min(len(df), 100)
    window_high = float(high.iloc[-lookback:].max())
    window_low = float(low.iloc[-lookback:].min())
    diff = window_high - window_low
    if diff > 0:
        result["fibonacci"] = {
            "swing_high": round(window_high, 8),
            "swing_low": round(window_low, 8),
            "0.236": round(window_high - 0.236 * diff, 8),
            "0.382": round(window_high - 0.382 * diff, 8),
            "0.5": round(window_high - 0.5 * diff, 8),
            "0.618": round(window_high - 0.618 * diff, 8),  # Golden Pocket
            "0.786": round(window_high - 0.786 * diff, 8),
        }

    # --- Donchian Channels (period 20) ---
    if len(df) >= donchian_period:
        dc_upper = float(high.iloc[-donchian_period:].max())
        dc_lower = float(low.iloc[-donchian_period:].min())
        result["donchian"] = {
            "upper": round(dc_upper, 8),
            "lower": round(dc_lower, 8),
            "middle": round((dc_upper + dc_lower) / 2, 8),
        }

    return result
