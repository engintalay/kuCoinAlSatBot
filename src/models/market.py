"""
KuCoin Al-Sat Botu — Modül 2 Pydantic Şemaları
Piyasa verileri ve analiz sinyalleri.
"""

from pydantic import BaseModel, Field


class TickerResponse(BaseModel):
    """Canlı piyasa ticker bilgisi."""
    success: bool
    data: dict = Field(description="Ticker bilgileri")
    error: str | None = None
    timestamp: str


class CandleData(BaseModel):
    """Tek bir mum verisi."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class CandlesResponse(BaseModel):
    """Mum (OHLCV) veri seti."""
    success: bool
    data: dict = Field(description="Mum verileri")
    error: str | None = None
    timestamp: str


class SymbolListResponse(BaseModel):
    """Aktif işlem çiftleri listesi."""
    success: bool
    data: dict = Field(description="İşlem çiftleri")
    error: str | None = None
    timestamp: str


class OrderBookResponse(BaseModel):
    """Emir defteri (Level 2) özeti: best bid/ask, spread, imbalance."""
    success: bool
    data: dict = Field(description="Emir defteri bilgileri")
    error: str | None = None
    timestamp: str


class AnalysisSignalResponse(BaseModel):
    """Analiz sinyali sonuçları."""
    success: bool
    data: dict = Field(description="Analiz sinyali")
    error: str | None = None
    timestamp: str
