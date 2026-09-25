"""
KuCoin Al-Sat Botu — WebSocket Canlı Fiyat ve Ticker Testleri
FastAPI WebSocket /ws/live bağlantısını, anlık fiyat iletimini ve dinamik sembol/piyasa aboneliğini test eder.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from src.models.market import TickerResponse
from src.models.account import PortfolioSummaryResponse
from src.utils.time_sync import timestamp


@pytest.fixture
def client_with_mock_market():
    from src.main import app, market, account

    # Mock market.get_ticker so we don't depend on external network
    async def mock_get_ticker(symbol: str, market_type: str = "spot"):
        price_map = {
            "BTC/USDT": 65000.0,
            "ETH/USDT": 3500.0,
            "SOL/USDT": 150.0,
        }
        price = price_map.get(symbol.upper(), 100.0)
        return TickerResponse(
            success=True,
            data={
                "symbol": symbol,
                "market_type": market_type,
                "last_price": price,
                "high_24h": price * 1.05,
                "low_24h": price * 0.95,
                "volume_24h": 12345.67,
                "change_percentage_24h": 2.5,
                "best_bid": price * 0.999,
                "best_ask": price * 1.001,
            },
            error=None,
            timestamp=timestamp(),
        )

    orig_get_ticker = market.get_ticker
    market.get_ticker = AsyncMock(side_effect=mock_get_ticker)

    orig_get_summary = account.get_summary
    account.get_summary = AsyncMock(return_value=PortfolioSummaryResponse(
        success=True,
        data={
            "total_portfolio_usdt": 10000.0,
            "free_usdt": 8000.0,
            "used_usdt": 2000.0,
            "asset_count": 3,
        },
        error=None,
        timestamp=timestamp(),
    ))

    client = TestClient(app)
    yield client

    market.get_ticker = orig_get_ticker
    account.get_summary = orig_get_summary


def test_websocket_connect_and_initial_tick(client_with_mock_market):
    """WebSocket /ws/live bağlantı kurabilmeli ve ilk tick verisini alabilmeli."""
    with client_with_mock_market.websocket_connect("/ws/live?symbol=BTC/USDT&market_type=spot") as ws:
        data = ws.receive_json()
        assert data["type"] == "tick"
        assert "timestamp" in data
        assert data["symbol"] == "BTC/USDT"
        assert data["market_type"] == "spot"
        assert data["ticker"] is not None
        assert data["ticker"]["symbol"] == "BTC/USDT"
        assert data["ticker"]["last_price"] == 65000.0
        assert "mode" in data
        assert "bot_active" in data


def test_websocket_dynamic_symbol_subscription(client_with_mock_market):
    """İstemci 'subscribe' mesajı gönderdiğinde WebSocket anında yeni sembol ve piyasa türünü dinlemeye başlamalı."""
    with client_with_mock_market.websocket_connect("/ws/live?symbol=BTC/USDT&market_type=spot") as ws:
        # 1. İlk mesaj BTC/USDT gelmeli
        first_data = ws.receive_json()
        assert first_data["symbol"] == "BTC/USDT"
        assert first_data["ticker"]["last_price"] == 65000.0

        # 2. ETH/USDT vadeli (futures) aboneliği gönder
        ws.send_json({
            "action": "subscribe",
            "symbol": "ETH/USDT",
            "market_type": "futures",
        })

        # 3. Sıradaki mesaj güncellenen ETH/USDT vadeli verisi olmalı
        next_data = ws.receive_json()
        assert next_data["symbol"] == "ETH/USDT"
        assert next_data["market_type"] == "futures"
        assert next_data["ticker"]["symbol"] == "ETH/USDT"
        assert next_data["ticker"]["market_type"] == "futures"
        assert next_data["ticker"]["last_price"] == 3500.0


def test_websocket_custom_coin_subscription(client_with_mock_market):
    """Kullanıcı analiz ekranında farklı bir coin girdiğinde (örn: SOL/USDT) WS doğru fiyata güncellenmeli."""
    with client_with_mock_market.websocket_connect("/ws/live?symbol=BTC/USDT") as ws:
        first = ws.receive_json()
        assert first["symbol"] == "BTC/USDT"

        # SOL/USDT marjin aboneliği
        ws.send_json({
            "action": "subscribe",
            "symbol": "SOL/USDT",
            "market_type": "margin",
        })

        data = ws.receive_json()
        assert data["symbol"] == "SOL/USDT"
        assert data["market_type"] == "margin"
        assert data["ticker"]["last_price"] == 150.0
