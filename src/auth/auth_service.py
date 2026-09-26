"""
KuCoin Al-Sat Botu — Kimlik Doğrulama Servisi (Faz 1 Task 3)
Şifre hash/doğrulama (bcrypt via passlib) ve TOTP 2FA (pyotp).
"""

import pyotp
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Uygulama adı — authenticator uygulamasında görünen etiket
TOTP_ISSUER = "KuCoinAlSatBot"


def hash_password(password: str) -> str:
    """Düz şifreyi bcrypt ile hash'ler."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Şifreyi hash ile karşılaştırır."""
    try:
        return _pwd_context.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def generate_totp_secret() -> str:
    """Yeni bir base32 TOTP secret üretir."""
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, username: str) -> str:
    """
    Authenticator uygulamasına eklenmek üzere otpauth:// URI'si üretir
    (QR koda dönüştürülebilir).
    """
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=TOTP_ISSUER)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    """
    TOTP kodunu doğrular. valid_window=1 → saat kaymasına karşı ±30sn tolerans.
    """
    if not secret or not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(str(code).strip(), valid_window=valid_window)
    except Exception:
        return False


def totp_qr_data_uri(secret: str, username: str) -> str:
    """
    TOTP provisioning URI'sini QR koda çevirip base64 PNG data-URI döndürür.
    Authenticator uygulamasıyla taranabilir: <img src="{data_uri}">.
    """
    import base64
    import io
    import qrcode

    uri = totp_provisioning_uri(secret, username)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
