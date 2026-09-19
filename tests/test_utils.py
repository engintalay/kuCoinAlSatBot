"""
KuCoin Al-Sat Botu — Yardımcı Fonksiyon Testleri
crypto (format_price, format_amount), time_sync (timestamp, check_time_sync), logger.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestFormatPrice:
    def test_btc_two_decimals(self):
        from src.utils.crypto import format_price
        assert format_price("BTC", 70050.5) == "70,050.50"

    def test_shib_eight_decimals(self):
        from src.utils.crypto import format_price
        assert format_price("SHIB", 0.0000185) == "0.00001850"

    def test_default_four_decimals(self):
        from src.utils.crypto import format_price
        assert format_price("XYZ", 1.23456789) == "1.2346"

    def test_case_insensitive_symbol(self):
        from src.utils.crypto import format_price
        assert format_price("btc", 100.0) == "100.00"

    def test_accepts_decimal_input(self):
        from decimal import Decimal
        from src.utils.crypto import format_price
        assert format_price("ETH", Decimal("2000.5")) == "2,000.50"


class TestFormatAmount:
    def test_two_decimals_with_separator(self):
        from src.utils.crypto import format_amount
        assert format_amount(1250.456) == "1,250.46"

    def test_zero(self):
        from src.utils.crypto import format_amount
        assert format_amount(0) == "0.00"

    def test_large_value(self):
        from src.utils.crypto import format_amount
        assert format_amount(1234567.891) == "1,234,567.89"


class TestTimestamp:
    def test_returns_iso_utc(self):
        from src.utils.time_sync import timestamp
        ts = timestamp()
        assert isinstance(ts, str)
        # ISO 8601 UTC (+00:00) formatı
        assert "T" in ts
        assert ts.endswith("+00:00") or ts.endswith("Z")


class TestCheckTimeSync:
    def test_success_within_threshold(self):
        """Sunucu saati yerel saate yakınsa senkron başarılı dönmeli."""
        import time
        from src.utils import time_sync
        now_ms = int(time.time() * 1000)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": now_ms}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.utils.time_sync.requests.get", return_value=mock_resp):
            ok, latency, msg = time_sync.check_time_sync()
        assert ok is True

    def test_failure_on_large_drift(self):
        """3 saniyeden fazla fark uyumsuzluk dönmeli."""
        import time
        from src.utils import time_sync
        drift_ms = int(time.time() * 1000) + 10000  # +10 sn
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": drift_ms}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.utils.time_sync.requests.get", return_value=mock_resp):
            ok, latency, msg = time_sync.check_time_sync()
        assert ok is False
        assert "uyumsuz" in msg.lower() or "fark" in msg.lower()

    def test_network_error_handled(self):
        """Ağ hatası çökmeden False dönmeli."""
        import requests
        from src.utils import time_sync
        with patch("src.utils.time_sync.requests.get",
                   side_effect=requests.exceptions.ConnectionError("no net")):
            ok, latency, msg = time_sync.check_time_sync()
        assert ok is False


class TestLogger:
    def test_setup_logger_returns_logger(self):
        from src.utils.logger import setup_logger
        import logging
        lg = setup_logger("test_logger", "INFO")
        assert isinstance(lg, logging.Logger)
        assert lg.level == logging.INFO

    def test_global_logger_exists(self):
        from src.utils.logger import logger
        assert logger is not None
        assert hasattr(logger, "info")
