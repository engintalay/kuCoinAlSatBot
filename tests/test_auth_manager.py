"""
Faz 1 — AuthManager (login/logout/session çözümleme) testleri.
"""

import pytest
import pyotp

from src.auth.crypto_vault import CryptoVault
from src.auth.user_store import UserStore
from src.auth.auth_service import hash_password, generate_totp_secret
from src.auth.auth_manager import AuthManager


async def _setup(tmp_path, with_totp=False, server_ip="192.168.68.100"):
    store = UserStore(db_path=str(tmp_path / "am.db"),
                      vault=CryptoVault(master_key=CryptoVault.generate_key()))
    secret = generate_totp_secret() if with_totp else None
    await store.create_user("alice", hash_password("dogruSifre"), role="user", totp_secret=secret)
    mgr = AuthManager(store, server_ip=server_ip)
    return store, mgr, secret


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success_no_totp_remote(self, tmp_path):
        _, mgr, _ = await _setup(tmp_path)
        r = await mgr.login("alice", "dogruSifre", request_ip="8.8.8.8")
        assert r["success"] is True and r["session_id"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, tmp_path):
        _, mgr, _ = await _setup(tmp_path)
        r = await mgr.login("alice", "yanlis", request_ip="8.8.8.8")
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_unknown_user(self, tmp_path):
        _, mgr, _ = await _setup(tmp_path)
        r = await mgr.login("yok", "x", request_ip="8.8.8.8")
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_totp_required_and_verified(self, tmp_path):
        _, mgr, secret = await _setup(tmp_path, with_totp=True)
        # Uzak ağdan TOTP'siz → totp_required
        r1 = await mgr.login("alice", "dogruSifre", request_ip="8.8.8.8")
        assert r1["success"] is False and r1.get("totp_required")
        # Doğru TOTP ile → başarılı
        code = pyotp.TOTP(secret).now()
        r2 = await mgr.login("alice", "dogruSifre", totp_code=code, request_ip="8.8.8.8")
        assert r2["success"] is True

    @pytest.mark.asyncio
    async def test_local_network_skips_totp(self, tmp_path):
        """Yerel ağdan (aynı /24) TOTP olmadan sadece şifre yeterli."""
        _, mgr, _ = await _setup(tmp_path, with_totp=True, server_ip="192.168.68.100")
        r = await mgr.login("alice", "dogruSifre", request_ip="192.168.68.55")
        assert r["success"] is True

    @pytest.mark.asyncio
    async def test_local_network_still_needs_password(self, tmp_path):
        _, mgr, _ = await _setup(tmp_path, with_totp=True, server_ip="192.168.68.100")
        r = await mgr.login("alice", "yanlis", request_ip="192.168.68.55")
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_lockout_after_failures_remote(self, tmp_path):
        store, mgr, _ = await _setup(tmp_path)
        for _ in range(5):
            await mgr.login("alice", "yanlis", request_ip="8.8.8.8")
        # 5 başarısız sonrası doğru şifreyle bile uzak ağdan kilitli
        r = await mgr.login("alice", "dogruSifre", request_ip="8.8.8.8")
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_lockout_bypassed_on_local_network(self, tmp_path):
        """Uzaktan kilitlenmiş hesap, yerel ağdan doğru şifreyle girebilir."""
        store, mgr, _ = await _setup(tmp_path, server_ip="192.168.68.100")
        for _ in range(5):
            await mgr.login("alice", "yanlis", request_ip="8.8.8.8")
        r = await mgr.login("alice", "dogruSifre", request_ip="192.168.68.55")
        assert r["success"] is True


class TestSession:
    @pytest.mark.asyncio
    async def test_resolve_valid_session(self, tmp_path):
        _, mgr, _ = await _setup(tmp_path)
        r = await mgr.login("alice", "dogruSifre", request_ip="8.8.8.8")
        user = await mgr.resolve_session(r["session_id"])
        assert user["username"] == "alice"

    @pytest.mark.asyncio
    async def test_logout_invalidates(self, tmp_path):
        _, mgr, _ = await _setup(tmp_path)
        r = await mgr.login("alice", "dogruSifre", request_ip="8.8.8.8")
        await mgr.logout(r["session_id"])
        assert await mgr.resolve_session(r["session_id"]) is None

    @pytest.mark.asyncio
    async def test_resolve_none(self, tmp_path):
        _, mgr, _ = await _setup(tmp_path)
        assert await mgr.resolve_session(None) is None
        assert await mgr.resolve_session("gecersiz") is None
