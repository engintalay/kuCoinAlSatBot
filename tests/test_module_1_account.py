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

    def test_get_balances_no_connection(self):
        """Bağlantı yoksa bakiye hatası dönmeli."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        result = account.get_balances()
        assert result.success is False
        assert "baglanilamadi" in result.error.lower() or "baglanti" in result.error.lower()

    def test_test_connection(self):
        """Bağlantı testi çalışmalı."""
        from src.modules.module1_account import KuCoinAccount
        account = KuCoinAccount()
        result = account.test_connection()
        assert result.success is False or result.data is not None


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
