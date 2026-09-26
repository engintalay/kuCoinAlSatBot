"""
KuCoin Al-Sat Botu — Kimlik Doğrulama Yöneticisi (Faz 1 Task 5)
Login/logout iş mantığını birleştirir: şifre + TOTP + kilit kontrolü +
yerel-ağ istisnası + sunucu tarafı oturum.
"""

from datetime import datetime, timedelta, timezone

from src.auth import auth_service
from src.auth.lockout import LockoutService, is_local_network
from src.auth.user_store import UserStore
from src.utils.logger import logger

SESSION_COOKIE = "kucoin_session"
SESSION_TTL_HOURS = 12


class AuthManager:
    """Kimlik doğrulama akışını yürütür."""

    def __init__(self, store: UserStore, server_ip: str | None = None):
        self.store = store
        self.lockout = LockoutService(store)
        self.server_ip = server_ip

    async def login(self, username: str, password: str, totp_code: str | None = None,
                    request_ip: str | None = None) -> dict:
        """
        Giriş dener. Başarılıysa {success, session_id, user} döndürür.
        Kurallar:
          - Yerel ağ (aynı /24) → kilit ve TOTP atlanır, yalnızca şifre.
          - Aksi halde: kilit kontrolü → şifre → (TOTP kayıtlıysa) TOTP zorunlu.
        """
        user = await self.store.get_user_by_username(username)
        local = is_local_network(request_ip, self.server_ip)

        # Kullanıcı yoksa: sabit mesaj (kullanıcı adı sızdırma yok)
        if not user:
            return {"success": False, "error": "Kullanıcı adı veya şifre hatalı."}

        # Kalıcı kapalı hesap yerel ağdan bile açılamaz
        if user.get("is_disabled"):
            return {"success": False, "error": self.lockout.lock_reason(user)}

        # Yerel ağ değilse kilit kontrolü
        if not local and self.lockout.is_locked(user):
            return {"success": False, "error": self.lockout.lock_reason(user)}

        # Şifre doğrulama (her durumda zorunlu)
        if not auth_service.verify_password(password, user["password_hash"]):
            updated = await self.lockout.register_failed_attempt(user)
            if not local and self.lockout.is_locked(updated):
                return {"success": False, "error": self.lockout.lock_reason(updated)}
            return {"success": False, "error": "Kullanıcı adı veya şifre hatalı."}

        # TOTP: yerel ağ değilse ve kullanıcının TOTP secret'ı varsa zorunlu
        if not local and user.get("totp_secret"):
            if not totp_code:
                return {"success": False, "error": "2FA kodu gerekli.", "totp_required": True}
            if not auth_service.verify_totp(user["totp_secret"], totp_code):
                await self.lockout.register_failed_attempt(user)
                return {"success": False, "error": "2FA kodu hatalı.", "totp_required": True}

        # Başarılı: sayaç sıfırla, oturum oluştur
        await self.lockout.register_success(user)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
        sid = await self.store.create_session(user["id"], expires_at=expires_at, ip=request_ip)
        logger.info(f"✅ Giriş başarılı: '{username}' (yerel_ağ={local})")
        return {"success": True, "session_id": sid,
                "user": {"id": user["id"], "username": user["username"], "role": user["role"]}}

    async def logout(self, session_id: str) -> None:
        if session_id:
            await self.store.delete_session(session_id)

    async def resolve_session(self, session_id: str | None) -> dict | None:
        """
        Session ID'den geçerli kullanıcıyı döndürür. Süresi dolmuş/geçersiz/kilitli
        oturumlarda None döner (ve süresi dolmuşsa oturumu siler).
        """
        if not session_id:
            return None
        sess = await self.store.get_session(session_id)
        if not sess:
            return None
        # Süre kontrolü
        try:
            exp = datetime.fromisoformat(sess["expires_at"])
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
        except (ValueError, KeyError):
            await self.store.delete_session(session_id)
            return None
        if datetime.now(timezone.utc) >= exp:
            await self.store.delete_session(session_id)
            return None
        user = await self.store.get_user_by_id(sess["user_id"])
        if not user or user.get("is_disabled"):
            await self.store.delete_session(session_id)
            return None
        return user
