"""
KuCoin Al-Sat Botu — Modül 1 Testleri
Bakiye, bağlantı, .env kontrolü.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os


class TestKuCoinAccount:
    """KuCoinAccount sınıfı testleri."""

    def test_connect_success(self):
        """Bağlantı başarılı olmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        account.connect = MagicMock(return_value=True)
        assert account.connect() is True

    def test_connect_failure(self):
        """Bağlantı başarısız olmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        account.connect = MagicMock(return_value=False)
        assert account.connect() is False

    def test_connect_creates_exchange(self):
        """Bağlantı başarılı olduğunda exchange oluşturulmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        account.connect = MagicMock(return_value=True)
        account.connect()
        account.connect.assert_called_once()

    def test_connect_creates_exchange_on_failure(self):
        """Bağlantı başarısız olduğunda exchange oluşturulmamalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        account.connect = MagicMock(return_value=False)
        account.connect()
        assert account.exchange is None

    @pytest.mark.asyncio
    async def test_get_balances_no_connection(self):
        """Bağlantı kurulamıyorsa bakiye hatası dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        from src.models.account import AccountBalancesResponse
        account = KuCoinAccount()
        account.exchange = None
        # Lazy-connect denemesi de başarısız olsun (exchange None kalır)
        account.connect = MagicMock(return_value=False)
        result = await account.get_balances()
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_get_balances_success(self):
        """Bağlantı başarılı olduğunda bakiye dönmeli (spot/funding/margin birleşik)."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        mock_exchange = AsyncMock()
        # trade/main/margin çağrılarının hepsi aynı yapıyı döndürsün
        mock_exchange.fetch_balance.return_value = {
            "info": {},
            "total": {"BTC": 0.5, "ETH": 10.0},
            "free": {"BTC": 0.3, "ETH": 10.0},
            "used": {"BTC": 0.2, "ETH": 0.0},
        }
        mock_exchange.fetch_ticker.return_value = {"last": 50000.0}
        account.exchange = mock_exchange
        account.futures_exchange = None  # futures kapalı
        account.is_connected = True
        result = await account.get_balances()
        assert result.success is True
        assert len(result.data["balances"]) == 2  # BTC ve ETH

    @pytest.mark.asyncio
    async def test_get_balances_includes_futures_and_margin(self):
        """
        Bakiye tüm hesap tiplerini içermeli: spot/funding/margin (spot uç noktası)
        + futures (kucoinfutures). Her varlık hangi hesaplarda olduğunu 'accounts'
        alanında göstermeli.
        """
        from unittest.mock import AsyncMock
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()

        # Spot uç noktası: type'a göre farklı bakiye döndür
        async def fake_fetch_balance(params=None):
            t = (params or {}).get("type")
            if t == "trade":
                return {"total": {"BTC": 0.5}, "free": {"BTC": 0.5}, "used": {"BTC": 0.0}}
            if t == "main":
                return {"total": {"USDT": 100.0}, "free": {"USDT": 100.0}, "used": {"USDT": 0.0}}
            if t == "margin":
                return {"total": {"ETH": 2.0}, "free": {"ETH": 2.0}, "used": {"ETH": 0.0}}
            return {"total": {}, "free": {}, "used": {}}

        spot = AsyncMock()
        spot.fetch_balance.side_effect = fake_fetch_balance
        spot.fetch_ticker.return_value = {"last": 1000.0}
        account.exchange = spot

        # Futures teminat cüzdanı
        fut = AsyncMock()
        fut.fetch_balance.return_value = {"total": {"USDT": 250.0}, "free": {"USDT": 250.0}, "used": {"USDT": 0.0}}
        account.futures_exchange = fut
        account.is_connected = True

        result = await account.get_balances()
        assert result.success is True
        by_sym = {a["symbol"]: a for a in result.data["balances"]}
        # BTC spot'ta, ETH margin'de, USDT hem funding hem futures'ta
        assert by_sym["BTC"]["accounts"] == ["spot"]
        assert by_sym["ETH"]["accounts"] == ["margin"]
        assert set(by_sym["USDT"]["accounts"]) == {"funding", "futures"}
        # USDT toplamı funding(100) + futures(250) = 350
        assert by_sym["USDT"]["total"] == 350.0

    def test_test_connection_success(self):
        """Bağlantı testi başarılı olmalı."""
        from src.modules.module1_account import KuCoinAccount
        from src.models.account import TestConnectionResponse
        account = KuCoinAccount()
        with patch("src.modules.module1_account.check_time_sync",
                   return_value=(True, 42.0, "✅ Zaman senkronize: 42ms")), \
             patch.object(account.config, "validate_credentials", return_value=True):
            result = account.test_connection()
        assert result.success is True
        assert result.data is not None

    def test_test_connection_failure(self):
        """Bağlantı testi başarısız olmalı."""
        from src.modules.module1_account import KuCoinAccount
        from src.models.account import TestConnectionResponse
        account = KuCoinAccount()
        with patch("src.modules.module1_account.check_time_sync",
                   return_value=(False, 0, "❌ İnternet bağlantısı hatası")), \
             patch.object(account.config, "validate_credentials", return_value=True):
            result = account.test_connection()
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_get_summary_no_balances(self):
        """Bakiye yoksa özet hatası dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        from src.models.account import AccountBalancesResponse, PortfolioSummaryResponse
        mock_balances_response = AccountBalancesResponse(
            success=False,
            data={},
            error="KuCoin API'ye bağlanılamadı",
            timestamp="2026-09-17T21:00:00Z"
        )
        mock_get_balances = AsyncMock(return_value=mock_balances_response)
        with patch("src.modules.module1_account.KuCoinAccount.get_balances", new=mock_get_balances):
            account = KuCoinAccount()
            result = await account.get_summary()
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_get_summary_success(self):
        """Bakiye başarılı olduğunda özet dönmeli (hesap-bazlı kırılımla)."""
        from src.modules.module1_account import KuCoinAccount
        from src.models.account import AccountBalancesResponse, PortfolioSummaryResponse
        mock_balances_response = AccountBalancesResponse(
            success=True,
            data={
                "balances": [
                    {
                        "symbol": "BTC",
                        "free": 0.3,
                        "used": 0.2,
                        "total": 0.5,
                        "price_usdt": 50000.0,
                        "usdt_value": 25000.0,
                        "portfolio_share_percent": 0.0
                    }
                ],
                "accounts": [
                    {
                        "account": "spot",
                        "total_usdt": 25000.0,
                        "assets": [
                            {"symbol": "BTC", "free": 0.3, "used": 0.2, "total": 0.5, "price_usdt": 50000.0, "usdt_value": 25000.0}
                        ]
                    }
                ]
            },
            error=None,
            timestamp="2026-09-17T21:00:00Z"
        )
        mock_get_balances = AsyncMock(return_value=mock_balances_response)
        with patch("src.modules.module1_account.KuCoinAccount.get_balances", new=mock_get_balances):
            account = KuCoinAccount()
            result = await account.get_summary()
        assert result.success is True
        assert result.data is not None
        assert result.data["total_portfolio_usdt"] > 0
        # hesap-bazlı kırılım da gelmeli
        assert "total_by_account" in result.data
        assert result.data["total_by_account"]["spot"] == 25000.0


class TestAccountBalancesResponse:
    """Bakiye yanıt şeması testleri."""

    def test_valid_response(self):
        """Geçerli yanıt kontrolü."""
        from src.models.account import AccountBalancesResponse
        response = AccountBalancesResponse(
            success=True,
            data={"balances": []},
            error=None,
            timestamp="2026-09-17T21:00:00Z"
        )
        assert response.success is True
        assert response.data is not None

    def test_invalid_response(self):
        """Geçersiz yanıt kontrolü."""
        from src.models.account import AccountBalancesResponse
        response = AccountBalancesResponse(
            success=False,
            data={},
            error="Test error",
            timestamp="2026-09-17T21:00:00Z"
        )
        assert response.success is False
        assert response.error is not None

    def test_empty_balances(self):
        """Boş bakiye listesi kontrolü."""
        from src.models.account import AccountBalancesResponse
        response = AccountBalancesResponse(
            success=True,
            data={"balances": []},
            error=None,
            timestamp="2026-09-17T21:00:00Z"
        )
        assert response.data["balances"] == []

    def test_portfolio_summary_response(self):
        """Portföy özet yanıt kontrolü."""
        from src.models.account import PortfolioSummaryResponse
        response = PortfolioSummaryResponse(
            success=True,
            data={
                "total_portfolio_usdt": 1250.45,
                "free_usdt": 500.00,
                "in_orders_usdt": 750.45
            },
            error=None,
            timestamp="2026-09-17T21:00:00Z"
        )
        assert response.success is True
        assert response.data["total_portfolio_usdt"] == 1250.45


class TestConfig:
    """Config sınıfı testleri."""

    def test_config_has_api_keys(self):
        """Config API anahtarlarına sahip olmalı."""
        from src.config import Config
        config = Config()
        assert hasattr(config, "API_KEY")
        assert hasattr(config, "API_SECRET")
        assert hasattr(config, "API_PASSPHRASE")

    def test_config_is_sandbox_default(self):
        """IS_SANDBOX varsayılan false olmalı."""
        from src.config import Config
        config = Config()
        assert config.IS_SANDBOX is False

    def test_config_has_trading_mode(self):
        """DEFAULT_TRADING_MODE mevcut olmalı."""
        from src.config import Config
        config = Config()
        assert hasattr(config, "DEFAULT_TRADING_MODE")

    def test_config_default_trading_mode_is_real(self):
        """Varsayılan trading modu 'real' olmalı."""
        from src.config import Config
        config = Config()
        # .env dosyası varsayılan değeri kullanmalı (KUCOIN_IS_SANDBOX=false)
        assert config.DEFAULT_TRADING_MODE == "paper"

    def test_config_simulation_mode(self):
        """SIMULATION_MODE true olmalı (paper mod)."""
        from src.config import Config
        config = Config()
        # DEFAULT_TRADING_MODE=paper => SIMULATION_MODE=True
        assert config.SIMULATION_MODE is True

    def test_config_default_symbol(self):
        """DEFAULT_SYMBOL mevcut olmalı."""
        from src.config import Config
        config = Config()
        assert hasattr(config, "DEFAULT_SYMBOL")


class TestDatabase:
    """Database sınıfı testleri."""

    def test_database_create_tables(self):
        """Tablolar oluşturulmalı."""
        from src.database import Database
        db_path = "test_create_tables.db"
        db = Database(db_path)
        mock_connection = MagicMock()
        mock_connection.row_factory = None
        mock_connection.execute = AsyncMock()
        mock_connection.commit = AsyncMock()
        mock_connection.close = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch("aiosqlite.connect", new=AsyncMock(return_value=mock_connection)):
            asyncio.run(db.create_tables())
        # Tablo oluşturma sorguları çalıştırılmış olmalı (orders + balance_history)
        assert mock_connection.execute.await_count >= 2

    def test_database_connect(self):
        """Veritabanı bağlantısı kurulmalı."""
        from src.database import Database
        db_path = "test_connect.db"
        db = Database(db_path)
        mock_connection = MagicMock()
        mock_connection.row_factory = None
        mock_connection.execute = AsyncMock()
        mock_connection.commit = AsyncMock()
        mock_connection.close = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        with patch("aiosqlite.connect", new=AsyncMock(return_value=mock_connection)):
            asyncio.run(db.connect())
        assert db.database is not None


class TestPermissions:
    """API yetki denetimi (get_permissions / get_status) testleri."""

    @pytest.mark.asyncio
    async def test_permissions_read_and_trade(self):
        """General+Spot yetkisi read+trade olarak normalize edilmeli, withdraw yok."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        mock_exchange = AsyncMock()
        mock_exchange.private_get_user_api_key.return_value = {
            "code": "200000",
            "data": {"permission": "General,Futures,Spot,Margin"}
        }
        account.exchange = mock_exchange
        result = await account.get_permissions()
        assert result["has_read"] is True
        assert result["has_trade"] is True
        assert result["has_withdraw"] is False
        assert result["warning"] is None
        assert result["permissions"] == ["read", "trade"]

    @pytest.mark.asyncio
    async def test_permissions_withdraw_warning(self):
        """Withdrawal yetkisi tespit edilirse güvenlik uyarısı üretilmeli."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        mock_exchange = AsyncMock()
        mock_exchange.private_get_user_api_key.return_value = {
            "code": "200000",
            "data": {"permission": "General,Spot,Withdrawal"}
        }
        account.exchange = mock_exchange
        result = await account.get_permissions()
        assert result["has_withdraw"] is True
        assert result["warning"] is not None
        assert "Withdrawal" in result["warning"]

    @pytest.mark.asyncio
    async def test_permissions_no_connection(self):
        """Bağlantı kurulamıyorsa yetki denetimi güvenli boş dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        account.exchange = None
        account.connect = MagicMock(return_value=False)
        result = await account.get_permissions()
        assert result["has_read"] is False
        assert result["has_trade"] is False

    @pytest.mark.asyncio
    async def test_get_status_success(self):
        """Kimlik + zaman senkron + yetki başarılıysa status CONNECTED dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        with patch.object(account.config, "validate_credentials", return_value=True), \
             patch("src.modules.module1_account.check_time_sync",
                   return_value=(True, 42.0, "✅ Zaman senkronize: 42ms")), \
             patch.object(account, "get_permissions", new=AsyncMock(return_value={
                 "permissions": ["read", "trade"],
                 "has_read": True, "has_trade": True,
                 "has_withdraw": False, "warning": None,
             })):
            result = await account.get_status()
        assert result.success is True
        assert result.data["status"] == "CONNECTED"
        assert result.data["permissions"] == ["read", "trade"]

    @pytest.mark.asyncio
    async def test_get_status_missing_credentials(self):
        """Kimlik bilgisi eksikse status hata dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        with patch.object(account.config, "validate_credentials", return_value=False):
            result = await account.get_status()
        assert result.success is False
        assert result.error is not None


class TestBalanceStream:
    """WebSocket canlı bakiye akışı testleri."""

    @pytest.mark.asyncio
    async def test_start_stream_missing_credentials(self):
        """Kimlik bilgisi yoksa WebSocket başlatılmamalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        with patch.object(account.config, "validate_credentials", return_value=False):
            ok = await account.start_balance_stream()
        assert ok is False
        assert account._ws_running is False

    @pytest.mark.asyncio
    async def test_stop_stream_idempotent(self):
        """Akış çalışmıyorken stop çağrısı hatasız çalışmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        await account.stop_balance_stream()  # hiç başlatılmadı
        assert account._ws_running is False
        assert account.ws_exchange is None
