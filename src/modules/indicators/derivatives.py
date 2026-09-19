"""
Katman 8: Türev Piyasa Verileri (Faz 2c)
MODULE_2_SPEC 3.8: Funding Rate, Open Interest.

KuCoin Futures (`kucoinfutures`) ayrı bir ccxt exchange'idir. Spot sembol
(örn. 'BTC/USDT') vadeli sembole ('BTC/USDT:USDT') çevrilir.

Not: CVD (Cumulative Volume Delta) ve L/S Ratio, taker akış / özel endpoint
verisi gerektirdiğinden bu sürümde funding + open interest ile sınırlıdır.
"""

import ccxt.async_support

from src.utils.logger import logger
from src.utils.time_sync import timestamp

FUNDING_HIGH = 0.0003   # +%0.03
FUNDING_LOW = -0.0003   # -%0.03


def _to_swap_symbol(symbol: str) -> str:
    """'BTC/USDT' -> 'BTC/USDT:USDT' (linear perpetual)."""
    if ":" in symbol:
        return symbol
    base, _, quote = symbol.partition("/")
    if not quote:
        return symbol
    return f"{base}/{quote}:{quote}"


class DerivativesData:
    """KuCoin Futures türev verisi (funding, open interest)."""

    def __init__(self):
        self.exchange: ccxt.async_support.kucoinfutures | None = None

    def _ensure(self) -> bool:
        if self.exchange is None:
            try:
                self.exchange = ccxt.async_support.kucoinfutures()
            except Exception as e:
                logger.error(f"kucoinfutures bağlantı hatası: {e}")
                return False
        return self.exchange is not None

    async def get_derivatives(self, symbol: str) -> dict:
        """
        Türev feature'ları.

        Returns:
            {
              "available": bool,
              "funding_rate": {"value":.., "status":..},
              "open_interest": {"amount":..},
              "error": str | None
            }
        """
        result = {"available": False, "funding_rate": None,
                  "open_interest": None, "error": None}
        if not self._ensure():
            result["error"] = "KuCoin Futures bağlantısı kurulamadı"
            return result

        swap = _to_swap_symbol(symbol)

        # Funding rate
        try:
            fr = await self.exchange.fetch_funding_rate(swap)
            rate = fr.get("fundingRate")
            if rate is not None:
                rate = float(rate)
                if rate > FUNDING_HIGH:
                    status = "OVERHEATED_LONG"   # long tarafı kalabalık, squeeze riski
                elif rate < FUNDING_LOW:
                    status = "OVERHEATED_SHORT"   # short tarafı kalabalık, short squeeze fırsatı
                else:
                    status = "NORMAL"
                result["funding_rate"] = {"value": rate, "status": status}
        except Exception as e:
            logger.error(f"Funding rate hatası ({swap}): {e}")

        # Open interest
        try:
            oi = await self.exchange.fetch_open_interest(swap)
            amount = oi.get("openInterestAmount") or oi.get("openInterestValue")
            if amount is not None:
                result["open_interest"] = {"amount": float(amount)}
        except Exception as e:
            logger.error(f"Open interest hatası ({swap}): {e}")

        result["available"] = result["funding_rate"] is not None or result["open_interest"] is not None
        return result

    async def close(self) -> None:
        if self.exchange is not None:
            try:
                await self.exchange.close()
            except Exception as e:
                logger.error(f"kucoinfutures kapatma hatası: {e}")
            finally:
                self.exchange = None
