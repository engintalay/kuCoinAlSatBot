"""
Katman 2: Momentum İndikatörleri
MODULE_2_SPEC 3.2:
- Faz 2a: RSI 14 (Wilder), MACD (12, 26, 9)
- Faz 2c: StochRSI (14, K/D), CCI (20), Williams %R (14), ROC (9)
"""

import pandas as pd


def _rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder smoothing ile RSI serisi."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Wilder smoothing: alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    # avg_loss == 0 durumunda RSI = 100
    rsi = rsi.fillna(100.0)
    return rsi


def _stoch_rsi(close: pd.Series, period: int = 14, k: int = 3, d: int = 3) -> dict | None:
    """Stochastic RSI: RSI'nin kendi min-max aralığına göre stokastiği."""
    if len(close) < period * 2:
        return None
    rsi = _rsi_wilder(close, period)
    rsi_min = rsi.rolling(period).min()
    rsi_max = rsi.rolling(period).max()
    rng = (rsi_max - rsi_min).replace(0.0, pd.NA)
    stoch = ((rsi - rsi_min) / rng * 100).fillna(0.0)
    k_line = stoch.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    kv, dv = k_line.iloc[-1], d_line.iloc[-1]
    if pd.isna(kv) or pd.isna(dv):
        return None
    cross = None
    if len(k_line) >= 2 and pd.notna(k_line.iloc[-2]) and pd.notna(d_line.iloc[-2]):
        if k_line.iloc[-2] <= d_line.iloc[-2] and kv > dv:
            cross = "BULLISH"
        elif k_line.iloc[-2] >= d_line.iloc[-2] and kv < dv:
            cross = "BEARISH"
    regime = "OVERBOUGHT" if kv > 80 else "OVERSOLD" if kv < 20 else "NEUTRAL"
    return {"k": round(float(kv), 2), "d": round(float(dv), 2),
            "regime": regime, "cross": cross}


def _cci(df: pd.DataFrame, period: int = 20) -> dict | None:
    """Commodity Channel Index (20). Eşikler ±100."""
    if len(df) < period:
        return None
    tp = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: (x - x.mean()).abs().mean(), raw=False)
    cci = (tp - sma) / (0.015 * mad.replace(0.0, pd.NA))
    val = cci.iloc[-1]
    if pd.isna(val):
        return None
    v = float(val)
    regime = "OVERBOUGHT" if v > 100 else "OVERSOLD" if v < -100 else "NEUTRAL"
    return {"value": round(v, 2), "regime": regime}


def _williams_r(df: pd.DataFrame, period: int = 14) -> dict | None:
    """Williams %R (14). Eşikler -20 / -80."""
    if len(df) < period:
        return None
    high = df["high"].astype(float).rolling(period).max()
    low = df["low"].astype(float).rolling(period).min()
    close = df["close"].astype(float)
    rng = (high - low).replace(0.0, pd.NA)
    wr = (high - close) / rng * -100
    val = wr.iloc[-1]
    if pd.isna(val):
        return None
    v = float(val)
    regime = "OVERBOUGHT" if v > -20 else "OVERSOLD" if v < -80 else "NEUTRAL"
    return {"value": round(v, 2), "regime": regime}


def _roc(close: pd.Series, period: int = 9) -> dict | None:
    """Rate of Change (9) yüzdesi."""
    if len(close) < period + 1:
        return None
    prev = close.iloc[-1 - period]
    if prev == 0:
        return None
    roc = (close.iloc[-1] - prev) / prev * 100
    return {"value": round(float(roc), 4),
            "regime": "POSITIVE" if roc > 0 else "NEGATIVE" if roc < 0 else "FLAT"}


def compute_momentum(df: pd.DataFrame) -> dict:
    """
    Momentum katmanı feature'ları: RSI, MACD, StochRSI, CCI, Williams %R, ROC.
    """
    close = df["close"].astype(float)
    result: dict = {"rsi": None, "macd": None, "stoch_rsi": None,
                    "cci": None, "williams_r": None, "roc": None}

    # --- RSI 14 ---
    if len(close) >= 15:
        rsi_series = _rsi_wilder(close, 14)
        rsi_val = rsi_series.iloc[-1]
        if pd.notna(rsi_val):
            slope = None
            if len(rsi_series.dropna()) >= 4:
                slope = round(float(rsi_series.iloc[-1] - rsi_series.iloc[-4]), 4)
            regime = "NEUTRAL"
            if rsi_val >= 70:
                regime = "OVERBOUGHT"
            elif rsi_val <= 30:
                regime = "OVERSOLD"
            elif rsi_val > 50:
                regime = "BULLISH_ABOVE_50"
            elif rsi_val < 50:
                regime = "BEARISH_BELOW_50"
            result["rsi"] = {
                "value": round(float(rsi_val), 2),
                "regime": regime,
                "slope_3_bars": slope,
            }

    # --- MACD (12, 26, 9) ---
    if len(close) >= 26:
        ema_fast = close.ewm(span=12, adjust=False).mean()
        ema_slow = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        # Sıfır çizgisi geçişi (son iki bar)
        zero_cross = None
        if len(macd_line) >= 2:
            prev, curr = macd_line.iloc[-2], macd_line.iloc[-1]
            if prev <= 0 < curr:
                zero_cross = "BULLISH"
            elif prev >= 0 > curr:
                zero_cross = "BEARISH"

        result["macd"] = {
            "line": round(float(macd_line.iloc[-1]), 8),
            "signal": round(float(signal_line.iloc[-1]), 8),
            "histogram": round(float(histogram.iloc[-1]), 8),
            "zero_cross": zero_cross,
        }

    # --- Faz 2c: ek osilatörler ---
    result["stoch_rsi"] = _stoch_rsi(close)
    result["cci"] = _cci(df)
    result["williams_r"] = _williams_r(df)
    result["roc"] = _roc(close)

    return result
