"""
Katman 4: Hacim ve Para Akışı İndikatörleri (Faz 2b / Adım 3 tamamlama)
MODULE_2_SPEC 3.4: RVOL, OBV, VWAP (±σ bantları), MFI 14, CMF 20, Volume Profile.
"""

import numpy as np
import pandas as pd


def compute_volume(df: pd.DataFrame) -> dict:
    """
    Hacim & para akışı feature'ları.

    Returns:
        {
          "rvol": {"value":.., "regime":..},
          "obv": {"value":.., "above_ema20":..},
          "vwap": {"value":.., "price_above_vwap":.., "upper_1sigma":.., "lower_1sigma":..},
          "mfi": {"value":.., "regime":..},
          "cmf": {"value":.., "regime":..},
          "volume_profile": {"poc":.., "vah":.., "val":..}
        }
    """
    result = {"rvol": None, "obv": None, "vwap": None,
              "mfi": None, "cmf": None, "volume_profile": None}
    if len(df) < 20:
        return result

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    typical = (high + low + close) / 3

    # --- RVOL (Relative Volume) ---
    vol_sma20 = volume.rolling(20).mean()
    if pd.notna(vol_sma20.iloc[-1]) and vol_sma20.iloc[-1] > 0:
        rvol = float(volume.iloc[-1] / vol_sma20.iloc[-1])
        if rvol > 1.5:
            regime = "HIGH"
        elif rvol < 0.7:
            regime = "LOW"
        else:
            regime = "NORMAL"
        result["rvol"] = {"value": round(rvol, 3), "regime": regime}

    # --- OBV (On-Balance Volume) ---
    direction = np.sign(close.diff().fillna(0.0))
    obv = (direction * volume).cumsum()
    obv_ema20 = obv.ewm(span=20, adjust=False).mean()
    result["obv"] = {
        "value": round(float(obv.iloc[-1]), 4),
        "above_ema20": bool(obv.iloc[-1] > obv_ema20.iloc[-1]),
    }

    # --- VWAP (kümülatif oturum) + standart sapma bantları ---
    cum_vol = volume.cumsum()
    cum_tpv = (typical * volume).cumsum()
    vwap = cum_tpv / cum_vol.replace(0.0, np.nan)
    vwap_val = float(vwap.iloc[-1])
    # tipik fiyatın VWAP'e göre std sapması
    dev = typical - vwap
    var = (dev.pow(2) * volume).cumsum() / cum_vol.replace(0.0, np.nan)
    sigma = float(np.sqrt(var.iloc[-1])) if pd.notna(var.iloc[-1]) else 0.0
    result["vwap"] = {
        "value": round(vwap_val, 8),
        "price_above_vwap": bool(float(close.iloc[-1]) > vwap_val),
        "upper_1sigma": round(vwap_val + sigma, 8),
        "lower_1sigma": round(vwap_val - sigma, 8),
        "upper_2sigma": round(vwap_val + 2 * sigma, 8),
        "lower_2sigma": round(vwap_val - 2 * sigma, 8),
    }

    # --- MFI (Money Flow Index, 14) ---
    if len(df) >= 15:
        raw_flow = typical * volume
        tp_diff = typical.diff()
        pos_flow = raw_flow.where(tp_diff > 0, 0.0).rolling(14).sum()
        neg_flow = raw_flow.where(tp_diff < 0, 0.0).rolling(14).sum()
        mfr = pos_flow / neg_flow.replace(0.0, np.nan)
        mfi = 100 - (100 / (1 + mfr))
        mfi = mfi.fillna(100.0)
        mfi_val = float(mfi.iloc[-1])
        regime = "OVERBOUGHT" if mfi_val >= 80 else "OVERSOLD" if mfi_val <= 20 else "NEUTRAL"
        result["mfi"] = {"value": round(mfi_val, 2), "regime": regime}

    # --- CMF (Chaikin Money Flow, 20) ---
    hl_range = (high - low).replace(0.0, np.nan)
    mf_mult = ((close - low) - (high - close)) / hl_range
    mf_vol = (mf_mult * volume).fillna(0.0)
    cmf = mf_vol.rolling(20).sum() / volume.rolling(20).sum().replace(0.0, np.nan)
    cmf_val = cmf.iloc[-1]
    if pd.notna(cmf_val):
        v = float(cmf_val)
        regime = "INFLOW" if v > 0.05 else "OUTFLOW" if v < -0.05 else "NEUTRAL"
        result["cmf"] = {"value": round(v, 4), "regime": regime}

    # --- Volume Profile (POC / VAH / VAL) ---
    result["volume_profile"] = _volume_profile(high, low, close, volume)

    return result


def _volume_profile(high, low, close, volume, bins: int = 24, value_area: float = 0.70) -> dict | None:
    """
    Basit Volume Profile: fiyat aralığını bin'lere böler, hacmi dağıtır.
    POC = en yüksek hacimli seviye; VAH/VAL = hacmin %70'ini kapsayan bölge sınırları.
    """
    price_min = float(low.min())
    price_max = float(high.max())
    if price_max <= price_min:
        return None

    edges = np.linspace(price_min, price_max, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    hist = np.zeros(bins)
    # her mumun tipik fiyatını ilgili bin'e ekle
    typical = ((high + low + close) / 3).values
    vols = volume.values
    idx = np.clip(np.digitize(typical, edges) - 1, 0, bins - 1)
    for b, v in zip(idx, vols):
        hist[b] += v

    total = hist.sum()
    if total <= 0:
        return None

    poc_i = int(np.argmax(hist))
    poc = float(centers[poc_i])

    # Value area: POC'tan başlayıp iki yana genişleyerek %70 hacmi topla
    included = {poc_i}
    acc = hist[poc_i]
    lo, hi = poc_i, poc_i
    while acc < value_area * total and (lo > 0 or hi < bins - 1):
        left = hist[lo - 1] if lo > 0 else -1
        right = hist[hi + 1] if hi < bins - 1 else -1
        if right >= left:
            hi += 1; acc += hist[hi]; included.add(hi)
        else:
            lo -= 1; acc += hist[lo]; included.add(lo)

    vah = float(centers[max(included)])
    val = float(centers[min(included)])
    return {"poc": round(poc, 8), "vah": round(vah, 8), "val": round(val, 8)}
