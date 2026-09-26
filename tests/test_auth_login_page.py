"""
Faz 1 — Giriş ekranı (login.html + /login route + dashboard auth öğeleri) testleri.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.main import app
    app.state.auth_enabled = False
    return TestClient(app)


def test_login_page_served(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "login-form" in r.text
    assert 'id="login-username"' in r.text
    assert 'id="login-totp"' in r.text  # 2FA alanı


def test_login_js_served(client):
    r = client.get("/static/js/login.js")
    assert r.status_code == 200
    assert "/api/v1/auth/login" in r.text


def test_dashboard_has_user_and_logout(client):
    r = client.get("/")
    assert 'id="current-user"' in r.text
    assert 'id="logout-btn"' in r.text


def test_app_js_has_auth_flow(client):
    js = client.get("/static/js/app.js").text
    assert "checkAuthAndInit" in js
    assert "/api/v1/auth/me" in js
    assert "_handleUnauthorized" in js
    assert "/login" in js
