"""
Faz 2 — Hesap içi para transferi (transfer_funds + endpoint) testleri.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.modules.module1_account import KuCoinAccount
from src.models.account import AccountBalancesResponse


def _account_with_mock_transfer():
    a = KuCoinAccount()
    a.exchange = MagicMock()
    a.exchange.transfer = AsyncMock(return_value={"id": "TX123"})
    a.get_balances = AsyncMock(return_value=AccountBalancesResponse(
        success=True, data={"accounts": [{"account": "futures", "total_usdt": 10.0}]},
        error=None, timestamp="t"))
    return a


class TestTransferFunds:
    @pytest.mark.asyncio
    async def test_spot_to_futures_maps_ccxt_args(self):
        a = _account_with_mock_transfer()
        r = await a.transfer_funds("USDT", 10, "spot", "futures")
        assert r["success"] is True
        assert r["data"]["transfer_id"] == "TX123"
        # ccxt transfer doğru hesap tiplerine çevrildi (spot→trade, futures→future)
        args = a.exchange.transfer.call_args[0]
        assert args == ("USDT", 10.0, "trade", "future")
        # transfer sonrası güncel bakiye döndü (2a)
        assert r["data"]["accounts"][0]["account"] == "futures"

    @pytest.mark.asyncio
    async def test_all_directions_valid(self):
        a = _account_with_mock_transfer()
        for src, dst in [("spot", "margin"), ("funding", "spot"), ("margin", "futures"),
                         ("futures", "funding")]:
            r = await a.transfer_funds("USDT", 5, src, dst)
            assert r["success"] is True, f"{src}->{dst} başarısız"

    @pytest.mark.asyncio
    async def test_same_account_rejected(self):
        a = _account_with_mock_transfer()
        r = await a.transfer_funds("USDT", 10, "spot", "spot")
        assert r["success"] is False and "aynı" in r["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_account_rejected(self):
        a = _account_with_mock_transfer()
        r = await a.transfer_funds("USDT", 10, "spot", "banka")
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_nonpositive_amount_rejected(self):
        a = _account_with_mock_transfer()
        assert (await a.transfer_funds("USDT", 0, "spot", "margin"))["success"] is False
        assert (await a.transfer_funds("USDT", -5, "spot", "margin"))["success"] is False

    @pytest.mark.asyncio
    async def test_empty_currency_rejected(self):
        a = _account_with_mock_transfer()
        r = await a.transfer_funds("", 10, "spot", "margin")
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_ccxt_error_handled(self):
        a = _account_with_mock_transfer()
        a.exchange.transfer = AsyncMock(side_effect=Exception("insufficient balance"))
        r = await a.transfer_funds("USDT", 10, "spot", "futures")
        assert r["success"] is False
        assert "insufficient" in r["error"].lower()


class TestTransferEndpoint:
    @pytest.fixture(scope="class")
    def client(self, tmp_path_factory):
        from src.main import app, user_store
        from src.auth.auth_service import hash_password
        db = tmp_path_factory.mktemp("transfer")
        user_store.db_path = str(db / "auth.db")
        user_store._initialized = False
        app.state.auth_enabled = True

        async def seed():
            await user_store.init_db()
            await user_store.create_user("u", hash_password("parola12345"), role="admin")
        asyncio.run(seed())
        return TestClient(app)

    def test_requires_auth(self, client):
        client.cookies.clear()
        r = client.post("/api/v1/account/transfer",
                        json={"currency": "USDT", "amount": 10, "from_account": "spot", "to_account": "futures"})
        assert r.status_code == 401

    def test_frontend_has_transfer_form(self, client):
        client.app.state.auth_enabled = False
        r = client.get("/")
        for el in ['id="transfer-currency"', 'id="transfer-from"', 'id="transfer-to"',
                   'id="transfer-btn"', 'data-info="transfer"']:
            assert el in r.text
        js = client.get("/static/js/app.js").text
        assert "transferFunds" in js and "/account/transfer" in js
        client.app.state.auth_enabled = True
