"""
Faz 1 — Auth endpoint'leri (login/logout/me) entegrasyon testleri.
TestClient localhost'tan (127.0.0.1) çağırır → yerel ağ kabul edilir, TOTP atlanır.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client_and_user(tmp_path_factory):
    from src.main import app, user_store
    from src.auth.auth_service import hash_password

    # İzole test DB'leri
    db_dir = tmp_path_factory.mktemp("authep")
    user_store.db_path = str(db_dir / "auth.db")
    user_store._initialized = False

    async def seed():
        await user_store.init_db()
        await user_store.create_user("tester", hash_password("parola123"), role="admin")
    asyncio.run(seed())

    return TestClient(app)


def test_me_requires_auth(client_and_user):
    c = client_and_user
    r = c.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_login_wrong_password(client_and_user):
    c = client_and_user
    r = c.post("/api/v1/auth/login", json={"username": "tester", "password": "yanlis"})
    assert r.status_code == 401
    assert r.json()["success"] is False


def test_login_success_sets_cookie_and_me(client_and_user):
    c = client_and_user
    r = c.post("/api/v1/auth/login", json={"username": "tester", "password": "parola123"})
    assert r.status_code == 200
    assert r.json()["data"]["user"]["username"] == "tester"
    # cookie ile me
    me = c.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "tester"


def test_logout_invalidates_session(client_and_user):
    c = client_and_user
    c.post("/api/v1/auth/login", json={"username": "tester", "password": "parola123"})
    assert c.get("/api/v1/auth/me").status_code == 200
    c.post("/api/v1/auth/logout")
    assert c.get("/api/v1/auth/me").status_code == 401
