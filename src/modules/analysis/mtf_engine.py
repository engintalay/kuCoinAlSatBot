"""
Multi-Timeframe (MTF) Karar Hiyerarşisi (MODULE_2_SPEC 3.10).

Üç seviyeli doğrulama:
  4H  -> Makro rejim (yön)
  1H  -> Kurulum (setup) teyidi
  15m -> Giriş tetikleyicisi (trigger)

Yalnızca üst zaman dilimi yönüyle uyumlu alt-tetikleyiciler onaylanır.
"""


def evaluate_mtf(regime_4h: dict, setup_1h: dict, trigger_15m: dict) -> dict:
    """
    Her timeframe için compute_score çıktısı alır ve hiyerarşik karar üretir.

    Args:
        regime_4h / setup_1h / trigger_15m: compute_score() dönüşleri.

    Returns:
        {
          "regime": "BULLISH"|"BEARISH"|"NEUTRAL",
          "aligned": bool,
          "final_signal": "LONG_SETUP"|"SHORT_SETUP"|"NO_TRADE",
          "explanation": str
        }
    """
    def direction(score: dict) -> str:
        sig = (score or {}).get("signal", "NEUTRAL")
        if "BULLISH" in sig:
            return "BULLISH"
        if "BEARISH" in sig:
            return "BEARISH"
        return "NEUTRAL"

    d4 = direction(regime_4h)
    d1 = direction(setup_1h)
    d15 = direction(trigger_15m)

    # 4H nötrse işlem yok.
    if d4 == "NEUTRAL":
        return {
            "regime": d4, "aligned": False, "final_signal": "NO_TRADE",
            "explanation": "4H makro rejim nötr; net yön yok, işlem aranmaz.",
        }

    aligned = (d4 == d1 == d15)
    if aligned and d4 == "BULLISH":
        final = "LONG_SETUP"
        expl = "4H/1H/15m üçlü boğa uyumu: Long kurulum onaylandı."
    elif aligned and d4 == "BEARISH":
        final = "SHORT_SETUP"
        expl = "4H/1H/15m üçlü ayı uyumu: Short kurulum onaylandı."
    else:
        final = "NO_TRADE"
        expl = (f"Zaman dilimleri uyumsuz (4H={d4}, 1H={d1}, 15m={d15}); "
                f"yalnızca 4H yönüyle uyumlu kurulum beklenir.")

    return {"regime": d4, "aligned": aligned, "final_signal": final, "explanation": expl}
