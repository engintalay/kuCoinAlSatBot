"""
Katman 2: Momentum İndikatörleri (Faz 2a çekirdek)
MODULE_2_SPEC 3.2: RSI 14 (Wilder), MACD (12, 26, 9).
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


def compute_momentum(df: pd.DataFrame) -> dict:
    """
    Momentum katmanı feature'ları: RSI ve MACD.

    Returns:
        {
          "rsi": {"value":.., "regime":.., "slope_3_bars":..},
          "macd": {"line":.., "signal":.., "histogram":.., "zero_cross":..}
        }
    """
    close = df["close"].astype(float)
    result: dict = {"rsi": None, "macd": None}

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

    return result
