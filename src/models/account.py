"""
KuCoin Al-Sat Botu — Modül 1 Pydantic Şemaları
Hesap durumu ve bağlantı bilgileri.
"""

from pydantic import BaseModel, Field


class ConnectionStatusResponse(BaseModel):
    """KuCoin API bağlantı durumu."""
    success: bool
    data: dict = Field(description="Bağlantı durumu bilgileri")
    error: str | None = None
    timestamp: str


class AssetBalance(BaseModel):
    """Tek bir kripto varlığının bakiye bilgisi."""
    symbol: str
    free: float = 0.0
    used: float = 0.0
    total: float = 0.0
    price_usdt: float = 0.0
    usdt_value: float = 0.0
    portfolio_share_percent: float = 0.0
    avg_cost: float | None = None
    total_cost: float | None = None
    unrealized_pnl: float | None = None
    pnl_percent: float | None = None


class ConnectionStatusData(BaseModel):
    """Bağlantı durumu detayları."""
    status: str  # "CONNECTED"
    is_sandbox: bool
    latency_ms: float
    permissions: list[str]


class AccountBalancesResponse(BaseModel):
    """Tüm kripto varlıklarının bakiye bilgileri."""
    success: bool
    data: dict = Field(description="Bakiye bilgileri")
    error: str | None = None
    timestamp: str


class PortfolioSummaryResponse(BaseModel):
    """Toplam portföy özet bilgisi."""
    success: bool
    data: dict = Field(description="Portföy özet bilgileri")
    error: str | None = None
    timestamp: str


class TestConnectionResponse(BaseModel):
    """API bağlantı testi sonucu."""
    success: bool
    data: dict = Field(description="Test sonucu")
    error: str | None = None
    timestamp: str
