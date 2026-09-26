"""
Faz 1 — Admin CLI iş mantığı (create_admin/reset_password/migrate_env) testleri.
"""

import pytest

from src.auth.crypto_vault import CryptoVault
from src.auth.user_store import UserStore
from src.auth import auth_service
from src.auth import cli


def _store(tmp_path):
    return UserStore(db_path=str(tmp_path / "cli.db"),
                     vault=CryptoVault(master_key=CryptoVault.generate_key()))


class TestCreateAdmin:
    @pytest.mark.asyncio
    async def test_creates_admin_with_totp(self, tmp_path, monkeypatch):
        # .env anahtarı yok say
        monkeypatch.setattr(cli.Config, "API_KEY", None, raising=False)
        s = _store(tmp_path)
        # 2FA varsayılan kapalı; açıkça with_totp=True istenirse secret üretilir
        r = await cli.create_admin(s, "admin", "parola123", with_totp=True, migrate_env_keys=False)
        assert r["user"]["role"] == "admin"
        assert r["totp_secret"] and r["provisioning_uri"].startswith("otpauth://")
        # şifre doğrulanabilir
        u = await s.get_user_by_username("admin")
        assert auth_service.verify_password("parola123", u["password_hash"])

    @pytest.mark.asyncio
    async def test_creates_admin_2fa_disabled_by_default(self, tmp_path, monkeypatch):
        """Varsayılan: CLI ile oluşturulan admin'de 2FA KAPALI (totp_secret None)."""
        monkeypatch.setattr(cli.Config, "API_KEY", None, raising=False)
        s = _store(tmp_path)
        r = await cli.create_admin(s, "admin2", "parola123", migrate_env_keys=False)
        assert r["totp_secret"] is None
        assert r["provisioning_uri"] is None

    @pytest.mark.asyncio
    async def test_duplicate_admin_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli.Config, "API_KEY", None, raising=False)
        s = _store(tmp_path)
        await cli.create_admin(s, "admin", "parola123", migrate_env_keys=False)
        with pytest.raises(ValueError):
            await cli.create_admin(s, "admin", "baska123", migrate_env_keys=False)

    @pytest.mark.asyncio
    async def test_migrates_env_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli.Config, "API_KEY", "ENVKEY", raising=False)
        monkeypatch.setattr(cli.Config, "API_SECRET", "ENVSEC", raising=False)
        monkeypatch.setattr(cli.Config, "API_PASSPHRASE", "ENVPASS", raising=False)
        monkeypatch.setattr(cli.Config, "IS_SANDBOX", False, raising=False)
        s = _store(tmp_path)
        r = await cli.create_admin(s, "admin", "parola123", migrate_env_keys=True)
        assert r["migrated"] is True
        keys = await s.get_api_keys(r["user"]["id"], "kucoin")
        assert keys["api_key"] == "ENVKEY" and keys["api_secret"] == "ENVSEC"


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_reset_clears_locks(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("admin", auth_service.hash_password("eski123"), role="admin")
        # hesabı kilitle
        await s.update_user_fields(u["id"], failed_attempts=5, lock_stage=1,
                                   locked_until="2099-01-01T00:00:00Z", is_disabled=1)
        await cli.reset_password(s, "admin", "yeni12345")
        got = await s.get_user_by_username("admin")
        assert got["is_disabled"] == 0 and got["lock_stage"] == 0
        assert got["locked_until"] is None
        assert auth_service.verify_password("yeni12345", got["password_hash"])

    @pytest.mark.asyncio
    async def test_reset_unknown_user(self, tmp_path):
        s = _store(tmp_path)
        with pytest.raises(ValueError):
            await cli.reset_password(s, "yok", "yeni12345")


class TestMigrateEnv:
    @pytest.mark.asyncio
    async def test_migrate_to_existing_user(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli.Config, "API_KEY", "K", raising=False)
        monkeypatch.setattr(cli.Config, "API_SECRET", "S", raising=False)
        monkeypatch.setattr(cli.Config, "API_PASSPHRASE", "P", raising=False)
        monkeypatch.setattr(cli.Config, "IS_SANDBOX", False, raising=False)
        s = _store(tmp_path)
        u = await s.create_user("u", auth_service.hash_password("x"))
        ok = await cli.migrate_env_keys(s, "u")
        assert ok is True
        assert (await s.get_api_keys(u["id"]))["api_key"] == "K"

    @pytest.mark.asyncio
    async def test_migrate_no_env_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli.Config, "API_KEY", None, raising=False)
        monkeypatch.setattr(cli.Config, "API_SECRET", None, raising=False)
        s = _store(tmp_path)
        await s.create_user("u", auth_service.hash_password("x"))
        assert await cli.migrate_env_keys(s, "u") is False
