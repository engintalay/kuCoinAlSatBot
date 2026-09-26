"""
KuCoin Al-Sat Botu — Brute-force Koruması & Kilitleme (Faz 1 Task 4)

Aşamalı kilitleme:
  - MAX_ATTEMPTS (5) başarısız denemede → Stage 1: süreli kilit (STAGE1_LOCK_MINUTES).
  - Stage 1 kilidi bitince tekrar MAX_ATTEMPTS başarısız → Stage 2: hesap tamamen kapanır
    (is_disabled=1). Admin dahil.

Yerel-ağ istisnası (2b):
  - Sunucu ile aynı /24 alt ağdan gelen IP, kilit ve 2FA'yı atlar (yalnızca şifre yeterli).
"""

import ipaddress
from datetime import datetime, timedelta, timezone

from src.auth.user_store import UserStore
from src.utils.logger import logger

MAX_ATTEMPTS = 5            # kilit tetikleyen başarısız deneme sayısı
STAGE1_LOCK_MINUTES = 15    # 1. aşama kilit süresi


def is_local_network(request_ip: str | None, server_ip: str | None) -> bool:
    """
    request_ip ile server_ip aynı /24 alt ağda mı? (ör. 192.168.68.100 ↔ 192.168.68.xx)
    Loopback (127.0.0.1, ::1) her zaman yerel kabul edilir.
    """
    if not request_ip:
        return False
    try:
        req = ipaddress.ip_address(request_ip)
    except ValueError:
        return False
    if req.is_loopback:
        return True
    if not server_ip:
        return False
    try:
        srv = ipaddress.ip_address(server_ip)
    except ValueError:
        return False
    if req.version != srv.version or req.version != 4:
        # Sadece IPv4 /24 destekleniyor; farklı sürümde eşitlik ara
        return req == srv
    net = ipaddress.ip_network(f"{srv}/24", strict=False)
    return req in net


class LockoutService:
    """Aşamalı hesap kilitleme mantığı (UserStore üzerinde çalışır)."""

    def __init__(self, store: UserStore,
                 max_attempts: int = MAX_ATTEMPTS,
                 stage1_minutes: int = STAGE1_LOCK_MINUTES):
        self.store = store
        self.max_attempts = max_attempts
        self.stage1_minutes = stage1_minutes

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _parse(self, iso: str | None) -> datetime | None:
        if not iso:
            return None
        try:
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def is_locked(self, user: dict) -> bool:
        """Kullanıcı şu an kilitli mi? (Stage 2 kapalı veya Stage 1 süresi dolmamış)"""
        if not user:
            return False
        if user.get("is_disabled"):
            return True
        locked_until = self._parse(user.get("locked_until"))
        if locked_until and self._now() < locked_until:
            return True
        return False

    def lock_reason(self, user: dict) -> str | None:
        """Kilit sebebini insan-okunur döndürür (kilitli değilse None)."""
        if not user:
            return None
        if user.get("is_disabled"):
            return "Hesap kalıcı olarak kapatıldı (çok sayıda başarısız giriş). Admin ile iletişime geçin."
        locked_until = self._parse(user.get("locked_until"))
        if locked_until and self._now() < locked_until:
            return f"Hesap geçici olarak kilitli. Kilit bitişi: {user.get('locked_until')}"
        return None

    async def register_failed_attempt(self, user: dict) -> dict:
        """
        Başarısız girişi işler. Eşiğe ulaşınca aşamalı kilit uygular ve
        güncellenmiş kullanıcıyı döndürür. Kilit uygulanınca oturumlar düşürülür.
        """
        attempts = int(user.get("failed_attempts", 0)) + 1
        stage = int(user.get("lock_stage", 0))

        if attempts >= self.max_attempts:
            if stage == 0:
                # Stage 1: süreli kilit
                locked_until = (self._now() + timedelta(minutes=self.stage1_minutes)).isoformat()
                updated = await self.store.update_user_fields(
                    user["id"], failed_attempts=0, lock_stage=1, locked_until=locked_until)
                await self.store.delete_user_sessions(user["id"])
                logger.warning(f"🔒 Kullanıcı '{user['username']}' Stage 1 kilit ({self.stage1_minutes}dk).")
                return updated
            else:
                # Stage 2: kalıcı kapatma
                updated = await self.store.update_user_fields(
                    user["id"], failed_attempts=0, lock_stage=2, is_disabled=1, locked_until=None)
                await self.store.delete_user_sessions(user["id"])
                logger.warning(f"⛔ Kullanıcı '{user['username']}' Stage 2: hesap kalıcı kapatıldı.")
                return updated

        updated = await self.store.update_user_fields(user["id"], failed_attempts=attempts)
        return updated

    async def register_success(self, user: dict) -> dict:
        """Başarılı giriş: deneme sayacını ve süreli kilidi sıfırla (Stage 2 hariç)."""
        if user.get("is_disabled"):
            return user
        return await self.store.update_user_fields(
            user["id"], failed_attempts=0, locked_until=None,
            lock_stage=0 if user.get("lock_stage") == 1 else user.get("lock_stage", 0))
