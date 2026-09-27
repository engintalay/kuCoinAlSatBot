"""
KuCoin Al-Sat Botu — Borsa Client Fabrikası (Faz 1 Task 6)
Giriş yapan kullanıcının çözülmüş API anahtarıyla request-scoped borsa
client'ları (Orders/Account) üretir ve kullanıcı bazlı önbelleğe alır.
Market (public veri) paylaşılır — kimlik bilgisi gerektirmez.
"""

from src.modules.module2_market import KuCoinMarket
from src.modules.module3_orders import KuCoinOrders
from src.modules.module1_account import KuCoinAccount
from src.auth.user_store import UserStore
from src.utils.logger import logger


class ExchangeClientFactory:
    """Kullanıcı bazlı Orders/Account client üretir ve önbelleğe alır."""

    def __init__(self, user_store: UserStore, shared_market: KuCoinMarket, settings_mgr=None):
        self.user_store = user_store
        self.market = shared_market          # public veri, paylaşımlı
        self.settings_mgr = settings_mgr
        self._orders: dict[int, KuCoinOrders] = {}
        self._accounts: dict[int, KuCoinAccount] = {}

    async def _credentials(self, user_id: int, exchange: str = "kucoin") -> dict | None:
        return await self.user_store.get_api_keys(user_id, exchange)

    async def get_orders_for_user(self, user_id: int) -> KuCoinOrders:
        if user_id not in self._orders:
            creds = await self._credentials(user_id)
            user_orders = KuCoinOrders(market=self.market, credentials=creds)
            if self.settings_mgr:
                try:
                    s_data = await self.settings_mgr.for_user(user_id).get_settings()
                    saved_mode = s_data.get("data", {}).get("default_mode")
                    if saved_mode in ("paper", "live"):
                        await user_orders.switch_mode(saved_mode)
                except Exception as e:
                    logger.debug(f"Kullanıcı varsayılan mod yükleme hatası (user={user_id}): {e}")
            self._orders[user_id] = user_orders
        return self._orders[user_id]

    async def get_account_for_user(self, user_id: int) -> KuCoinAccount:
        if user_id not in self._accounts:
            creds = await self._credentials(user_id)
            orders = await self.get_orders_for_user(user_id)
            self._accounts[user_id] = KuCoinAccount(orders=orders, credentials=creds)
        return self._accounts[user_id]

    async def invalidate_user(self, user_id: int) -> None:
        """Kullanıcının önbelleğe alınmış client'larını temizler (kapatarak)."""
        for cache in (self._orders, self._accounts):
            obj = cache.pop(user_id, None)
            if obj is not None:
                try:
                    await obj.close()
                except Exception as e:
                    logger.debug(f"Client kapatma hatası (user={user_id}): {e}")

    async def close_all(self) -> None:
        for cache in (self._orders, self._accounts):
            for obj in list(cache.values()):
                try:
                    await obj.close()
                except Exception:
                    pass
            cache.clear()
