"""
Katman 1: Trend İndikatörleri
MODULE_2_SPEC 3.1:
- Faz 2a: EMA (20/50/100/200), SMA (50/200)
- Faz 2b: Supertrend (10, 3.0), Ichimoku (9/26/52), Parabolic SAR (0.02/0.20)
"""

import numpy as np
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


def _supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> dict | None:
    """Supertrend (ATR bazlı). Çıktı: direction (1/-1), trend_price."""
    if len(df) < period + 1:
        return None
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    final_upper = upper.copy()
    final_lower = lower.copy()
    direction = pd.Series(1, index=df.index)

    # ATR'nin geçerli (non-NaN) olduğu ilk index'ten itibaren hesapla.
    valid_idx = atr.first_valid_index()
    if valid_idx is None:
        return None
    start = df.index.get_loc(valid_idx)

    for i in range(start + 1, len(df)):
        pu = final_upper.iloc[i - 1]
        pl = final_lower.iloc[i - 1]
        # Önceki değer NaN ise mevcut bant değerini taban al
        if pd.isna(pu):
            pu = upper.iloc[i]
        if pd.isna(pl):
            pl = lower.iloc[i]
        final_upper.iloc[i] = (upper.iloc[i]
                               if (upper.iloc[i] < pu or close.iloc[i - 1] > pu)
                               else pu)
        final_lower.iloc[i] = (lower.iloc[i]
                               if (lower.iloc[i] > pl or close.iloc[i - 1] < pl)
                               else pl)
        if close.iloc[i] > pu:
            direction.iloc[i] = 1
        elif close.iloc[i] < pl:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

    d = int(direction.iloc[-1])
    trend_price = float(final_lower.iloc[-1]) if d == 1 else float(final_upper.iloc[-1])
    if pd.isna(trend_price):
        return {"direction": d, "trend_price": None}
    return {"direction": d, "trend_price": round(trend_price, 8)}


def _ichimoku(df: pd.DataFrame) -> dict | None:
    """Ichimoku Kinko Hyo (9/26/52). Fiyatın Kumo'ya göre konumu."""
    if len(df) < 52:
        return None
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2)
    span_b = (high.rolling(52).max() + low.rolling(52).min()) / 2

    price = float(close.iloc[-1])
    a = float(span_a.iloc[-1])
    b = float(span_b.iloc[-1])
    cloud_top, cloud_bottom = max(a, b), min(a, b)
    if price > cloud_top:
        position = "ABOVE_CLOUD"   # bullish
    elif price < cloud_bottom:
        position = "BELOW_CLOUD"   # bearish
    else:
        position = "IN_CLOUD"      # konsolidasyon
    return {
        "tenkan": round(float(tenkan.iloc[-1]), 8),
        "kijun": round(float(kijun.iloc[-1]), 8),
        "span_a": round(a, 8),
        "span_b": round(b, 8),
        "position": position,
    }


def _parabolic_sar(df: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.20) -> dict | None:
    """Parabolic SAR. Çıktı: sar değeri ve fiyata göre konum (bullish/bearish)."""
    if len(df) < 5:
        return None
    high = df["high"].astype(float).values
    low = df["low"].astype(float).values

    sar = low[0]
    ep = high[0]
    af = af_step
    trend_up = True
    for i in range(1, len(df)):
        prev_sar = sar
        sar = prev_sar + af * (ep - prev_sar)
        if trend_up:
            sar = min(sar, low[i - 1], low[max(i - 2, 0)])
            if high[i] > ep:
                ep = high[i]
                af = min(af + af_step, af_max)
            if low[i] < sar:
                trend_up = False
                sar = ep
                ep = low[i]
                af = af_step
        else:
            sar = max(sar, high[i - 1], high[max(i - 2, 0)])
            if low[i] < ep:
                ep = low[i]
                af = min(af + af_step, af_max)
            if high[i] > sar:
                trend_up = True
                sar = ep
                ep = high[i]
                af = af_step

    return {
        "sar": round(float(sar), 8),
        "position": "BULLISH" if trend_up else "BEARISH",
    }


def compute_trend(df: pd.DataFrame) -> dict:
    """
    Trend katmanı feature'ları (Faz 2a EMA/SMA + Faz 2b Supertrend/Ichimoku/SAR).
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
        "supertrend": _supertrend(df),
        "ichimoku": _ichimoku(df),
        "parabolic_sar": _parabolic_sar(df),
    }
