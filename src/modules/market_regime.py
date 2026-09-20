"""
Katman 9: Piyasa Geneli Rejim Göstergeleri (Faz 2c / Market-wide Regime)
MODULE_2_SPEC 3.9: BTC Dominance, Total Market Cap, Stablecoin Dominance.

Veri kaynağı: CoinGecko `/api/v3/global` (ücretsiz, API anahtarı gerektirmez).
Yalnızca kamuya açık piyasa verisi çekilir; proje verisi dışarı gönderilmez.
"""

import requests

from src.utils.logger import logger
from src.utils.time_sync import timestamp

COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"


class MarketRegime:
    """Piyasa geneli rejim göstergeleri (BTC.D, Total MCap, Stablecoin.D)."""

    def get_regime(self, timeout: int = 10) -> dict:
        """
        Piyasa geneli rejim verilerini çeker ve yorumlar.

        Returns envelope:
          data: {
            total_market_cap_usd, market_cap_change_24h_pct,
            btc_dominance, eth_dominance, stablecoin_dominance,
            regime: RISK_ON | RISK_OFF | NEUTRAL,
            altseason_hint: bool, notes: [...]
          }
        """
        try:
            resp = requests.get(COINGECKO_GLOBAL_URL, timeout=timeout)
            resp.raise_for_status()
            d = resp.json().get("data", {})

            mcp = d.get("market_cap_percentage", {})
            btc_d = mcp.get("btc")
            eth_d = mcp.get("eth")
            usdt_d = mcp.get("usdt", 0.0) or 0.0
            usdc_d = mcp.get("usdc", 0.0) or 0.0
            stable_d = round(usdt_d + usdc_d, 4)
            total_mcap = d.get("total_market_cap", {}).get("usd")
            mcap_chg = d.get("market_cap_change_percentage_24h_usd")

            notes = []
            regime = "NEUTRAL"
            # Stablecoin dominansı yüksek + piyasa düşüyorsa risk-off (nakite kaçış)
            if mcap_chg is not None and mcap_chg < -2 and stable_d > 8:
                regime = "RISK_OFF"
                notes.append("Piyasa düşüşte ve stablecoin dominansı yüksek: nakite kaçış (risk-off).")
            elif mcap_chg is not None and mcap_chg > 2:
                regime = "RISK_ON"
                notes.append("Toplam piyasa değeri artışta: risk iştahı yüksek (risk-on).")

            # Altseason ipucu: BTC.D düşük/düşüyorsa altcoinler öne çıkabilir
            altseason_hint = btc_d is not None and btc_d < 50.0
            if altseason_hint:
                notes.append("BTC dominansı %50 altında: altcoin rallisi (altseason) olasılığı.")
            elif btc_d is not None and btc_d > 55.0:
                notes.append("BTC dominansı yüksek: sermaye BTC'de yoğunlaşıyor, altcoinlerde temkin.")

            return {
                "success": True,
                "data": {
                    "total_market_cap_usd": total_mcap,
                    "market_cap_change_24h_pct": round(mcap_chg, 2) if mcap_chg is not None else None,
                    "btc_dominance": round(btc_d, 2) if btc_d is not None else None,
                    "eth_dominance": round(eth_d, 2) if eth_d is not None else None,
                    "stablecoin_dominance": stable_d,
                    "regime": regime,
                    "altseason_hint": altseason_hint,
                    "notes": notes,
                },
                "error": None,
                "timestamp": timestamp(),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Piyasa geneli veri hatası: {e}")
            return {"success": False, "data": {},
                    "error": f"Piyasa geneli verisi alınamadı: {e}", "timestamp": timestamp()}
        except Exception as e:
            logger.error(f"Piyasa rejimi hatası: {e}")
            return {"success": False, "data": {}, "error": str(e), "timestamp": timestamp()}
