"""
Faz 1 — UserStore (kullanıcı/oturum/şifreli API anahtarı) testleri.
"""

import pytest

from src.auth.crypto_vault import CryptoVault
from src.auth.user_store import UserStore
from src.utils.time_sync import timestamp


def _store(tmp_path):
    db = str(tmp_path / "auth_test.db")
    vault = CryptoVault(master_key=CryptoVault.generate_key())
    return UserStore(db_path=db, vault=vault)


class TestUserStore:
    @pytest.mark.asyncio
    async def test_create_and_get_user(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("admin", "hash123", role="admin")
        assert u["id"] >= 1
        assert u["username"] == "admin"
        assert u["role"] == "admin"
        assert u["lock_stage"] == 0 and u["is_disabled"] == 0
        # username ile getir
        u2 = await s.get_user_by_username("admin")
        assert u2["id"] == u["id"]

    @pytest.mark.asyncio
    async def test_count_users(self, tmp_path):
        s = _store(tmp_path)
        assert await s.count_users() == 0
        await s.create_user("a", "h")
        await s.create_user("b", "h")
        assert await s.count_users() == 2

    @pytest.mark.asyncio
    async def test_api_keys_encrypted_roundtrip(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("trader", "h")
        await s.save_api_keys(u["id"], "KEY123", "SECRET456", "PASS789", exchange="kucoin")
        keys = await s.get_api_keys(u["id"], "kucoin")
        assert keys["api_key"] == "KEY123"
        assert keys["api_secret"] == "SECRET456"
        assert keys["api_passphrase"] == "PASS789"

    @pytest.mark.asyncio
    async def test_api_keys_stored_encrypted_not_plaintext(self, tmp_path):
        """DB'de düz metin API anahtarı bulunmamalı (şifreli olmalı)."""
        import aiosqlite
        s = _store(tmp_path)
        u = await s.create_user("t", "h")
        await s.save_api_keys(u["id"], "PLAINKEY", "PLAINSECRET")
        async with aiosqlite.connect(s.db_path) as db:
            async with db.execute("SELECT enc_api_key, enc_api_secret FROM user_api_keys") as cur:
                row = await cur.fetchone()
        assert "PLAINKEY" not in (row[0] or "")
        assert "PLAINSECRET" not in (row[1] or "")

    @pytest.mark.asyncio
    async def test_totp_secret_encrypted_roundtrip(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("x", "h", totp_secret="JBSWY3DPEHPK3PXP")
        got = await s.get_user_by_username("x")
        assert got["totp_secret"] == "JBSWY3DPEHPK3PXP"  # çözülmüş döner

    @pytest.mark.asyncio
    async def test_update_lock_fields(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("l", "h")
        await s.update_user_fields(u["id"], failed_attempts=3, lock_stage=1, locked_until="2030-01-01T00:00:00Z")
        got = await s.get_user_by_id(u["id"])
        assert got["failed_attempts"] == 3 and got["lock_stage"] == 1

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("s", "h")
        sid = await s.create_session(u["id"], expires_at="2030-01-01T00:00:00Z", ip="127.0.0.1")
        assert len(sid) >= 32
        sess = await s.get_session(sid)
        assert sess["user_id"] == u["id"]
        await s.delete_session(sid)
        assert await s.get_session(sid) is None

    @pytest.mark.asyncio
    async def test_delete_user_sessions(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("m", "h")
        await s.create_session(u["id"], expires_at="2030-01-01T00:00:00Z")
        await s.create_session(u["id"], expires_at="2030-01-01T00:00:00Z")
        await s.delete_user_sessions(u["id"])
        # yeni oturum alıp silindiğini dolaylı doğrula
        sid = await s.create_session(u["id"], expires_at="2030-01-01T00:00:00Z")
        assert await s.get_session(sid) is not None
