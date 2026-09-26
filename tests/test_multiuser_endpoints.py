"""
Faz 1 — Çok kullanıcılı request-scoped client entegrasyon testi.
Her kullanıcının endpoint çağrısı kendi API anahtarıyla oluşturulan client'ı
kullanmalı (izolasyon).
"""

import asyncio
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def multi_user_client(tmp_path_factory):
    from src.main import app, user_store, client_factory
    from src.auth.auth_service import hash_password

    db = tmp_path_factory.mktemp("mu")
    user_store.db_path = str(db / "auth.db")
    user_store._initialized = False
    app.state.auth_enabled = True

    async def seed():
        await user_store.init_db()
        a = await user_store.create_user("alice", hash_password("p1"), role="admin")
        b = await user_store.create_user("bob", hash_password("p2"), role="user")
        await user_store.save_api_keys(a["id"], "ALICE_KEY", "ALICE_SEC", "ALICE_PASS")
        await user_store.save_api_keys(b["id"], "BOB_KEY", "BOB_SEC", "BOB_PASS")
    asyncio.run(seed())
    # Fabrika önbelleğini temizle (önceki testlerden kalmasın)
    asyncio.run(client_factory.close_all())
    return app, user_store, client_factory


def test_each_user_gets_own_client(multi_user_client):
    app, user_store, factory = multi_user_client

    async def check():
        ua = await user_store.get_user_by_username("alice")
        ub = await user_store.get_user_by_username("bob")
        oa = await factory.get_orders_for_user(ua["id"])
        ob = await factory.get_orders_for_user(ub["id"])
        oa.connect(); ob.connect()
        assert oa is not ob
        assert oa.exchange.apiKey == "ALICE_KEY"
        assert ob.exchange.apiKey == "BOB_KEY"
        await factory.close_all()
    asyncio.run(check())


def test_login_required_for_balances(multi_user_client):
    app, _, _ = multi_user_client
    c = TestClient(app)
    c.cookies.clear()
    assert c.get("/api/v1/account/balances").status_code == 401


def test_account_object_isolation(multi_user_client):
    """Account client'ları kullanıcı bazlı ayrı olmalı."""
    app, user_store, factory = multi_user_client

    async def check():
        ua = await user_store.get_user_by_username("alice")
        ub = await user_store.get_user_by_username("bob")
        aa = await factory.get_account_for_user(ua["id"])
        ab = await factory.get_account_for_user(ub["id"])
        assert aa is not ab
        aa.connect(); ab.connect()
        assert aa.exchange.apiKey == "ALICE_KEY"
        assert ab.exchange.apiKey == "BOB_KEY"
        await factory.close_all()
    asyncio.run(check())
