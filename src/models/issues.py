"""
KuCoin Al-Sat Botu — Hata Raporlama ve Sorun Takibi Pydantic Şemaları
Kullanıcı hata bildirimleri, sistem teşhis kayıtları ve sorun durumları.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class IssueCreate(BaseModel):
    """Yeni hata bildirimi oluşturma şeması."""
    title: str = Field(..., min_length=3, max_length=200, description="Hata başlığı")
    category: str = Field(default="general", description="Hata kategorisi: analysis, orders, account, settings, chart, api, general")
    severity: str = Field(default="medium", description="Önem derecesi: critical, high, medium, low")
    description: str = Field(..., min_length=5, description="Hata açıklaması")
    steps_to_reproduce: Optional[str] = Field(default=None, description="Hatanın tekrarlanma adımları")
    expected_behavior: Optional[str] = Field(default=None, description="Beklenen davranış")
    actual_behavior: Optional[str] = Field(default=None, description="Gerçekleşen davranış")
    system_info: Optional[str] = Field(default=None, description="Sistem/tarayıcı bilgileri")


class IssueUpdate(BaseModel):
    """Hata bildirimi güncelleme şeması."""
    status: Optional[str] = Field(default=None, description="Durum: open, in_progress, resolved, closed")
    resolution_note: Optional[str] = Field(default=None, description="Çözüm açıklaması veya inceleme notu")
    severity: Optional[str] = Field(default=None, description="Güncellenen önem derecesi")
    title: Optional[str] = Field(default=None, description="Güncellenen başlık")
    description: Optional[str] = Field(default=None, description="Güncellenen açıklama")


class IssueItem(BaseModel):
    """Tekil hata kaydı detayı."""
    id: int
    title: str
    category: str
    severity: str
    status: str
    description: str
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    system_info: Optional[str] = None
    resolution_note: Optional[str] = None
    created_at: str
    updated_at: str


class IssueListResponse(BaseModel):
    """Hata listesi API yanıtı."""
    success: bool
    data: List[IssueItem]
    total: int
    open_count: int
    resolved_count: int
    error: Optional[str] = None
    timestamp: str


class IssueDetailResponse(BaseModel):
    """Tekil hata detayı API yanıtı."""
    success: bool
    data: Optional[IssueItem] = None
    error: Optional[str] = None
    timestamp: str
