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
