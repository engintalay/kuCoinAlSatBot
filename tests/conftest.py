"""
Pytest ortak yapılandırması.

KRİTİK: Testlerin GERÇEK veritabanlarına (auth.db, bot_settings.db, database.db)
asla dokunmamasını garanti eder. Global singleton'ların (user_store, settings_mgr)
db_path'leri, test oturumu boyunca geçici bir dizine yönlendirilir. Böylece
`from src.main import app` yapan testler kullanıcı verisini SİLEMEZ/EZEMEZ.
"""

import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolate_real_databases():
    """Tüm test oturumu için global DB yollarını geçici dizine yönlendir."""
    tmpdir = tempfile.mkdtemp(prefix="kucoinbot_tests_")

    # main.py import edilince global singleton'lar oluşur; onları yakala.
    try:
        import src.main as main
    except Exception:
        main = None

    saved = {}

    if main is not None:
        # Auth kullanıcı deposu
        if hasattr(main, "user_store"):
            saved["user_store"] = main.user_store.db_path
            main.user_store.db_path = os.path.join(tmpdir, "test_auth.db")
            main.user_store._initialized = False
        # Ayarlar
        if hasattr(main, "settings_mgr"):
            saved["settings_mgr"] = main.settings_mgr.db_path
            main.settings_mgr.db_path = os.path.join(tmpdir, "test_settings.db")
        # Hata takip
        if hasattr(main, "bug_tracker"):
            saved["bug_tracker"] = main.bug_tracker.db_path
            main.bug_tracker.db_path = os.path.join(tmpdir, "test_bugs.db")

    yield

    # Oturum sonunda orijinal yolları geri yükle (temizlik)
    if main is not None:
        for attr, path in saved.items():
            try:
                getattr(main, attr).db_path = path
            except Exception:
                pass
