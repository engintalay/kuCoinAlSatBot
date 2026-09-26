"""
Faz 1 — ExchangeClientFactory & credential override testleri.
"""

import pytest

from src.auth.crypto_vault import CryptoVault
from src.auth.user_store import UserStore
from src.auth.auth_service import hash_password
from src.modules.module2_market import KuCoinMarket
from src.exchanges.factory import ExchangeClientFactory


def _store(tmp_path):
    return UserStore(db_path=str(tmp_path / "fac.db"),
                     vault=CryptoVault(master_key=CryptoVault.generate_key()))


class TestCredentialOverride:
    def test_orders_uses_injected_credentials(self):
        from src.modules.module3_orders import KuCoinOrders
        creds = {"api_key": "K1", "api_secret": "S1", "api_passphrase": "P1", "is_sandbox": False}
        o = KuCoinOrders(credentials=creds)
        assert o.connect() is True
        assert o.exchange.apiKey == "K1"
        assert o.futures_exchange.apiKey == "K1"

    def test_account_uses_injected_credentials(self):
        from src.modules.module1_account import KuCoinAccount
        creds = {"api_key": "AK", "api_secret": "AS", "api_passphrase": "AP"}
        a = KuCoinAccount(credentials=creds)
        assert a.connect() is True
        assert a.exchange.apiKey == "AK"


class TestFactory:
    @pytest.mark.asyncio
    async def test_per_user_isolated_clients(self, tmp_path):
        s = _store(tmp_path)
        u1 = await s.create_user("u1", hash_password("p"))
        u2 = await s.create_user("u2", hash_password("p"))
        await s.save_api_keys(u1["id"], "KEY1", "SEC1", "PAS1")
        await s.save_api_keys(u2["id"], "KEY2", "SEC2", "PAS2")

        fac = ExchangeClientFactory(s, KuCoinMarket())
        o1 = await fac.get_orders_for_user(u1["id"])
        o2 = await fac.get_orders_for_user(u2["id"])
        assert o1 is not o2
        o1.connect(); o2.connect()
        assert o1.exchange.apiKey == "KEY1"
        assert o2.exchange.apiKey == "KEY2"
        # aynı kullanıcı → aynı (önbellek) instance
        assert await fac.get_orders_for_user(u1["id"]) is o1
        await fac.close_all()

    @pytest.mark.asyncio
    async def test_account_shares_market(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("u", hash_password("p"))
        await s.save_api_keys(u["id"], "K", "S", "P")
        market = KuCoinMarket()
        fac = ExchangeClientFactory(s, market)
        acc = await fac.get_account_for_user(u["id"])
        assert acc.orders.market is market
        await fac.close_all()

    @pytest.mark.asyncio
    async def test_invalidate_user(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("u", hash_password("p"))
        await s.save_api_keys(u["id"], "K", "S", "P")
        fac = ExchangeClientFactory(s, KuCoinMarket())
        o1 = await fac.get_orders_for_user(u["id"])
        await fac.invalidate_user(u["id"])
        o2 = await fac.get_orders_for_user(u["id"])
        assert o1 is not o2  # önbellek temizlendi, yeni instance
        await fac.close_all()
