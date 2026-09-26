"""
Faz 1 ek — Kullanıcı-yönetimli 2FA (setup/enable/disable/status) testleri.
"""

import asyncio
import pytest
import pyotp
from fastapi.testclient import TestClient

from src.auth import auth_service as A


class TestTotpQrHelper:
    def test_qr_data_uri_is_png(self):
        secret = A.generate_totp_secret()
        uri = A.totp_qr_data_uri(secret, "alice")
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 200


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from src.main import app, user_store
    from src.auth.auth_service import hash_password

    db = tmp_path_factory.mktemp("twofa")
    user_store.db_path = str(db / "auth.db")
    user_store._initialized = False
    app.state.auth_enabled = True

    async def seed():
        await user_store.init_db()
        # 2FA KAPALI kullanıcı (CLI davranışı)
        await user_store.create_user("u", hash_password("parola12345"), role="admin")
    asyncio.run(seed())
    return TestClient(app)


def _login(c):
    c.cookies.clear()
    c.post("/api/v1/auth/login", json={"username": "u", "password": "parola12345"})


class TestTwoFaEndpoints:
    def test_status_initially_disabled(self, client):
        _login(client)
        assert client.get("/api/v1/auth/2fa/status").json()["data"]["enabled"] is False

    def test_setup_returns_secret_and_qr(self, client):
        _login(client)
        d = client.post("/api/v1/auth/2fa/setup").json()["data"]
        assert d["secret"]
        assert d["qr_data_uri"].startswith("data:image/png;base64,")
        assert d["otpauth_uri"].startswith("otpauth://totp/")

    def test_enable_wrong_code_rejected(self, client):
        _login(client)
        s = client.post("/api/v1/auth/2fa/setup").json()["data"]["secret"]
        r = client.post("/api/v1/auth/2fa/enable", json={"secret": s, "code": "000000"})
        assert r.status_code == 400

    def test_enable_then_disable_flow(self, client):
        _login(client)
        s = client.post("/api/v1/auth/2fa/setup").json()["data"]["secret"]
        code = pyotp.TOTP(s).now()
        en = client.post("/api/v1/auth/2fa/enable", json={"secret": s, "code": code})
        assert en.status_code == 200 and en.json()["data"]["enabled"] is True
        assert client.get("/api/v1/auth/2fa/status").json()["data"]["enabled"] is True
        # şifre ile devre dışı bırak
        dis = client.post("/api/v1/auth/2fa/disable", json={"password": "parola12345"})
        assert dis.status_code == 200 and dis.json()["data"]["enabled"] is False
        assert client.get("/api/v1/auth/2fa/status").json()["data"]["enabled"] is False

    def test_disable_with_totp_code(self, client):
        _login(client)
        s = client.post("/api/v1/auth/2fa/setup").json()["data"]["secret"]
        client.post("/api/v1/auth/2fa/enable", json={"secret": s, "code": pyotp.TOTP(s).now()})
        # yanlış kod/şifre reddedilir
        bad = client.post("/api/v1/auth/2fa/disable", json={"password": "yanlis"})
        assert bad.status_code == 400
        # doğru TOTP kodu ile kapat
        ok = client.post("/api/v1/auth/2fa/disable", json={"code": pyotp.TOTP(s).now()})
        assert ok.status_code == 200

    def test_2fa_requires_auth(self, client):
        client.cookies.clear()
        assert client.post("/api/v1/auth/2fa/setup").status_code == 401
        assert client.get("/api/v1/auth/2fa/status").status_code == 401


class TestCliNoTotpByDefault:
    @pytest.mark.asyncio
    async def test_cli_admin_has_no_totp(self, tmp_path, monkeypatch):
        from src.auth.user_store import UserStore
        from src.auth.crypto_vault import CryptoVault
        from src.auth import cli
        monkeypatch.setattr(cli.Config, "API_KEY", None, raising=False)
        s = UserStore(db_path=str(tmp_path / "c.db"), vault=CryptoVault(master_key=CryptoVault.generate_key()))
        r = await cli.create_admin(s, "admin", "parola12345", migrate_env_keys=False)
        assert r["totp_secret"] is None  # 2FA varsayılan kapalı


class TestTwoFaFrontend:
    def test_settings_has_2fa_card(self, client):
        client.app.state.auth_enabled = False
        r = client.get("/")
        for el in ['id="twofa-status"', 'id="twofa-setup-btn"', 'id="twofa-qr-img"',
                   'id="twofa-enable-btn"', 'id="twofa-disable-btn"', 'data-info="twofa"']:
            assert el in r.text
        client.app.state.auth_enabled = True

    def test_app_js_has_2fa_functions(self, client):
        client.app.state.auth_enabled = False
        js = client.get("/static/js/app.js").text
        assert "setup2FA" in js and "enable2FA" in js and "disable2FA" in js
        client.app.state.auth_enabled = True
