"""
Katman 5: Volatilite İndikatörleri (Faz 2a çekirdek)
MODULE_2_SPEC 3.5: ATR 14 (Wilder), Normalized ATR %.
"""

import pandas as pd


def compute_volatility(df: pd.DataFrame) -> dict:
    """
    Volatilite katmanı feature'ları: ATR ve normalize ATR yüzdesi.

    Returns:
        {
          "atr": <ATR 14>,
          "atr_percent": <ATR / Close * 100>,
          "stop_loss_1_5x": <1.5 * ATR>,
          "stop_loss_2x": <2.0 * ATR>
        }
    """
    if len(df) < 15:
        return {"atr": None, "atr_percent": None,
                "stop_loss_1_5x": None, "stop_loss_2x": None}

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)

    # True Range = max(H-L, |H-Cprev|, |L-Cprev|)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Wilder smoothing (alpha = 1/period)
    atr_series = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    atr = atr_series.iloc[-1]
    if pd.isna(atr):
        return {"atr": None, "atr_percent": None,
                "stop_loss_1_5x": None, "stop_loss_2x": None}

    atr = float(atr)
    last_close = float(close.iloc[-1])
    atr_percent = round(atr / last_close * 100, 4) if last_close > 0 else None

    return {
        "atr": round(atr, 8),
        "atr_percent": atr_percent,
        "stop_loss_1_5x": round(1.5 * atr, 8),
        "stop_loss_2x": round(2.0 * atr, 8),
    }
