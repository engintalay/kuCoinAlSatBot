"""
KuCoin Al-Sat Botu — Hata Raporlama (Issue Tracker) ve Sembol Seçici Testleri
Hata takip motoru, REST API endpoint'leri ve arayüz bileşenlerini doğrular.
"""

import pytest
import os
from fastapi.testclient import TestClient
from src.main import app
from src.modules.bug_reports import BugTracker


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
async def temp_bug_tracker(tmp_path):
    db_file = str(tmp_path / "temp_bugs.db")
    tracker = BugTracker(db_file)
    await tracker.init_db()
    return tracker


@pytest.mark.asyncio
async def test_bug_tracker_seed_bugs(temp_bug_tracker):
    """BugTracker ilk açılışta Hata #1 ve Hata #2'yi tohumlamalı."""
    issues = await temp_bug_tracker.list_issues()
    assert len(issues) >= 2
    ids = [i["id"] for i in issues]
    assert 1 in ids
    assert 2 in ids
    bug1 = next(i for i in issues if i["id"] == 1)
    assert "combo" in bug1["title"] or "BTC" in bug1["title"]
    assert bug1["status"] == "resolved"
    bug2 = next(i for i in issues if i["id"] == 2)
    assert "canlı" in bug2["title"] or "live" in bug2["title"]
    assert bug2["category"] == "settings"
    assert bug2["status"] == "resolved"


def test_settings_live_mode_switch(client):
    """Ayarlar üzerinden 'live' moda geçiş yapılabilmeli ve orders.mode senkronize olmalı."""
    from src.main import orders

    # 1. Ayarlardan 'live' moda geçiş
    r_live = client.post("/api/v1/settings", json={"default_mode": "live"})
    assert r_live.status_code == 200
    assert r_live.json()["success"] is True
    assert orders.mode == "live"

    # 2. /orders/mode endpoint'i canlı modu teyit etmeli
    r_mode = client.get("/api/v1/orders/mode")
    assert r_mode.status_code == 200
    m_data = r_mode.json()["data"]
    assert m_data["mode"] == "live"
    assert m_data["is_live"] is True

    # 3. Geriye simülasyona (paper) geçiş ve ayarlar senkronizasyonu
    r_paper = client.post("/api/v1/orders/switch-mode", json={"mode": "paper"})
    assert r_paper.status_code == 200
    assert orders.mode == "paper"

    # Ayarlar da senkronize olarak 'paper' dönmeli
    r_set = client.get("/api/v1/settings")
    assert r_set.json()["data"]["default_mode"] == "paper"


@pytest.mark.asyncio
async def test_bug_tracker_crud_lifecycle(temp_bug_tracker):
    """Hata oluşturma, getirme, güncelleme ve silme yaşam döngüsü."""
    # 1. Create
    created = await temp_bug_tracker.create_issue(
        title="Test Emri Verilemiyor",
        category="orders",
        severity="critical",
        description="Limit emir girerken bakiye yetersiz uyarısı hatalı tetikleniyor.",
        steps_to_reproduce="1. Emir sekmesine git\n2. Limit 100 USDT gir\n3. Hata al",
        expected_behavior="Emir başarıyla oluşturulmalı",
        actual_behavior="Yetersiz bakiye hatası",
        system_info="TestClient OS Linux"
    )
    assert created["id"] > 1
    assert created["title"] == "Test Emri Verilemiyor"
    assert created["status"] == "open"

    # 2. Get
    fetched = await temp_bug_tracker.get_issue(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["severity"] == "critical"

    # 3. Update status to in_progress then resolved
    updated = await temp_bug_tracker.update_issue(
        created["id"],
        status="in_progress"
    )
    assert updated["status"] == "in_progress"

    resolved = await temp_bug_tracker.update_issue(
        created["id"],
        status="resolved",
        resolution_note="Bakiye kontrol mantığı düzeltildi."
    )
    assert resolved["status"] == "resolved"
    assert "Bakiye" in resolved["resolution_note"]

    # 4. List with filter
    resolved_list = await temp_bug_tracker.list_issues(status="resolved")
    assert any(i["id"] == created["id"] for i in resolved_list)

    # 5. Delete
    deleted = await temp_bug_tracker.delete_issue(created["id"])
    assert deleted is True

    # 6. Verify deleted
    gone = await temp_bug_tracker.get_issue(created["id"])
    assert gone is None


@pytest.mark.asyncio
async def test_bug_tracker_diagnostics(temp_bug_tracker):
    """Teşhis verileri doğru sayaçları ve platformu dönmeli."""
    diag = await temp_bug_tracker.get_diagnostics()
    assert "platform" in diag
    assert "python_version" in diag
    assert diag["total_issues"] >= 1
    assert "categories" in diag
    assert "timestamp" in diag


def test_api_issues_endpoints(client):
    """/api/v1/issues REST API uç noktaları doğrulaması."""
    # Listeleme
    r = client.get("/api/v1/issues")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "total" in data
    assert "open_count" in data
    assert "resolved_count" in data
    assert len(data["data"]) >= 1

    # Hata #1 kontrolü
    r1 = client.get("/api/v1/issues/1")
    assert r1.status_code == 200
    bug1 = r1.json()["data"]
    assert bug1["id"] == 1
    assert "BTC" in bug1["title"]

    # Yeni hata kaydetme
    new_payload = {
        "title": "Arayüzde Font Boyutu Küçük",
        "category": "chart",
        "severity": "low",
        "description": "Mum grafiğindeki eksen yazıları küçük görünüyor.",
        "steps_to_reproduce": "Grafiği aç",
        "expected_behavior": "Daha okunaklı font",
        "actual_behavior": "10px font",
        "system_info": "Chrome 120"
    }
    r_create = client.post("/api/v1/issues", json=new_payload)
    assert r_create.status_code == 200
    created_item = r_create.json()["data"]
    new_id = created_item["id"]
    assert created_item["title"] == new_payload["title"]

    # Durum güncelleme (PATCH)
    r_patch = client.patch(f"/api/v1/issues/{new_id}", json={
        "status": "resolved",
        "resolution_note": "CSS font boyutu 12px yapıldı."
    })
    assert r_patch.status_code == 200
    assert r_patch.json()["data"]["status"] == "resolved"

    # Silme (DELETE)
    r_del = client.delete(f"/api/v1/issues/{new_id}")
    assert r_del.status_code == 200
    assert r_del.json()["data"]["deleted_id"] == new_id


def test_api_diagnostics_endpoint(client):
    """/api/v1/system/diagnostics sistem teşhis endpoint doğrulaması."""
    r = client.get("/api/v1/system/diagnostics")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    d = data["data"]
    assert "platform" in d
    assert "orders_mode" in d
    assert "exchange_connected" in d
    assert "watchlist_count" in d


def test_frontend_issues_and_symbol_combo(client):
    """Frontend HTML'inde Hata Raporlama ekranı ve Koin combo/çipler bulunmalı."""
    r = client.get("/")
    assert r.status_code == 200
    text = r.text

    # Hata Raporlama menüsü ve görünümü
    assert 'data-view="issues"' in text
    assert 'id="view-issues"' in text
    assert 'id="issue-form"' in text
    assert 'id="issues-list"' in text
    assert 'id="diagnostics-summary"' in text
    assert 'id="diagnostics-log-box"' in text
    assert 'data-info="bug-report"' in text

    # Analiz ekranı koin açılır kutusu (combo) ve hızlı seçim çipleri
    assert 'id="analysis-symbol-select"' in text
    assert 'id="analysis-symbol"' in text
    assert 'id="analysis-quick-chips"' in text
    assert 'class="quick-symbol-bar"' in text

    # Sembol alanları için datalist entegrasyonu korunmalı (analiz + emir + bracket + pnl)
    assert text.count('list="symbol-choices"') == 4
