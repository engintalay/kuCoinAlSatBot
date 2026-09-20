"""
KuCoin Al-Sat Botu — Dinamik Öneri Motoru (MODULE_3_SPEC 2.7)

Açık emirleri ve güncel piyasa fiyatını karşılaştırarak kullanıcıya
uygulanabilir güncelleme tavsiyeleri üretir (SL'yi break-even'a çek,
kâr realizasyonu, SL'ye yakınlık uyarısı vb.).
"""

from src.utils.logger import logger
from src.utils.time_sync import timestamp


class RecommendationEngine:
    """Açık emirler + canlı fiyattan uygulanabilir tavsiyeler üretir."""

    def __init__(self, orders, market):
        self.orders = orders
        self.market = market

    async def get_recommendations(self) -> dict:
        try:
            open_res = await self.orders.get_open_orders()
            if not open_res.success:
                return {"success": False, "data": {}, "error": open_res.error,
                        "timestamp": timestamp()}

            open_orders = open_res.data.get("orders", [])
            recs = []
            price_cache: dict[str, float] = {}

            for o in open_orders:
                symbol = o.get("symbol")
                if symbol not in price_cache:
                    tk = await self.market.get_ticker(symbol)
                    price_cache[symbol] = float(tk.data["last_price"]) if tk.success else None
                last = price_cache.get(symbol)
                if last is None:
                    continue

                price = float(o.get("price", 0) or 0)
                side = o.get("side")
                oid = o.get("id")
                leg = o.get("bracket_leg")

                # SL ayağı için: fiyat SL'ye çok yaklaştıysa uyarı
                if leg == "sl" and price > 0:
                    dist_pct = abs(last - price) / last * 100
                    if dist_pct < 1.0:
                        recs.append({
                            "order_id": oid, "symbol": symbol, "type": "SL_NEAR",
                            "severity": "warning",
                            "message": f"{symbol} fiyatı Stop-Loss'a çok yakın (%{dist_pct:.2f}). "
                                       f"Pozisyonu gözden geçirin.",
                            "action": None,
                        })

                # TP ayağı için: fiyat TP'yi geçtiyse realizasyon önerisi
                if leg in ("tp1", "tp2") and price > 0:
                    reached = (last >= price) if side == "sell" else (last <= price)
                    # sell exit (long TP) -> fiyat TP üstüne çıktıysa
                    if side == "sell" and last >= price * 0.998:
                        recs.append({
                            "order_id": oid, "symbol": symbol, "type": "TP_REACHED",
                            "severity": "success",
                            "message": f"{symbol} {leg.upper()} hedefine ulaşıldı/yaklaştı "
                                       f"({last} ≈ {price}). Kârı realize edebilirsiniz.",
                            "action": {"kind": "info"},
                        })

            return {"success": True,
                    "data": {"count": len(recs), "recommendations": recs},
                    "error": None, "timestamp": timestamp()}
        except Exception as e:
            logger.error(f"Öneri motoru hatası: {e}")
            return {"success": False, "data": {}, "error": str(e), "timestamp": timestamp()}

    async def apply_recommendation(self, order_id: str, new_price: float | None = None) -> dict:
        """Bir tavsiyeyi uygular (örn. SL fiyatını güncelle)."""
        try:
            res = await self.orders.amend_order(order_id, price=new_price)
            return {"success": res.success, "data": res.data, "error": res.error,
                    "timestamp": timestamp()}
        except Exception as e:
            logger.error(f"Öneri uygulama hatası: {e}")
            return {"success": False, "data": {}, "error": str(e), "timestamp": timestamp()}
