"""
KuCoin Al-Sat Botu — Modül 2 Testleri
Ticker, emir defteri, mum (OHLCV) ve sembol listesi (mock'lu).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestGetTicker:
    """get_ticker testleri."""

    @pytest.mark.asyncio
    async def test_ticker_success(self):
        from src.modules.module2_market import KuCoinMarket
        m = KuCoinMarket()
        mock_ex = AsyncMock()
        mock_ex.fetch_ticker.return_value = {
            "last": 81000.0, "high": 82000.0, "low": 80000.0,
            "baseVolume": 1200.0, "quoteVolume": 98000000.0,
            "percentage": 1.25, "bid": 80999.0, "ask": 81001.0,
        }
        m.exchange = mock_ex
        result = await m.get_ticker("BTC/USDT")
        assert result.success is True
        assert result.data["last_price"] == 81000.0
        assert result.data["change_percentage_24h"] == 1.25

    @pytest.mark.asyncio
    async def test_ticker_no_connection(self):
        from src.modules.module2_market import KuCoinMarket
        m = KuCoinMarket()
        m.exchange = None
        m.connect = MagicMock(return_value=False)
        result = await m.get_ticker("BTC/USDT")
        assert result.success is False
        assert result.error is not None


class TestGetOrderBook:
    """get_orderbook testleri."""

    @pytest.mark.asyncio
    async def test_orderbook_success_and_imbalance(self):
        from src.modules.module2_market import KuCoinMarket
        m = KuCoinMarket()
        mock_ex = AsyncMock()
        # bids toplam hacim = 3, asks toplam hacim = 1 -> imbalance = (3-1)/4 = 0.5
        mock_ex.fetch_order_book.return_value = {
            "bids": [[100.0, 2.0], [99.0, 1.0]],
            "asks": [[101.0, 0.5], [102.0, 0.5]],
        }
        m.exchange = mock_ex
        result = await m.get_orderbook("BTC/USDT")
        assert result.success is True
        assert result.data["best_bid"] == 100.0
        assert result.data["best_ask"] == 101.0
        assert result.data["spread"] == 1.0
        assert result.data["imbalance"] == 0.5

    @pytest.mark.asyncio
    async def test_orderbook_empty(self):
        from src.modules.module2_market import KuCoinMarket
        m = KuCoinMarket()
        mock_ex = AsyncMock()
        mock_ex.fetch_order_book.return_value = {"bids": [], "asks": []}
        m.exchange = mock_ex
        result = await m.get_orderbook("BTC/USDT")
        assert result.success is False


class TestGetCandles:
    """get_candles testleri."""

    @pytest.mark.asyncio
    async def test_candles_success_and_repaint_guard(self):
        from src.modules.module2_market import KuCoinMarket
        m = KuCoinMarket()
        mock_ex = AsyncMock()
        mock_ex.fetch_ohlcv.return_value = [
            [1000, 10, 12, 9, 11, 100],
            [2000, 11, 13, 10, 12, 120],
            [3000, 12, 14, 11, 13, 90],
        ]
        m.exchange = mock_ex
        result = await m.get_candles("BTC/USDT", "1h", 3)
        assert result.success is True
        assert result.data["count"] == 3
        # Repaint koruması: son mum confirmed=False, öncekiler True
        assert result.data["candles"][-1]["confirmed"] is False
        assert result.data["candles"][0]["confirmed"] is True
        # Ring buffer dolmalı
        assert len(m.get_buffer("BTC/USDT", "1h")) == 3

    @pytest.mark.asyncio
    async def test_candles_invalid_timeframe(self):
        from src.modules.module2_market import KuCoinMarket
        m = KuCoinMarket()
        result = await m.get_candles("BTC/USDT", "3m", 10)
        assert result.success is False
        assert "timeframe" in result.error.lower()


class TestGetSymbols:
    """get_symbols testleri."""

    @pytest.mark.asyncio
    async def test_symbols_filters_active_usdt_spot(self):
        from src.modules.module2_market import KuCoinMarket
        m = KuCoinMarket()
        mock_ex = AsyncMock()
        mock_ex.load_markets.return_value = {
            "BTC/USDT": {"symbol": "BTC/USDT", "active": True, "quote": "USDT", "spot": True},
            "ETH/USDT": {"symbol": "ETH/USDT", "active": True, "quote": "USDT", "spot": True},
            "XRP/BTC": {"symbol": "XRP/BTC", "active": True, "quote": "BTC", "spot": True},
            "OLD/USDT": {"symbol": "OLD/USDT", "active": False, "quote": "USDT", "spot": True},
        }
        m.exchange = mock_ex
        result = await m.get_symbols("USDT")
        assert result.success is True
        assert result.data["symbols"] == ["BTC/USDT", "ETH/USDT"]
        assert result.data["count"] == 2


class TestMarketClose:
    """close() testi."""

    @pytest.mark.asyncio
    async def test_close_releases_exchange(self):
        from src.modules.module2_market import KuCoinMarket
        m = KuCoinMarket()
        mock_ex = AsyncMock()
        m.exchange = mock_ex
        await m.close()
        assert m.exchange is None
        mock_ex.close.assert_awaited_once()
