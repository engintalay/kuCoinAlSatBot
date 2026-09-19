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
