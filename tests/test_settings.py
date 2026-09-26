"""
KuCoin Al-Sat Botu — Ayarlar & Watchlist Testleri (MODULE_3_SPEC 2.8)
"""

import os
import pytest
from unittest.mock import AsyncMock


def _mgr(tmp_path):
    from src.modules.settings import SettingsManager
    db = str(tmp_path / "test_settings.db")
    return SettingsManager(db_path=db)


class TestSettings:
    @pytest.mark.asyncio
    async def test_defaults_created(self, tmp_path):
        sm = _mgr(tmp_path)
        res = await sm.get_settings()
        assert res["success"] is True
        assert "BTC/USDT" in res["data"]["watchlist"]
        assert res["data"]["default_mode"] == "paper"

    @pytest.mark.asyncio
    async def test_partial_update_preserves_other_fields(self, tmp_path):
        """
        Regresyon: kısmi güncelleme (yalnızca default_mode) diğer alanları
        (watchlist, default_symbol) SIFIRLAMAMALI. 'Kaydedildi ama kaydetmiyor'
        hatasının kök nedeni buydu.
        """
        from src.modules.settings import SettingsManager
        db = str(tmp_path / "partial.db")
        sm = SettingsManager(db_path=db)
        # Özel watchlist + sembol kaydet
        await sm.update_settings({"watchlist": ["DOGE/USDT", "PEPE/USDT"], "default_symbol": "DOGE/USDT"})
        # Sonra SADECE modu güncelle (frontend save watchlist göndermez)
        await sm.update_settings({"default_mode": "live", "default_symbol": "DOGE/USDT",
                                  "default_timeframe": "1h", "risk": {"max_order_usdt": 500}})
        # Diskten yeni instance ile oku → özel watchlist korunmalı
        sm2 = SettingsManager(db_path=db)
        s = await sm2.load()
        assert s["watchlist"] == ["DOGE/USDT", "PEPE/USDT"], "watchlist sıfırlanmamalı"
        assert s["default_mode"] == "live"
        assert s["default_symbol"] == "DOGE/USDT"
        # risk derin merge: güncellenen alan + korunan varsayılanlar
        assert s["risk"]["max_order_usdt"] == 500
        assert s["risk"]["default_stop_loss_pct"] == 2.0

    @pytest.mark.asyncio
    async def test_update_and_persist(self, tmp_path):
        from src.modules.settings import SettingsManager
        db = str(tmp_path / "persist.db")
        sm = SettingsManager(db_path=db)
        await sm.update_settings({"default_mode": "live", "default_symbol": "ETH/USDT"})
        # yeni instance aynı db'den okumalı (kalıcılık)
        sm2 = SettingsManager(db_path=db)
        res = await sm2.get_settings()
        assert res["data"]["default_mode"] == "live"
        assert res["data"]["default_symbol"] == "ETH/USDT"

    @pytest.mark.asyncio
    async def test_invalid_mode_falls_back_to_paper(self, tmp_path):
        sm = _mgr(tmp_path)
        res = await sm.update_settings({"default_mode": "turbo"})
        assert res["data"]["default_mode"] == "paper"

    @pytest.mark.asyncio
    async def test_add_remove_watchlist(self, tmp_path):
        sm = _mgr(tmp_path)
        await sm.add_to_watchlist("AVAX/USDT")
        r1 = await sm.get_settings()
        assert "AVAX/USDT" in r1["data"]["watchlist"]
        await sm.remove_from_watchlist("AVAX/USDT")
        r2 = await sm.get_settings()
        assert "AVAX/USDT" not in r2["data"]["watchlist"]

    @pytest.mark.asyncio
    async def test_add_duplicate_no_error(self, tmp_path):
        sm = _mgr(tmp_path)
        await sm.add_to_watchlist("BTC/USDT")  # zaten var
        res = await sm.get_settings()
        # tekrar eklenmemeli
        assert res["data"]["watchlist"].count("BTC/USDT") == 1

    @pytest.mark.asyncio
    async def test_search_symbols_filters(self, tmp_path):
        from src.models.market import SymbolListResponse
        sm = _mgr(tmp_path)
        sm.market = AsyncMock()
        sm.market.get_symbols.return_value = SymbolListResponse(
            success=True,
            data={"quote": "USDT", "count": 3,
                  "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"]},
            error=None, timestamp="2026-01-01T00:00:00Z")
        res = await sm.search_symbols("eth")
        assert res["success"] is True
        assert res["data"]["symbols"] == ["ETH/USDT"]


class TestUserScopedSettings:
    """Task 7: kullanıcı-bazlı ayarlar (user_settings tablosu)."""

    @pytest.mark.asyncio
    async def test_per_user_watchlist_isolated(self, tmp_path):
        from src.modules.settings import SettingsManager
        base = SettingsManager(db_path=str(tmp_path / "us.db"))
        s1 = base.for_user(1)
        s2 = base.for_user(2)
        await s1.update_settings({"watchlist": ["BTC/USDT", "DOGE/USDT"]})
        await s2.update_settings({"watchlist": ["ETH/USDT"]})
        r1 = (await s1.get_settings())["data"]["watchlist"]
        r2 = (await s2.get_settings())["data"]["watchlist"]
        assert r1 == ["BTC/USDT", "DOGE/USDT"]
        assert r2 == ["ETH/USDT"]

    @pytest.mark.asyncio
    async def test_user_settings_persist_across_instances(self, tmp_path):
        from src.modules.settings import SettingsManager
        db = str(tmp_path / "persist_user.db")
        await SettingsManager(db_path=db, user_id=7).update_settings({"default_symbol": "SOL/USDT"})
        # yeni instance ile diskten oku
        got = await SettingsManager(db_path=db, user_id=7).get_settings()
        assert got["data"]["default_symbol"] == "SOL/USDT"

    @pytest.mark.asyncio
    async def test_global_and_user_are_separate(self, tmp_path):
        from src.modules.settings import SettingsManager
        db = str(tmp_path / "sep.db")
        base = SettingsManager(db_path=db)  # global (user_id=None)
        await base.update_settings({"default_symbol": "GLOBAL/USDT"})
        u = base.for_user(99)
        await u.update_settings({"default_symbol": "USER/USDT"})
        assert (await base.get_settings())["data"]["default_symbol"] == "GLOBAL/USDT"
        assert (await u.get_settings())["data"]["default_symbol"] == "USER/USDT"

    @pytest.mark.asyncio
    async def test_watchlist_add_remove_user_scoped(self, tmp_path):
        from src.modules.settings import SettingsManager
        s = SettingsManager(db_path=str(tmp_path / "wl.db"), user_id=3)
        await s.add_to_watchlist("AVAX/USDT")
        assert "AVAX/USDT" in (await s.get_settings())["data"]["watchlist"]
        await s.remove_from_watchlist("AVAX/USDT")
        assert "AVAX/USDT" not in (await s.get_settings())["data"]["watchlist"]
