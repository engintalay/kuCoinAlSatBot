"""
Faz 1 — ExchangeClientFactory & credential override testleri.
"""

import pytest
import asyncio

from src.auth.crypto_vault import CryptoVault
from src.auth.user_store import UserStore
from src.auth.auth_service import hash_password
from src.modules.module2_market import KuCoinMarket
from src.exchanges.factory import ExchangeClientFactory


def _store(tmp_path):
    return UserStore(db_path=str(tmp_path / "fac.db"),
                     vault=CryptoVault(master_key=CryptoVault.generate_key()))


def _assert_connect_is_idempotent(monkeypatch, client, module_path):
    from unittest.mock import MagicMock

    spot_factory = MagicMock(return_value=object())
    futures_factory = MagicMock(return_value=object())
    monkeypatch.setattr(f"{module_path}.ccxt.async_support.kucoin", spot_factory)
    monkeypatch.setattr(f"{module_path}.ccxt.async_support.kucoinfutures", futures_factory)

    assert client.connect() is True
    spot_exchange = client.exchange
    futures_exchange = client.futures_exchange
    assert client.connect() is True

    assert client.exchange is spot_exchange
    assert client.futures_exchange is futures_exchange
    spot_factory.assert_called_once()
    futures_factory.assert_called_once()


class TestCredentialOverride:
    def test_orders_uses_injected_credentials(self):
        from src.modules.module3_orders import KuCoinOrders
        creds = {"api_key": "K1", "api_secret": "S1", "api_passphrase": "P1", "is_sandbox": False}
        o = KuCoinOrders(credentials=creds)
        assert o.connect() is True
        assert o.exchange.apiKey == "K1"
        assert o.futures_exchange.apiKey == "K1"
        asyncio.run(o.close())

    def test_account_uses_injected_credentials(self):
        from src.modules.module1_account import KuCoinAccount
        creds = {"api_key": "AK", "api_secret": "AS", "api_passphrase": "AP"}
        a = KuCoinAccount(credentials=creds)
        assert a.connect() is True
        assert a.exchange.apiKey == "AK"
        asyncio.run(a.close())

    def test_orders_connect_does_not_replace_open_exchanges(self, monkeypatch):
        from src.modules.module3_orders import KuCoinOrders
        _assert_connect_is_idempotent(monkeypatch, KuCoinOrders(), "src.modules.module3_orders")

    def test_account_connect_does_not_replace_open_exchanges(self, monkeypatch):
        from src.modules.module1_account import KuCoinAccount
        _assert_connect_is_idempotent(monkeypatch, KuCoinAccount(), "src.modules.module1_account")


class TestFactory:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("getter_name", ["get_orders_for_user", "get_account_for_user"])
    async def test_concurrent_requests_share_one_user_client(self, tmp_path, monkeypatch, getter_name):
        import asyncio

        fac = ExchangeClientFactory(_store(tmp_path), KuCoinMarket())
        first_lookup_started = asyncio.Event()
        allow_lookup_to_finish = asyncio.Event()
        lookup_count = 0

        async def concurrent_credentials(user_id, exchange="kucoin"):
            nonlocal lookup_count
            lookup_count += 1
            first_lookup_started.set()
            await allow_lookup_to_finish.wait()
            return {"api_key": "K", "api_secret": "S", "api_passphrase": "P"}

        monkeypatch.setattr(fac, "_credentials", concurrent_credentials)
        get_client = getattr(fac, getter_name)
        first_task = asyncio.create_task(get_client(7))
        await first_lookup_started.wait()
        second_task = asyncio.create_task(get_client(7))
        allow_lookup_to_finish.set()
        first, second = await asyncio.gather(first_task, second_task)

        assert first is second
        assert lookup_count == 1
        await fac.close_all()

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
