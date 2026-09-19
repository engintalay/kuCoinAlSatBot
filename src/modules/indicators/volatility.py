"""
Katman 5: Volatilite İndikatörleri
MODULE_2_SPEC 3.5:
- Faz 2a: ATR 14 (Wilder), Normalized ATR %
- Faz 2b: Bollinger Bands (20, 2.0), Keltner Channels (EMA20, 1.5*ATR), Squeeze
"""

import pandas as pd


def _atr_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low, (high - prev_close).abs(), (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _bollinger_keltner(df: pd.DataFrame) -> dict | None:
    """Bollinger Bands (20, 2.0), Keltner (EMA20, 1.5*ATR) ve Squeeze durumu."""
    if len(df) < 20:
        return None
    close = df["close"].astype(float)
    price = float(close.iloc[-1])

    # Bollinger
    mid = close.rolling(20).mean()
    std = close.rolling(20).std(ddof=0)
    bb_upper = mid + 2.0 * std
    bb_lower = mid - 2.0 * std
    bb_u, bb_l, bb_m = float(bb_upper.iloc[-1]), float(bb_lower.iloc[-1]), float(mid.iloc[-1])
    bandwidth = round((bb_u - bb_l) / bb_m, 6) if bb_m != 0 else None
    percent_b = round((price - bb_l) / (bb_u - bb_l), 4) if (bb_u - bb_l) != 0 else None

    # Keltner (EMA20 merkez, 1.5 * ATR14)
    ema20 = close.ewm(span=20, adjust=False).mean()
    atr = _atr_series(df, 14)
    kc_upper = ema20 + 1.5 * atr
    kc_lower = ema20 - 1.5 * atr
    kc_u, kc_l = float(kc_upper.iloc[-1]), float(kc_lower.iloc[-1])

    # Squeeze: BB, KC içine girdiğinde ON
    squeeze = "SQUEEZE_ON" if (bb_u < kc_u and bb_l > kc_l) else "SQUEEZE_OFF"

    return {
        "bollinger": {
            "upper": round(bb_u, 8),
            "middle": round(bb_m, 8),
            "lower": round(bb_l, 8),
            "bandwidth": bandwidth,
            "percent_b": percent_b,
        },
        "keltner": {"upper": round(kc_u, 8), "lower": round(kc_l, 8)},
        "squeeze": squeeze,
    }


def compute_volatility(df: pd.DataFrame) -> dict:
    """
    Volatilite katmanı feature'ları: ATR, normalize ATR %, Bollinger/Keltner/Squeeze.
    """
    if len(df) < 15:
        return {"atr": None, "atr_percent": None,
                "stop_loss_1_5x": None, "stop_loss_2x": None,
                "bollinger_keltner": None}

    close = df["close"].astype(float)
    atr_series = _atr_series(df, 14)
    atr = atr_series.iloc[-1]
    if pd.isna(atr):
        return {"atr": None, "atr_percent": None,
                "stop_loss_1_5x": None, "stop_loss_2x": None,
                "bollinger_keltner": None}

    atr = float(atr)
    last_close = float(close.iloc[-1])
    atr_percent = round(atr / last_close * 100, 4) if last_close > 0 else None

    return {
        "atr": round(atr, 8),
        "atr_percent": atr_percent,
        "stop_loss_1_5x": round(1.5 * atr, 8),
        "stop_loss_2x": round(2.0 * atr, 8),
        "bollinger_keltner": _bollinger_keltner(df),
    }
