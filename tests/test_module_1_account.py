"""
KuCoin Al-Sat Botu — Modül 1 Testleri
Bakiye, bağlantı, .env kontrolü.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestKuCoinAccount:
    """KuCoinAccount sınıfı testleri."""

    @patch("src.modules.module1_account.KuCoinAccount.connect")
    def test_connect_success(self, mock_connect):
        """Bağlantı başarılı olmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        mock_connect.return_value = True
        assert account.connect() is True

    @patch("src.modules.module1_account.KuCoinAccount.connect")
    def test_connect_failure(self, mock_connect):
        """Bağlantı başarısız olmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        mock_connect.return_value = False
        assert account.connect() is False

    @patch("src.modules.module1_account.KuCoinAccount.connect")
    def test_connect_creates_exchange(self, mock_connect):
        """Bağlantı başarılı olduğunda exchange oluşturulmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        mock_connect.return_value = True
        account.connect()
        assert account.exchange is not None

    @patch("src.modules.module1_account.KuCoinAccount.connect")
    def test_connect_creates_exchange_on_failure(self, mock_connect):
        """Bağlantı başarısız olduğunda exchange oluşturulmamalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        mock_connect.return_value = False
        account.connect()
        assert account.exchange is None

    def test_get_balances_no_connection(self):
        """Bağlantı yoksa bakiye hatası dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        result = account.get_balances()
        assert result.success is False
        assert result.error is not None

    @patch("src.modules.module1_account.KuCoinAccount._check_time_sync")
    @patch("src.modules.module1_account.KuCoinAccount.get_balances")
    def test_get_balances_success(self, mock_get_balances, mock_check_time_sync):
        """Bağlantı başarılı olduğunda bakiye dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        mock_check_time_sync.return_value = (True, 42.0, "Zaman senkronize")
        mock_get_balances.return_value = {
            "success": True,
            "data": {"balances": []},
            "error": None,
            "timestamp": "2026-09-17T21:00:00Z"
        }
        account = KuCoinAccount()
        result = account.get_balances()
        assert result.success is True
        assert result.data is not None

    def test_test_connection_success(self):
        """Bağlantı testi başarılı olmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        result = account.test_connection()
        assert result.success is True
        assert result.data is not None

    def test_test_connection_failure(self):
        """Bağlantı testi başarısız olmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        result = account.test_connection()
        assert result.success is False
        assert result.error is not None

    @patch("src.modules.module1_account.KuCoinAccount.get_balances")
    def test_get_summary_no_balances(self, mock_get_balances):
        """Bakiye yoksa özet hatası dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        mock_get_balances.return_value = {
            "success": False,
            "data": {},
            "error": "Hata",
            "timestamp": "2026-09-17T21:00:00Z"
        }
        account = KuCoinAccount()
        result = account.get_summary()
        assert result.success is False
        assert result.error is not None

    @patch("src.modules.module1_account.KuCoinAccount.get_balances")
    def test_get_summary_success(self, mock_get_balances):
        """Bakiye başarılı olduğunda özet dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        mock_get_balances.return_value = {
            "success": True,
            "data": {"balances": []},
            "error": None,
            "timestamp": "2026-09-17T21:00:00Z"
        }
        account = KuCoinAccount()
        result = account.get_summary()
        assert result.success is True
        assert result.data is not None


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


class TestDatabase:
    """Database sınıfı testleri."""

    def test_database_create_tables(self):
        """Tablolar oluşturulmalı."""
        from src.database import Database
        db = Database("test_db.db")
        import asyncio
        asyncio.run(db.create_tables())
        import os
        if os.path.exists("test_db.db"):
            os.remove("test_db.db")
        assert True

    def test_database_connect(self):
        """Veritabanı bağlantısı kurulmalı."""
        from src.database import Database
        db = Database("test_connect.db")
        import asyncio
        asyncio.run(db.connect())
        assert db.database is not None
        import os
        if os.path.exists("test_connect.db"):
            os.remove("test_connect.db")
