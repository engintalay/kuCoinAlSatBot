"""
KuCoin Al-Sat Botu — Kullanıcı Veri Katmanı (Faz 1 Task 2)
users / sessions / user_api_keys tablolarını yönetir. API anahtarları
CryptoVault (master key) ile şifreli saklanır.
"""

import uuid
import aiosqlite

from src.auth.crypto_vault import CryptoVault
from src.utils.logger import logger
from src.utils.time_sync import timestamp


class UserStore:
    """Kullanıcı, oturum ve şifreli API anahtarı deposu."""

    def __init__(self, db_path: str = "auth.db", vault: CryptoVault | None = None):
        self.db_path = db_path
        self.vault = vault or CryptoVault()
        self._initialized = False

    async def init_db(self):
        """Tabloları oluştur."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',        -- 'admin' | 'user'
                    totp_secret TEXT,                          -- şifreli (vault)
                    email TEXT,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    lock_stage INTEGER NOT NULL DEFAULT 0,     -- 0=açık, 1=1. kilit, 2=tam kapalı
                    locked_until TEXT,                         -- ISO zaman; NULL=kilit yok
                    is_disabled INTEGER NOT NULL DEFAULT 0,    -- 1=tamamen kapalı
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,                       -- opak session token
                    user_id INTEGER NOT NULL,
                    ip TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    exchange TEXT NOT NULL DEFAULT 'kucoin',   -- kucoin | binance ...
                    enc_api_key TEXT,                          -- şifreli
                    enc_api_secret TEXT,                       -- şifreli
                    enc_api_passphrase TEXT,                   -- şifreli
                    is_sandbox INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, exchange),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            await db.commit()
        self._initialized = True

    async def _ensure(self):
        if not self._initialized:
            await self.init_db()

    # ------------------------------------------------------------------ #
    # Kullanıcı CRUD
    # ------------------------------------------------------------------ #
    async def create_user(self, username: str, password_hash: str, role: str = "user",
                          totp_secret: str | None = None, email: str | None = None) -> dict:
        await self._ensure()
        now = timestamp()
        enc_totp = self.vault.encrypt(totp_secret) if totp_secret else None
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """INSERT INTO users (username, password_hash, role, totp_secret, email,
                                      created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (username, password_hash, role, enc_totp, email, now, now),
            )
            await db.commit()
            user_id = cur.lastrowid
        return await self.get_user_by_id(user_id)

    async def get_user_by_username(self, username: str) -> dict | None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cur:
                row = await cur.fetchone()
        return self._row_to_user(row)

    async def get_user_by_id(self, user_id: int) -> dict | None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
        return self._row_to_user(row)

    def _row_to_user(self, row) -> dict | None:
        if not row:
            return None
        d = dict(row)
        # TOTP secret'ı çöz (varsa)
        if d.get("totp_secret"):
            try:
                d["totp_secret"] = self.vault.decrypt(d["totp_secret"])
            except ValueError:
                logger.error(f"Kullanıcı {d.get('username')} TOTP secret çözülemedi.")
                d["totp_secret"] = None
        return d

    async def count_users(self) -> int:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                row = await cur.fetchone()
        return row[0] if row else 0

    async def update_user_fields(self, user_id: int, **fields) -> dict | None:
        """Belirtilen alanları günceller (password_hash, role, failed_attempts,
        lock_stage, locked_until, is_disabled, email). totp_secret verilirse şifrelenir."""
        if not fields:
            return await self.get_user_by_id(user_id)
        await self._ensure()
        if "totp_secret" in fields and fields["totp_secret"] is not None:
            fields["totp_secret"] = self.vault.encrypt(fields["totp_secret"])
        allowed = {"password_hash", "role", "totp_secret", "email",
                   "failed_attempts", "lock_stage", "locked_until", "is_disabled"}
        sets, params = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return await self.get_user_by_id(user_id)
        sets.append("updated_at = ?")
        params.append(timestamp())
        params.append(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
            await db.commit()
        return await self.get_user_by_id(user_id)

    # ------------------------------------------------------------------ #
    # API anahtarları (şifreli)
    # ------------------------------------------------------------------ #
    async def save_api_keys(self, user_id: int, api_key: str, api_secret: str,
                            api_passphrase: str = "", exchange: str = "kucoin",
                            is_sandbox: bool = False) -> None:
        await self._ensure()
        now = timestamp()
        enc_k = self.vault.encrypt(api_key)
        enc_s = self.vault.encrypt(api_secret)
        enc_p = self.vault.encrypt(api_passphrase or "")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO user_api_keys (user_id, exchange, enc_api_key, enc_api_secret,
                                              enc_api_passphrase, is_sandbox, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, exchange) DO UPDATE SET
                       enc_api_key = excluded.enc_api_key,
                       enc_api_secret = excluded.enc_api_secret,
                       enc_api_passphrase = excluded.enc_api_passphrase,
                       is_sandbox = excluded.is_sandbox,
                       updated_at = excluded.updated_at""",
                (user_id, exchange, enc_k, enc_s, enc_p, 1 if is_sandbox else 0, now, now),
            )
            await db.commit()

    async def get_api_keys(self, user_id: int, exchange: str = "kucoin") -> dict | None:
        """Çözülmüş API anahtarlarını döndürür (yoksa None)."""
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_api_keys WHERE user_id = ? AND exchange = ?",
                (user_id, exchange),
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            return {
                "exchange": d["exchange"],
                "api_key": self.vault.decrypt(d["enc_api_key"]) if d["enc_api_key"] else "",
                "api_secret": self.vault.decrypt(d["enc_api_secret"]) if d["enc_api_secret"] else "",
                "api_passphrase": self.vault.decrypt(d["enc_api_passphrase"]) if d["enc_api_passphrase"] else "",
                "is_sandbox": bool(d["is_sandbox"]),
            }
        except ValueError as e:
            logger.error(f"API anahtarı çözme hatası (user={user_id}): {e}")
            return None

    # ------------------------------------------------------------------ #
    # Oturumlar
    # ------------------------------------------------------------------ #
    async def create_session(self, user_id: int, expires_at: str, ip: str | None = None) -> str:
        await self._ensure()
        sid = uuid.uuid4().hex + uuid.uuid4().hex  # 64 hex opak token
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sessions (id, user_id, ip, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (sid, user_id, ip, timestamp(), expires_at),
            )
            await db.commit()
        return sid

    async def get_session(self, session_id: str) -> dict | None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cur:
                row = await cur.fetchone()
        return dict(row) if row else None

    async def delete_session(self, session_id: str) -> None:
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()

    async def delete_user_sessions(self, user_id: int) -> None:
        """Bir kullanıcının tüm oturumlarını düşür (kilit/kapatma sonrası)."""
        await self._ensure()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            await db.commit()
