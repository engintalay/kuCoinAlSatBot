"""
Faz 1 — Brute-force kilitleme & yerel-ağ istisnası testleri.
"""

import pytest

from src.auth.crypto_vault import CryptoVault
from src.auth.user_store import UserStore
from src.auth.lockout import LockoutService, is_local_network


def _store(tmp_path):
    return UserStore(db_path=str(tmp_path / "lock.db"),
                     vault=CryptoVault(master_key=CryptoVault.generate_key()))


class TestLocalNetwork:
    def test_same_24_subnet(self):
        assert is_local_network("192.168.68.55", "192.168.68.100") is True

    def test_different_subnet(self):
        assert is_local_network("10.0.0.5", "192.168.68.100") is False

    def test_loopback_always_local(self):
        assert is_local_network("127.0.0.1", None) is True

    def test_invalid_ip(self):
        assert is_local_network("not-an-ip", "192.168.68.100") is False

    def test_none_request_ip(self):
        assert is_local_network(None, "192.168.68.100") is False


class TestLockout:
    @pytest.mark.asyncio
    async def test_stage1_lock_after_max_attempts(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("u", "h")
        svc = LockoutService(s, max_attempts=5)
        # 4 başarısız → henüz kilit yok
        for _ in range(4):
            u = await svc.register_failed_attempt(u)
        assert u["lock_stage"] == 0 and not svc.is_locked(u)
        # 5. başarısız → Stage 1 kilit
        u = await svc.register_failed_attempt(u)
        assert u["lock_stage"] == 1
        assert svc.is_locked(u) is True
        assert u["failed_attempts"] == 0  # sayaç sıfırlandı

    @pytest.mark.asyncio
    async def test_stage2_permanent_disable(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("u2", "h")
        svc = LockoutService(s, max_attempts=3)
        # Stage 1
        for _ in range(3):
            u = await svc.register_failed_attempt(u)
        assert u["lock_stage"] == 1
        # Stage 1'deyken tekrar 3 başarısız → Stage 2 kalıcı kapatma
        for _ in range(3):
            u = await svc.register_failed_attempt(u)
        assert u["lock_stage"] == 2
        assert u["is_disabled"] == 1
        assert svc.is_locked(u) is True
        assert "kalıcı" in svc.lock_reason(u).lower()

    @pytest.mark.asyncio
    async def test_success_resets_attempts(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("u3", "h")
        svc = LockoutService(s, max_attempts=5)
        u = await svc.register_failed_attempt(u)
        u = await svc.register_failed_attempt(u)
        assert u["failed_attempts"] == 2
        u = await svc.register_success(u)
        assert u["failed_attempts"] == 0

    @pytest.mark.asyncio
    async def test_disabled_user_stays_locked_after_success_attempt(self, tmp_path):
        s = _store(tmp_path)
        u = await s.create_user("u4", "h")
        await s.update_user_fields(u["id"], is_disabled=1, lock_stage=2)
        u = await s.get_user_by_id(u["id"])
        svc = LockoutService(s)
        assert svc.is_locked(u) is True
