"""
Composite Scoring Engine (MODULE_2_SPEC 4.2 & 4.3).

İndikatör katmanı çıktılarından (trend, momentum, strength, volatility,
structure) ağırlıklı 0-100 boğa/ayı skoru üretir; risk filtrelerini uygular
ve insan-okunabilir gerekçelerle bir sinyal durumu döndürür.

Not: Türev (Katman 8) veri kaynağı bu fazda mevcut olmadığından ilgili
puan satırları hesaba katılmaz; skor mevcut feature'lar üzerinden 100'e
normalize edilir.
"""


def _score_trend(trend: dict) -> tuple[float, float, list]:
    bull = bear = 0.0
    reasons = []
    if not trend:
        return bull, bear, reasons
    regime, cross = trend.get("regime"), trend.get("cross")
    if regime == "BULLISH" and cross == "GOLDEN_CROSS":
        bull += 15; reasons.append("Fiyat EMA200 üstünde ve EMA50>EMA200 (Golden Cross)")
    elif regime == "BEARISH" and cross == "DEATH_CROSS":
        bear += 15; reasons.append("Fiyat EMA200 altında ve EMA50<EMA200 (Death Cross)")

    st = trend.get("supertrend")
    if st:
        if st.get("direction") == 1:
            bull += 5; reasons.append("Supertrend bullish")
        elif st.get("direction") == -1:
            bear += 5; reasons.append("Supertrend bearish")

    ich = trend.get("ichimoku")
    if ich:
        if ich.get("position") == "ABOVE_CLOUD":
            bull += 5; reasons.append("Fiyat Ichimoku bulutu üzerinde")
        elif ich.get("position") == "BELOW_CLOUD":
            bear += 5; reasons.append("Fiyat Ichimoku bulutu altında")
    return bull, bear, reasons


def _score_momentum(mom: dict) -> tuple[float, float, list]:
    bull = bear = 0.0
    reasons = []
    if not mom:
        return bull, bear, reasons
    rsi = mom.get("rsi")
    if rsi and rsi.get("slope_3_bars") is not None:
        if rsi["value"] > 50 and rsi["slope_3_bars"] > 0:
            bull += 8; reasons.append(f"RSI {rsi['value']} > 50 ve yükseliyor")
        elif rsi["value"] < 50 and rsi["slope_3_bars"] < 0:
            bear += 8; reasons.append(f"RSI {rsi['value']} < 50 ve düşüyor")

    macd = mom.get("macd")
    if macd:
        hist = macd.get("histogram")
        if hist is not None and hist > 0:
            bull += 7; reasons.append("MACD histogram pozitif")
        elif hist is not None and hist < 0:
            bear += 7; reasons.append("MACD histogram negatif")
    return bull, bear, reasons


def _score_structure(struct: dict) -> tuple[float, float, list]:
    bull = bear = 0.0
    reasons = []
    if not struct:
        return bull, bear, reasons
    if struct.get("bos") == "BULLISH":
        bull += 12; reasons.append("Bullish BOS (yapı yukarı kırıldı)")
    elif struct.get("bos") == "BEARISH":
        bear += 12; reasons.append("Bearish BOS (yapı aşağı kırıldı)")

    fvg = struct.get("fvg") or []
    if any(g.get("type") == "BULLISH" for g in fvg):
        bull += 8; reasons.append("Aktif Bullish FVG")
    if any(g.get("type") == "BEARISH" for g in fvg):
        bear += 8; reasons.append("Aktif Bearish FVG")
    return bull, bear, reasons


def _score_strength(strength: dict) -> tuple[float, float, list]:
    bull = bear = 0.0
    reasons = []
    if not strength:
        return bull, bear, reasons
    adx = strength.get("adx")
    if adx and adx.get("value") is not None and adx["value"] > 25:
        # ADX yön vermez; +DI/-DI yönü ile ağırlığı taraflara dağıt.
        if adx.get("plus_di") is not None and adx.get("minus_di") is not None:
            if adx["plus_di"] > adx["minus_di"]:
                bull += 5; reasons.append(f"ADX {adx['value']} güçlü trend (+DI>−DI)")
            else:
                bear += 5; reasons.append(f"ADX {adx['value']} güçlü trend (−DI>+DI)")
    return bull, bear, reasons


def _score_volume(volume: dict) -> tuple[float, float, list]:
    """Hacim & akış puanlaması (spec 4.2: RVOL+VWAP, CMF, OBV)."""
    bull = bear = 0.0
    reasons = []
    if not volume:
        return bull, bear, reasons

    rvol = volume.get("rvol") or {}
    vwap = volume.get("vwap") or {}
    if rvol.get("regime") == "HIGH" and vwap.get("price_above_vwap") is True:
        bull += 10; reasons.append("Yüksek RVOL ve fiyat VWAP üstünde")
    elif rvol.get("regime") == "HIGH" and vwap.get("price_above_vwap") is False:
        bear += 10; reasons.append("Yüksek RVOL ve fiyat VWAP altında")

    cmf = volume.get("cmf") or {}
    if cmf.get("regime") == "INFLOW":
        bull += 5; reasons.append("CMF net sermaye girişi")
    elif cmf.get("regime") == "OUTFLOW":
        bear += 5; reasons.append("CMF net sermaye çıkışı")

    obv = volume.get("obv") or {}
    if obv.get("above_ema20") is True:
        bull += 5; reasons.append("OBV EMA20 üzerinde")
    elif obv.get("above_ema20") is False:
        bear += 5; reasons.append("OBV EMA20 altında")

    return bull, bear, reasons


def _score_derivatives(derivatives: dict | None) -> tuple[float, float, list]:
    """Türev piyasa puanlaması (Katman 8: funding rate & open interest)."""
    bull = bear = 0.0
    reasons = []
    if not derivatives or not derivatives.get("available"):
        return bull, bear, reasons

    fr = derivatives.get("funding_rate") or {}
    st = fr.get("status")
    val = fr.get("value")
    if st == "OVERHEATED_SHORT":
        bull += 10
        reasons.append(f"Negatif fonlama ({val}): Short tarafı sıkışık, yukarı tepki potansiyeli")
    elif st == "OVERHEATED_LONG":
        bear += 10
        reasons.append(f"Aşırı pozitif fonlama ({val}): Long tarafı kalabalık, long squeeze riski")
    elif st == "NORMAL" and val is not None:
        reasons.append(f"Fonlama oranı dengeli ({val})")

    oi = derivatives.get("open_interest") or {}
    if oi.get("amount") is not None:
        reasons.append(f"Açık pozisyon hacmi: {oi['amount']:,.0f}")

    return bull, bear, reasons


def _risk_filters(indicators: dict, market_type: str = "spot") -> list:
    """Sahte sinyal / risk filtreleri (spec 3.3, 3.5). Uyarı listesi döndürür."""
    warnings = []
    strength = indicators.get("strength") or {}
    adx = strength.get("adx") or {}
    chop = strength.get("choppiness") or {}
    vol = indicators.get("volatility") or {}

    if adx.get("value") is not None and adx["value"] < 20:
        warnings.append("Düşük ADX (<20): Trend zayıf, range riski.")
    if chop.get("regime") == "CONSOLIDATION":
        warnings.append("Choppiness yüksek: Konsolidasyon/yatay bant.")
    if adx.get("regime") == "OVEREXTENDED":
        warnings.append("ADX aşırı yüksek (>40): Trend tükenme/klimaks riski.")
    bk = vol.get("bollinger_keltner") or {}
    if bk.get("squeeze") == "SQUEEZE_ON":
        warnings.append("Bollinger/Keltner Squeeze aktif: Düşük volatilite, patlama beklentisi.")

    # Piyasa türü özel risk uyarıları
    if market_type == "futures":
        deriv = indicators.get("derivatives") or {}
        fr = deriv.get("funding_rate") or {}
        if fr.get("status") in ("OVERHEATED_LONG", "OVERHEATED_SHORT"):
            warnings.append(f"Vadeli Uyarı: Aşırı fonlama oranı ({fr.get('status')}) — ani tasfiye (liquidation cascade) riski.")
    elif market_type == "margin":
        warnings.append("Marjin Uyarısı: Kaldıraçlı borçlanma — teminat seviyesini ve faiz yükünü izleyin.")

    return warnings


def compute_score(indicators: dict, market_type: str = "spot") -> dict:
    """
    Ağırlıklı boğa/ayı skoru ve sinyal durumu üretir.

    Returns:
        {
          "bull_score": 0-100, "bear_score": 0-100, "net_score": ...,
          "signal": "STRONG_BULLISH"|"BULLISH"|"NEUTRAL"|"BEARISH"|"STRONG_BEARISH",
          "reasons": [...], "warnings": [...]
        }
    """
    layers = [
        _score_trend(indicators.get("trend")),
        _score_momentum(indicators.get("momentum")),
        _score_strength(indicators.get("strength")),
        _score_volume(indicators.get("volume")),
        _score_structure(indicators.get("structure")),
    ]
    if market_type == "futures" or indicators.get("derivatives"):
        layers.append(_score_derivatives(indicators.get("derivatives")))

    bull = sum(l[0] for l in layers)
    bear = sum(l[1] for l in layers)
    reasons = [r for l in layers for r in l[2]]
    warnings = _risk_filters(indicators, market_type=market_type)

    # Mevcut feature'ların maksimum toplam puanı (türev dahil/hariç):
    max_points = 90.0 if (market_type == "futures" or indicators.get("derivatives")) else 80.0
    bull_score = round(min(bull / max_points * 100, 100), 1)
    bear_score = round(min(bear / max_points * 100, 100), 1)
    net = round(bull_score - bear_score, 1)

    # Choppiness yüksekse sinyali nötrle (spec 4.3).
    chop = (indicators.get("strength") or {}).get("choppiness") or {}
    force_neutral = chop.get("regime") == "CONSOLIDATION"

    if force_neutral:
        signal = "NEUTRAL"
    elif bull_score >= 80 and not warnings:
        signal = "STRONG_BULLISH"
    elif bull_score >= 60:
        signal = "BULLISH"
    elif bear_score >= 80 and not warnings:
        signal = "STRONG_BEARISH"
    elif bear_score >= 60:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    return {
        "bull_score": bull_score,
        "bear_score": bear_score,
        "net_score": net,
        "signal": signal,
        "market_type": market_type,
        "reasons": reasons,
        "warnings": warnings,
    }

