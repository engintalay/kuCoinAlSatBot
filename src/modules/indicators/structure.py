"""
Katman 7: Market Structure & Smart Money Concepts (SMC) — Faz 2b
MODULE_2_SPEC 3.7: Swing tespiti (lookahead-korumalı), HH/HL/LH/LL trend yapısı,
BOS (Break of Structure), CHoCH (Change of Character), FVG, Order Block.
"""

import pandas as pd


def _find_swings(df: pd.DataFrame, n: int = 3) -> tuple[list, list]:
    """
    Lookahead-korumalı swing tespiti.
    Bir bar swing high sayılır: solunda ve sağında n bar daha düşük tepe.
    Sağdaki n teyit barı kapanmadan swing teyit edilmez.

    Returns: (swing_highs, swing_lows) — her biri [(index, price), ...]
    """
    highs = df["high"].astype(float).values
    lows = df["low"].astype(float).values
    swing_highs, swing_lows = [], []
    length = len(df)

    # i, sağında n teyit barı olacak şekilde en fazla length-n-1'e kadar
    for i in range(n, length - n):
        window_h = highs[i - n:i + n + 1]
        window_l = lows[i - n:i + n + 1]
        if highs[i] == window_h.max() and (window_h == highs[i]).sum() == 1:
            swing_highs.append((i, float(highs[i])))
        if lows[i] == window_l.min() and (window_l == lows[i]).sum() == 1:
            swing_lows.append((i, float(lows[i])))

    return swing_highs, swing_lows


def _fair_value_gaps(df: pd.DataFrame, lookback: int = 30) -> list:
    """
    FVG (Fair Value Gap): 3 barlık seride Mum1.high < Mum3.low (bullish gap)
    veya Mum1.low > Mum3.high (bearish gap).
    """
    high = df["high"].astype(float).values
    low = df["low"].astype(float).values
    gaps = []
    start = max(2, len(df) - lookback)
    for i in range(start, len(df)):
        h1, l1 = high[i - 2], low[i - 2]
        h3, l3 = high[i], low[i]
        if h1 < l3:
            gaps.append({"type": "BULLISH", "index": i, "bottom": round(h1, 8), "top": round(l3, 8)})
        elif l1 > h3:
            gaps.append({"type": "BEARISH", "index": i, "bottom": round(h3, 8), "top": round(l1, 8)})
    return gaps


def compute_structure(df: pd.DataFrame, n: int = 3) -> dict:
    """
    Market structure feature'ları.

    Returns:
        {
          "structure": "BULLISH"|"BEARISH"|"RANGING",
          "bos": "BULLISH"|"BEARISH"|None,
          "choch": "BULLISH"|"BEARISH"|None,
          "last_swing_high": .., "last_swing_low": ..,
          "fvg": [...], "order_block": {...}|None
        }
    """
    result = {
        "structure": "RANGING", "bos": None, "choch": None,
        "last_swing_high": None, "last_swing_low": None,
        "fvg": [], "order_block": None,
    }
    if len(df) < 2 * n + 3:
        return result

    swing_highs, swing_lows = _find_swings(df, n)
    close = df["close"].astype(float)
    last_close = float(close.iloc[-1])

    # Son swing seviyeleri (varsa) — BOS/CHoCH için tek swing yeterli.
    last_sh = swing_highs[-1][1] if swing_highs else None
    last_sl = swing_lows[-1][1] if swing_lows else None
    if last_sh is not None:
        result["last_swing_high"] = round(last_sh, 8)
    if last_sl is not None:
        result["last_swing_low"] = round(last_sl, 8)

    # Trend yapısı: en az 2 swing high VE 2 swing low gerekir (HH/HL vs LH/LL).
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        h_prev, h_last = swing_highs[-2][1], swing_highs[-1][1]
        l_prev, l_last = swing_lows[-2][1], swing_lows[-1][1]
        if h_last > h_prev and l_last > l_prev:
            result["structure"] = "BULLISH"
        elif h_last < h_prev and l_last < l_prev:
            result["structure"] = "BEARISH"

    # BOS: gövde kapanışı son swing high üstünde (bullish) / son swing low altında (bearish).
    if last_sh is not None and last_close > last_sh:
        result["bos"] = "BULLISH"
    elif last_sl is not None and last_close < last_sl:
        result["bos"] = "BEARISH"

    # CHoCH: yükselen yapıda son swing low kırılırsa bearish; düşen yapıda son swing high kırılırsa bullish.
    if result["structure"] == "BULLISH" and last_sl is not None and last_close < last_sl:
        result["choch"] = "BEARISH"
    elif result["structure"] == "BEARISH" and last_sh is not None and last_close > last_sh:
        result["choch"] = "BULLISH"

    # Order Block: bullish BOS öncesi son düşüş mumu (basitleştirilmiş).
    if result["bos"] == "BULLISH":
        for i in range(len(df) - 1, max(len(df) - 20, 0), -1):
            if float(df["close"].iloc[i]) < float(df["open"].iloc[i]):
                result["order_block"] = {
                    "type": "BULLISH_OB",
                    "low": round(float(df["low"].iloc[i]), 8),
                    "high": round(float(df["high"].iloc[i]), 8),
                }
                break

    result["fvg"] = _fair_value_gaps(df)
    return result
