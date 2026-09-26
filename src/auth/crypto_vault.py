"""
KuCoin Al-Sat Botu — Kripto Kasa (Crypto Vault)
Master key ile simetrik şifreleme (Fernet). Borsa API anahtarları gibi
hassas verileri kullanıcı şifresinden bağımsız olarak şifreler/çözer.

Master key kaynağı (öncelik sırası):
1. Ortam değişkeni  MASTER_KEY  (.env'de tutulabilir — genel sistem ayarı)
2. Dosya            .master_key (kök dizinde; yoksa otomatik üretilir)

MASTER_KEY, urlsafe base64 kodlu 32 baytlık bir Fernet anahtarı olmalıdır.
"""

import os

from cryptography.fernet import Fernet, InvalidToken

from src.utils.logger import logger

MASTER_KEY_FILE = ".master_key"


class CryptoVault:
    """Master key tabanlı simetrik şifreleme kasası."""

    def __init__(self, master_key: str | bytes | None = None):
        self._fernet = Fernet(self._resolve_key(master_key))

    @staticmethod
    def generate_key() -> str:
        """Yeni bir Fernet master key üretir (urlsafe base64, str)."""
        return Fernet.generate_key().decode("utf-8")

    def _resolve_key(self, explicit: str | bytes | None) -> bytes:
        """Master key'i belirle: explicit > MASTER_KEY env > .master_key dosyası > üret."""
        # 1) Doğrudan verilen
        if explicit:
            return explicit.encode() if isinstance(explicit, str) else explicit
        # 2) Ortam değişkeni
        env_key = os.getenv("MASTER_KEY")
        if env_key:
            return env_key.encode()
        # 3) Dosya
        if os.path.exists(MASTER_KEY_FILE):
            with open(MASTER_KEY_FILE, "rb") as f:
                data = f.read().strip()
            if data:
                return data
        # 4) Üret ve dosyaya yaz (yalnızca sahip okuyabilsin)
        key = Fernet.generate_key()
        with open(MASTER_KEY_FILE, "wb") as f:
            f.write(key)
        try:
            os.chmod(MASTER_KEY_FILE, 0o600)
        except OSError:
            pass
        logger.warning(
            f"MASTER_KEY bulunamadı; yeni anahtar üretildi ve '{MASTER_KEY_FILE}' dosyasına yazıldı. "
            "Bu dosyayı güvenle saklayın; kaybı şifreli verilerin çözülememesine yol açar."
        )
        return key

    def encrypt(self, plaintext: str) -> str:
        """Düz metni şifreler, base64 token (str) döndürür."""
        if plaintext is None:
            plaintext = ""
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, token: str) -> str:
        """Şifreli token'ı çözer. Geçersiz/bozuk token'da ValueError fırlatır."""
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError, TypeError) as e:
            raise ValueError(f"Şifre çözme başarısız (geçersiz token veya yanlış master key): {e}")
