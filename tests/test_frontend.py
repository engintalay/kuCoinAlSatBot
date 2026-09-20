"""
KuCoin Al-Sat Botu — Frontend Dashboard servis testleri (Adım 5)
Dashboard HTML ve statik varlıkların FastAPI tarafından sunulduğunu doğrular.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from src.main import app
    return TestClient(app)


def test_dashboard_served(client):
    """Root '/' dashboard HTML dönmeli."""
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "KuCoin Al-Sat Botu" in r.text


def test_css_served(client):
    r = client.get("/static/css/style.css")
    assert r.status_code == 200
    assert "css" in r.headers.get("content-type", "")


def test_js_served(client):
    r = client.get("/static/js/app.js")
    assert r.status_code == 200


def test_api_info_endpoint(client):
    """/api bilgi endpoint'i JSON envelope dönmeli."""
    r = client.get("/api")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["name"] == "KuCoin Al-Sat Botu"


def test_dashboard_references_assets(client):
    """Dashboard HTML, CSS ve JS dosyalarına referans vermeli."""
    r = client.get("/")
    assert "/static/css/style.css" in r.text
    assert "/static/js/app.js" in r.text
    # Master Layout bileşenleri
    assert "PANIC STOP" in r.text
    assert "toast-container" in r.text


def test_guide_view_present(client):
    """Kullanım Kılavuzu görünümü ve navigasyon linki bulunmalı (GLOBAL_STANDARDS 2.3)."""
    r = client.get("/")
    assert 'data-view="guide"' in r.text
    assert "Kullanım Kılavuzu" in r.text
    assert 'id="view-guide"' in r.text
    # Kılavuz içeriği kritik başlıkları içermeli
    assert "SIMULATION" in r.text
    assert "Withdraw" in r.text


def test_contextual_info_buttons(client):
    """7 kritik arayüz noktasında bağlamsal info düğmeleri olmalı."""
    r = client.get("/")
    for point in ["portfolio", "mode", "panic", "score", "mtf", "smc", "orders"]:
        assert f'data-info="{point}"' in r.text, f"info button eksik: {point}"
    assert 'id="info-popover"' in r.text
    # info butonu ve popover stilleri
    css = client.get("/static/css/style.css").text
    assert ".info-btn" in css
    assert ".info-popover" in css


def test_bracket_and_settings_views(client):
    """Akıllı Paket Emir bileşeni ve Ayarlar görünümü bulunmalı."""
    r = client.get("/")
    assert "Akıllı Paket Emir" in r.text
    assert 'id="bracket-load"' in r.text
    assert 'data-info="bracket"' in r.text
    assert 'data-view="settings"' in r.text
    assert 'id="view-settings"' in r.text


def test_amend_modal_and_watchlist_widget(client):
    """Emir düzenleme modalı, mini watchlist ve öneri kartları alanı bulunmalı."""
    r = client.get("/")
    assert 'id="edit-modal"' in r.text
    assert 'id="mini-watchlist"' in r.text
    assert 'id="reco-cards"' in r.text


def test_symbol_datalist_integration(client):
    """Sembol girişleri watchlist datalist'ine bağlı olmalı."""
    r = client.get("/")
    assert 'id="symbol-choices"' in r.text
    assert r.text.count('list="symbol-choices"') == 3  # analiz + emir + bracket


def test_market_regime_widget(client):
    """Katman 9 piyasa geneli rejim göstergesi ve info düğmesi bulunmalı."""
    r = client.get("/")
    assert 'id="market-regime"' in r.text
    assert 'data-info="regime"' in r.text


def test_order_market_type_ui(client):
    """Emir formu piyasa türü seçici içermeli; açık emirler tablosu Piyasa kolonu göstermeli."""
    r = client.get("/")
    assert 'id="order-market-type"' in r.text
    assert '<option value="margin">Margin</option>' in r.text
    assert '<option value="futures">Futures</option>' in r.text
    assert "<th>Piyasa</th>" in r.text
    js = client.get("/static/js/app.js").text
    # emir gönderiminde ve açık emir render'ında market_type kullanılmalı
    assert 'order-market-type' in js
    assert "market-badge" in js
    # Akıllı Paket (bracket) da piyasa türü seçici içermeli
    assert 'id="bracket-market-type"' in r.text
    assert 'bracket-market-type' in js


def test_api_helpers_are_resilient(client):
    """
    Hata #9 regresyon testi: apiGet/apiSend fetch veya JSON hatasında
    throw etmemeli, envelope {success:false} döndürmeli; böylece tek bir
    başarısız çağrı tüm dashboard'ı 'Yükleniyor'da kilitlemez.
    """
    js = client.get("/static/js/app.js").text
    # apiGet ve apiSend try/catch ile sarılı olmalı ve hata envelope'u döndürmeli
    assert js.count("success: false, data: {}, error:") >= 2
    # refreshDashboard widget'ları izole (allSettled) çalıştırmalı
    assert "Promise.allSettled" in js
    # mini-watchlist başarısızlıkta açık mesaj göstermeli (Yükleniyor'da kalmamalı)
    assert "İzleme listesi yüklenemedi" in js


def test_analysis_view_chart_and_levels(client):
    """Analiz görünümünde piyasa türü seçici, grafik alanı, trade-setup seviyeleri ve sub-15m olmalı."""
    r = client.get("/")
    assert 'id="analysis-market-type"' in r.text
    assert 'value="futures"' in r.text
    assert 'value="margin"' in r.text
    assert 'id="analysis-candle-chart"' in r.text
    assert 'id="analysis-setup-content"' in r.text
    assert 'id="analysis-to-bracket-btn"' in r.text
    assert '<option value="1m">1m</option>' in r.text
    assert '<option value="5m">5m</option>' in r.text

