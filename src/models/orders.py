"""
KuCoin Al-Sat Botu — Modül 3 Pydantic Şemaları
Emir oluşturma, takip ve yönetim.
"""

from pydantic import BaseModel, Field


class OrderCreateResponse(BaseModel):
    """Yeni emir oluşturma sonucu."""
    success: bool
    data: dict = Field(description="Emir bilgileri")
    error: str | None = None
    timestamp: str


class OpenOrdersResponse(BaseModel):
    """Açık emirler listesi."""
    success: bool
    data: dict = Field(description="Açık emirler")
    error: str | None = None
    timestamp: str


class OrderHistoryResponse(BaseModel):
    """Geçmiş emir geçmişi."""
    success: bool
    data: dict = Field(description="Emir geçmişi")
    error: str | None = None
    timestamp: str


class OrderCancelResponse(BaseModel):
    """Emir iptal sonucu."""
    success: bool
    data: dict = Field(description="İptal bilgileri")
    error: str | None = None
    timestamp: str


class PanicStopResponse(BaseModel):
    """Acil durum (Panic Stop) sonucu."""
    success: bool
    data: dict = Field(description="Panic stop bilgileri")
    error: str | None = None
    timestamp: str


class SwitchModeResponse(BaseModel):
    """Simülasyon/Live mod geçiş sonucu."""
    success: bool
    data: dict = Field(description="Mod geçiş bilgileri")
    error: str | None = None
    timestamp: str
