"""
KuCoin Al-Sat Botu — Ayarlar & Çoklu Coin (Watchlist) Yönetimi
MODULE_3_SPEC 2.8. Ayarları SQLite'ta kalıcı saklar; watchlist, varsayılan mod
ve risk parametrelerini yönetir.
"""

import json
import aiosqlite

from src.config import Config
from src.utils.logger import logger
from src.utils.time_sync import timestamp

DEFAULT_SETTINGS = {
    "watchlist": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    "default_mode": "paper",          # paper | live
    "default_symbol": "BTC/USDT",
    "default_timeframe": "1h",
    "risk": {
        "max_order_usdt": 1000.0,     # tek emirde maksimum tutar
        "default_stop_loss_pct": 2.0, # %
        "default_take_profit_pct": 4.0,
    },
}


class SettingsManager:
    """Ayarların SQLite kalıcılığı ve watchlist yönetimi."""

    def __init__(self, db_path: str = "bot_settings.db", market=None):
        self.db_path = db_path
        self.market = market
        self._settings: dict | None = None  # bellek önbelleği

    async def _ensure_table(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    data TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            await db.commit()

    async def load(self) -> dict:
        """Ayarları yükle; yoksa varsayılanı oluştur."""
        await self._ensure_table()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT data FROM settings WHERE id = 1") as cur:
                row = await cur.fetchone()
        if row:
            self._settings = json.loads(row[0])
        else:
            self._settings = json.loads(json.dumps(DEFAULT_SETTINGS))  # kopya
            await self.save(self._settings)
        return self._settings

    async def save(self, settings: dict) -> dict:
        """Ayarları doğrula, mevcut ayarların ÜZERİNE birleştir ve kalıcı kaydet.

        Kısmi güncelleme (ör. yalnızca default_mode) gönderildiğinde diğer
        alanların (watchlist, default_symbol vb.) sıfırlanmaması için önce
        diskteki mevcut ayar tabanı okunur.
        """
        await self._ensure_table()
        # Taban: DEFAULT üstüne diskteki mevcut ayarlar (kayıp önleme)
        merged = json.loads(json.dumps(DEFAULT_SETTINGS))
        current = await self._read_raw()
        if current:
            merged.update({k: v for k, v in current.items() if k in DEFAULT_SETTINGS})
        # Gelen kısmi güncellemeyi uygula
        for k, v in settings.items():
            if k not in DEFAULT_SETTINGS:
                continue
            # risk gibi iç içe dict'leri derin birleştir
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                nested = dict(merged[k])
                nested.update(v)
                merged[k] = nested
            else:
                merged[k] = v
        # mod doğrulaması
        if merged.get("default_mode") not in ("paper", "live"):
            merged["default_mode"] = "paper"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO settings (id, data, updated_at) VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
                (json.dumps(merged), timestamp()),
            )
            await db.commit()
        self._settings = merged
        return merged

    async def _read_raw(self) -> dict | None:
        """Diskteki ham ayar sözlüğünü okur (yoksa None)."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT data FROM settings WHERE id = 1") as cur:
                row = await cur.fetchone()
        return json.loads(row[0]) if row else None

    async def get_settings(self) -> dict:
        s = self._settings if self._settings is not None else await self.load()
        return {"success": True, "data": s, "error": None, "timestamp": timestamp()}

    async def update_settings(self, settings: dict) -> dict:
        try:
            merged = await self.save(settings)
            return {"success": True, "data": merged, "error": None, "timestamp": timestamp()}
        except Exception as e:
            logger.error(f"Ayar kaydetme hatası: {e}")
            return {"success": False, "data": {}, "error": f"Ayarlar kaydedilemedi: {e}",
                    "timestamp": timestamp()}

    async def add_to_watchlist(self, symbol: str) -> dict:
        s = await self.load()
        if symbol not in s["watchlist"]:
            s["watchlist"].append(symbol)
            await self.save(s)
        return {"success": True, "data": {"watchlist": s["watchlist"]}, "error": None,
                "timestamp": timestamp()}

    async def remove_from_watchlist(self, symbol: str) -> dict:
        s = await self.load()
        if symbol in s["watchlist"]:
            s["watchlist"].remove(symbol)
            await self.save(s)
        return {"success": True, "data": {"watchlist": s["watchlist"]}, "error": None,
                "timestamp": timestamp()}

    async def search_symbols(self, query: str = "", quote: str = "USDT") -> dict:
        """KuCoin sembollerini ara (Modül 2 market üzerinden)."""
        try:
            if self.market is None:
                return {"success": False, "data": {}, "error": "Market modülü yok",
                        "timestamp": timestamp()}
            res = await self.market.get_symbols(quote)
            if not res.success:
                return {"success": False, "data": {}, "error": res.error, "timestamp": timestamp()}
            symbols = res.data["symbols"]
            if query:
                q = query.upper()
                symbols = [s for s in symbols if q in s.upper()]
            return {"success": True, "data": {"count": len(symbols), "symbols": symbols[:50]},
                    "error": None, "timestamp": timestamp()}
        except Exception as e:
            logger.error(f"Sembol arama hatası: {e}")
            return {"success": False, "data": {}, "error": str(e), "timestamp": timestamp()}
