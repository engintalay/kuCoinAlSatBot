"""
KuCoin Al-Sat Botu — Katman 9 Piyasa Geneli Rejim Testleri (MODULE_2_SPEC 3.9)
CoinGecko harici API mock'lanır (GLOBAL_STANDARDS 5.2).
"""

import pytest
from unittest.mock import patch, MagicMock


def _mock_response(payload):
    m = MagicMock()
    m.json.return_value = payload
    m.raise_for_status = MagicMock()
    return m


class TestMarketRegime:
    def test_risk_off_on_market_drop(self):
        """Piyasa düşüşte + stablecoin dominansı yüksekse RISK_OFF."""
        from src.modules.market_regime import MarketRegime
        payload = {"data": {
            "total_market_cap": {"usd": 2.5e12},
            "market_cap_change_percentage_24h_usd": -3.5,
            "market_cap_percentage": {"btc": 58.0, "eth": 11.0, "usdt": 7.0, "usdc": 3.0},
        }}
        with patch("src.modules.market_regime.requests.get", return_value=_mock_response(payload)):
            r = MarketRegime().get_regime()
        assert r["success"] is True
        assert r["data"]["regime"] == "RISK_OFF"
        assert r["data"]["stablecoin_dominance"] == pytest.approx(10.0)

    def test_risk_on_when_market_up(self):
        from src.modules.market_regime import MarketRegime
        payload = {"data": {
            "total_market_cap": {"usd": 3.0e12},
            "market_cap_change_percentage_24h_usd": 4.0,
            "market_cap_percentage": {"btc": 45.0, "eth": 18.0, "usdt": 4.0},
        }}
        with patch("src.modules.market_regime.requests.get", return_value=_mock_response(payload)):
            r = MarketRegime().get_regime()
        assert r["data"]["regime"] == "RISK_ON"

    def test_altseason_hint_low_btc_dominance(self):
        """BTC.D < %50 ise altseason ipucu True."""
        from src.modules.market_regime import MarketRegime
        payload = {"data": {
            "total_market_cap": {"usd": 3.0e12},
            "market_cap_change_percentage_24h_usd": 1.0,
            "market_cap_percentage": {"btc": 45.0, "eth": 20.0, "usdt": 4.0},
        }}
        with patch("src.modules.market_regime.requests.get", return_value=_mock_response(payload)):
            r = MarketRegime().get_regime()
        assert r["data"]["altseason_hint"] is True
        assert r["data"]["btc_dominance"] == 45.0

    def test_network_error_handled(self):
        """Ağ hatası çökmeden success=False dönmeli."""
        import requests
        from src.modules.market_regime import MarketRegime
        with patch("src.modules.market_regime.requests.get",
                   side_effect=requests.exceptions.ConnectionError("no net")):
            r = MarketRegime().get_regime()
        assert r["success"] is False
        assert r["error"] is not None
