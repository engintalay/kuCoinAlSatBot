"""
Faz 1 ek — Kullanıcı bazlı Borsa API anahtarı yönetimi (endpoint + frontend) testleri.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from src.main import app, user_store
    from src.auth.auth_service import hash_password

    db = tmp_path_factory.mktemp("apik")
    user_store.db_path = str(db / "auth.db")
    user_store._initialized = False
    app.state.auth_enabled = True

    async def seed():
        await user_store.init_db()
        await user_store.create_user("u", hash_password("parola12345"), role="admin")
    asyncio.run(seed())
    return TestClient(app)


def _login(c):
    c.post("/api/v1/auth/login", json={"username": "u", "password": "parola12345"})


class TestApiKeysEndpoint:
    def test_requires_auth(self, client):
        client.cookies.clear()
        assert client.get("/api/v1/settings/api-keys").status_code == 401
        assert client.post("/api/v1/settings/api-keys", json={"api_key": "x", "api_secret": "y"}).status_code == 401

    def test_initially_not_configured(self, client):
        _login(client)
        r = client.get("/api/v1/settings/api-keys")
        assert r.status_code == 200
        assert r.json()["data"]["configured"] is False

    def test_save_then_masked_get(self, client):
        _login(client)
        r = client.post("/api/v1/settings/api-keys", json={
            "api_key": "MYKEY1234", "api_secret": "SUPERSECRET", "api_passphrase": "PP", "is_sandbox": False})
        assert r.status_code == 200 and r.json()["success"] is True
        g = client.get("/api/v1/settings/api-keys").json()["data"]
        assert g["configured"] is True
        assert g["api_key_masked"] == "MYKE****34"
        assert g["api_passphrase_set"] is True
        # secret hiçbir şekilde yanıtta olmamalı
        assert "SUPERSECRET" not in str(g)

    def test_save_validation(self, client):
        _login(client)
        r = client.post("/api/v1/settings/api-keys", json={"api_key": "", "api_secret": ""})
        assert r.status_code == 400

    def test_saved_encrypted_and_decryptable(self, client):
        """Kaydedilen anahtar DB'de şifreli; store.get_api_keys ile çözülebilir."""
        from src.main import user_store
        _login(client)
        client.post("/api/v1/settings/api-keys", json={
            "api_key": "ENCKEY", "api_secret": "ENCSEC", "api_passphrase": "ENCPP"})

        async def check():
            u = await user_store.get_user_by_username("u")
            keys = await user_store.get_api_keys(u["id"], "kucoin")
            assert keys["api_key"] == "ENCKEY" and keys["api_secret"] == "ENCSEC"
        asyncio.run(check())


class TestApiKeysFrontend:
    def test_settings_has_apikey_form(self, client):
        app_ = client
        app_.app.state.auth_enabled = False
        r = client.get("/")
        for el in ['id="apikey-key"', 'id="apikey-secret"', 'id="apikey-passphrase"',
                   'id="apikey-sandbox"', 'id="apikey-save"', 'data-info="apikeys"']:
            assert el in r.text
        app_.app.state.auth_enabled = True

    def test_app_js_has_apikey_functions(self, client):
        client.app.state.auth_enabled = False
        js = client.get("/static/js/app.js").text
        assert "loadApiKeys" in js and "saveApiKeys" in js
        assert "/settings/api-keys" in js
        client.app.state.auth_enabled = True
