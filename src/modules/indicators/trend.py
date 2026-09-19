"""
Katman 1: Trend İndikatörleri (Faz 2a çekirdek)
MODULE_2_SPEC 3.1: EMA (20/50/100/200), SMA (50/200).
"""

import pandas as pd


def _ema(series: pd.Series, period: int) -> float | None:
    """Son EMA değerini döndürür (yetersiz veri varsa None)."""
    if len(series) < period:
        return None
    ema = series.ewm(span=period, adjust=False).mean()
    val = ema.iloc[-1]
    return round(float(val), 8) if pd.notna(val) else None


def _sma(series: pd.Series, period: int) -> float | None:
    """Son SMA değerini döndürür (yetersiz veri varsa None)."""
    if len(series) < period:
        return None
    val = series.rolling(window=period).mean().iloc[-1]
    return round(float(val), 8) if pd.notna(val) else None


def compute_trend(df: pd.DataFrame) -> dict:
    """
    Trend katmanı feature'ları.

    Returns:
        {
          "ema": {"20":.., "50":.., "100":.., "200":..},
          "sma": {"50":.., "200":..},
          "price": <son kapanış>,
          "regime": "BULLISH" | "BEARISH" | "NEUTRAL",
          "cross": "GOLDEN_CROSS" | "DEATH_CROSS" | None
        }
    """
    close = df["close"].astype(float)
    price = round(float(close.iloc[-1]), 8) if len(close) else None

    ema = {p: _ema(close, p) for p in (20, 50, 100, 200)}
    sma = {p: _sma(close, p) for p in (50, 200)}

    regime = "NEUTRAL"
    cross = None
    ema50, ema200 = ema[50], ema[200]
    if price is not None and ema50 is not None and ema200 is not None:
        # Golden Cross: fiyat EMA200 üstünde ve EMA50 > EMA200
        if price > ema200 and ema50 > ema200:
            regime = "BULLISH"
            cross = "GOLDEN_CROSS"
        elif price < ema200 and ema50 < ema200:
            regime = "BEARISH"
            cross = "DEATH_CROSS"

    return {
        "ema": {str(k): v for k, v in ema.items()},
        "sma": {str(k): v for k, v in sma.items()},
        "price": price,
        "regime": regime,
        "cross": cross,
    }
