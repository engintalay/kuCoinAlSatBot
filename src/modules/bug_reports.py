"""
KuCoin Al-Sat Botu — Hata Raporlama ve Sorun Takip Motoru
Veritabanı üzerinde hata bildirimleri, teşhis logları ve durum takibini yönetir.
"""

import aiosqlite
import contextlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import platform
import sys


DEFAULT_BUG_1 = {
    "title": "Analiz ekranında coin seçim combo'sunda sadece BTC var",
    "category": "analysis",
    "severity": "high",
    "status": "resolved",
    "description": "Analiz ekranında sembol seçimi için bulunan combo açılır kutusunda yalnızca BTC/USDT seçeneği görünüyordu. İzleme listesindeki diğer koinler (ETH, SOL vb.) ve KuCoin'in popüler işlem çiftleri listede yer almıyordu.",
    "steps_to_reproduce": "1. Analiz sekmesine geçin.\n2. Sembol combo kutusuna tıklayın.\n3. Açılan listede yalnızca 'BTC/USDT' olduğunu ve diğer koinlerin listelenmediğini görün.",
    "expected_behavior": "Kullanıcı combo kutusuna tıkladığında hem izleme listesindeki tüm koinleri (BTC, ETH, SOL vb.) hem de popüler KuCoin çiftlerini görebilmeli, tek tıkla seçebilmeli ve özel sembol yazabilmelidir.",
    "actual_behavior": "HTML5 datalist filtreleme davranışı nedeniyle varsayılan 'BTC/USDT' değeri varken liste diğer seçenekleri gizliyordu ve popüler koinler entegre edilmemişti.",
    "system_info": f"Platform: {platform.system()} {platform.release()}, Python: {sys.version.split()[0]}, Modül: Analiz Ekranı",
    "resolution_note": "Analiz ekranındaki koin seçimi, hem kullanıcının İzleme Listesi'ni (Watchlist) hem de KuCoin popüler koinlerini (ETH, SOL, XRP, DOGE, BNB, SUI, AVAX, PEPE vb.) gruplu olarak listeleyen gerçek bir açılır kutu (<select>) mimarisine kavuşturuldu. Ayrıca tek tıkla analiz başlatan hızlı koin çipleri ve özel koin girme desteği eklendi.",
}

DEFAULT_BUG_2 = {
    "title": "Ayarlardan canlı (live) moda geçiş olmuyor",
    "category": "settings",
    "severity": "critical",
    "status": "resolved",
    "description": "Ayarlar sekmesinde 'Varsayılan Mod' olarak '⚡ LIVE KUCOIN' seçilip 'Kaydet' yapıldığında sistem canlı moda geçmiyordu; başlık çubuğundaki rozet '🧪 SIMULATION' kalmaya ve emir motoru modu paper olarak işlemeye devam ediyordu.",
    "steps_to_reproduce": "1. Ayarlar sekmesine gidin.\n2. 'Varsayılan Mod' açılır kutusundan '⚡ LIVE KUCOIN' seçin.\n3. 'Kaydet' butonuna tıklayın.\n4. Başlıktaki rozetin ve emir motorunun değişmediğini görün.",
    "expected_behavior": "Ayarlar'da 'LIVE' seçilip kaydedildiğinde; 1. Backend orders.mode 'live' olmalı, 2. SQLite veritabanında kalıcı olarak saklanmalı, 3. Başlık çubuğundaki mod rozeti derhal yeşil '⚡ LIVE KUCOIN' olmalı, 4. Başlıktaki rozete tıklandığında da kolayca mod geçişi yapılabilmelidir.",
    "actual_behavior": "POST /settings endpoint'i yalnızca SQLite ayar tablosunu güncelliyor fakat emir motorunun (orders.switch_mode) çalışma modunu güncellemiyordu. Ayrıca startup_event kaydedilen modu yüklemiyor ve arayüzdeki başlık rozeti güncellenmiyordu.",
    "system_info": f"Platform: {platform.system()} {platform.release()}, Python: {sys.version.split()[0]}, Modül: Ayarlar & Emir Motoru",
    "resolution_note": "1. POST /settings endpoint'ine default_mode parametresi geldiğinde orders.switch_mode senkronizasyonu eklendi. 2. Uygulama açılışında (startup_event) kaydedilmiş default_mode otomatik yüklenerek emir motoruna uygulandı. 3. GET /orders/mode uç noktası eklendi. 4. Frontend'de ayar kaydı sonrası anında mod geçişi sağlandı ve başlık rozeti (#mode-badge) tıklanabilir interaktif hızlı geçiş düğmesine dönüştürüldü.",
}


class BugTracker:
    """Hata raporlama ve sorun takip yöneticisi."""

    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._initialized = False

    @contextlib.asynccontextmanager
    async def _get_connection(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA journal_mode=WAL")
            yield db

    async def _ensure_init(self):
        if not self._initialized:
            await self.init_db()

    async def init_db(self):
        """Tabloyu oluştur ve ilk hata kaydını (Hata #1) tohumla."""
        self._initialized = True
        async with self._get_connection() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bug_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT NOT NULL,
                    steps_to_reproduce TEXT,
                    expected_behavior TEXT,
                    actual_behavior TEXT,
                    system_info TEXT,
                    resolution_note TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.commit()

            # Hata #1 tohumlama kontrolü
            cursor = await db.execute("SELECT COUNT(*) as cnt FROM bug_reports WHERE id = 1")
            row = await cursor.fetchone()
            if row and row["cnt"] == 0:
                now_str = datetime.now(timezone.utc).isoformat()
                await db.execute("""
                    INSERT INTO bug_reports (
                        id, title, category, severity, status, description,
                        steps_to_reproduce, expected_behavior, actual_behavior,
                        system_info, resolution_note, created_at, updated_at
                    ) VALUES (
                        1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    DEFAULT_BUG_1["title"],
                    DEFAULT_BUG_1["category"],
                    DEFAULT_BUG_1["severity"],
                    DEFAULT_BUG_1["status"],
                    DEFAULT_BUG_1["description"],
                    DEFAULT_BUG_1["steps_to_reproduce"],
                    DEFAULT_BUG_1["expected_behavior"],
                    DEFAULT_BUG_1["actual_behavior"],
                    DEFAULT_BUG_1["system_info"],
                    DEFAULT_BUG_1["resolution_note"],
                    now_str,
                    now_str
                ))
                await db.commit()

            # Hata #2 tohumlama kontrolü
            cursor2 = await db.execute("SELECT COUNT(*) as cnt FROM bug_reports WHERE id = 2")
            row2 = await cursor2.fetchone()
            if row2 and row2["cnt"] == 0:
                now_str = datetime.now(timezone.utc).isoformat()
                await db.execute("""
                    INSERT INTO bug_reports (
                        id, title, category, severity, status, description,
                        steps_to_reproduce, expected_behavior, actual_behavior,
                        system_info, resolution_note, created_at, updated_at
                    ) VALUES (
                        2, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    DEFAULT_BUG_2["title"],
                    DEFAULT_BUG_2["category"],
                    DEFAULT_BUG_2["severity"],
                    DEFAULT_BUG_2["status"],
                    DEFAULT_BUG_2["description"],
                    DEFAULT_BUG_2["steps_to_reproduce"],
                    DEFAULT_BUG_2["expected_behavior"],
                    DEFAULT_BUG_2["actual_behavior"],
                    DEFAULT_BUG_2["system_info"],
                    DEFAULT_BUG_2["resolution_note"],
                    now_str,
                    now_str
                ))
                await db.commit()

    async def create_issue(
        self,
        title: str,
        category: str,
        severity: str,
        description: str,
        steps_to_reproduce: Optional[str] = None,
        expected_behavior: Optional[str] = None,
        actual_behavior: Optional[str] = None,
        system_info: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Yeni bir hata bildirimi oluştur."""
        await self._ensure_init()
        now_str = datetime.now(timezone.utc).isoformat()
        status = "open"

        async with self._get_connection() as db:
            cursor = await db.execute("""
                INSERT INTO bug_reports (
                    title, category, severity, status, description,
                    steps_to_reproduce, expected_behavior, actual_behavior,
                    system_info, resolution_note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """, (
                title, category, severity, status, description,
                steps_to_reproduce, expected_behavior, actual_behavior,
                system_info, now_str, now_str
            ))
            await db.commit()
            new_id = cursor.lastrowid

        return await self.get_issue(new_id)

    async def list_issues(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Kayıtlı hataları listele."""
        await self._ensure_init()
        query = "SELECT * FROM bug_reports WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY id DESC"

        async with self._get_connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_issue(self, issue_id: int) -> Optional[Dict[str, Any]]:
        """Tek bir hata kaydını getir."""
        await self._ensure_init()
        async with self._get_connection() as db:
            cursor = await db.execute("SELECT * FROM bug_reports WHERE id = ?", (issue_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def update_issue(
        self,
        issue_id: int,
        status: Optional[str] = None,
        resolution_note: Optional[str] = None,
        severity: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Hata durumunu veya çözüm notunu güncelle."""
        await self._ensure_init()
        existing = await self.get_issue(issue_id)
        if not existing:
            return None

        now_str = datetime.now(timezone.utc).isoformat()
        fields = []
        params = []

        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if resolution_note is not None:
            fields.append("resolution_note = ?")
            params.append(resolution_note)
        if severity is not None:
            fields.append("severity = ?")
            params.append(severity)
        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if description is not None:
            fields.append("description = ?")
            params.append(description)

        if not fields:
            return existing

        fields.append("updated_at = ?")
        params.append(now_str)
        params.append(issue_id)

        query = f"UPDATE bug_reports SET {', '.join(fields)} WHERE id = ?"
        async with self._get_connection() as db:
            await db.execute(query, params)
            await db.commit()

        return await self.get_issue(issue_id)

    async def delete_issue(self, issue_id: int) -> bool:
        """Hata kaydını sil."""
        await self._ensure_init()
        async with self._get_connection() as db:
            cursor = await db.execute("DELETE FROM bug_reports WHERE id = ?", (issue_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_diagnostics(self) -> Dict[str, Any]:
        """Sistem teşhis ve hata istatistiklerini getir."""
        issues = await self.list_issues()
        open_count = sum(1 for i in issues if i["status"] in ("open", "in_progress"))
        resolved_count = sum(1 for i in issues if i["status"] in ("resolved", "closed"))

        return {
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "total_issues": len(issues),
            "open_issues": open_count,
            "resolved_issues": resolved_count,
            "categories": {
                "analysis": sum(1 for i in issues if i["category"] == "analysis"),
                "orders": sum(1 for i in issues if i["category"] == "orders"),
                "account": sum(1 for i in issues if i["category"] == "account"),
                "settings": sum(1 for i in issues if i["category"] == "settings"),
                "other": sum(1 for i in issues if i["category"] not in ("analysis", "orders", "account", "settings")),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
