"""
KuCoin Al-Sat Botu — Veritabanı Modülü
SQLite bağlantı ve temel tablo yapıları.
"""

import aiosqlite
import os


class Database:
    """SQLite veritabanı bağlantısı ve işlemleri."""

    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self.database: aiosqlite.Connection | None = None

    async def connect(self):
        """Veritabanına bağlan."""
        self.database = await aiosqlite.connect(self.db_path)
        self.database.row_factory = aiosqlite.Row
        await self.database.execute("PRAGMA journal_mode=WAL")
        await self.database.commit()
        print(f"✅ Veritabanı bağlantısı kuruldu: {self.db_path}")

    async def create_tables(self):
        """Temel tablo yapılarını oluştur."""
        if not self.database:
            await self.connect()

        async with self.database:
            # Emir geçmişi tablosu
            await self.database.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    price REAL,
                    amount REAL,
                    filled_price REAL,
                    filled_amount REAL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    filled_at TIMESTAMP
                )
            """)

            # Bakiye geçmişi tablosu
            await self.database.execute("""
                CREATE TABLE IF NOT EXISTS balance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    free_amount REAL,
                    used_amount REAL,
                    total_amount REAL,
                    usdt_value REAL,
                    snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await self.database.commit()
            print("✅ Tablolar oluşturuldu")

    async def close(self):
        """Veritabanı bağlantısını kapat."""
        if self.database:
            await self.database.close()
            print("✅ Veritabanı bağlantısı kapatıldı")
