"""
Faz 1 — auth_service (bcrypt şifre + pyotp TOTP) testleri.
"""

import pyotp

from src.auth import auth_service as A


class TestPassword:
    def test_hash_and_verify(self):
        h = A.hash_password("SuperGizli!123")
        assert h != "SuperGizli!123"           # hash, düz metin değil
        assert A.verify_password("SuperGizli!123", h) is True

    def test_wrong_password(self):
        h = A.hash_password("dogru")
        assert A.verify_password("yanlis", h) is False

    def test_verify_invalid_hash(self):
        assert A.verify_password("x", "gecersiz-hash") is False

    def test_hash_unique_salt(self):
        # Aynı şifre iki kez hash'lense de farklı (salt) olmalı
        assert A.hash_password("aynı") != A.hash_password("aynı")


class TestTOTP:
    def test_secret_and_verify(self):
        secret = A.generate_totp_secret()
        code = pyotp.TOTP(secret).now()
        assert A.verify_totp(secret, code) is True

    def test_wrong_code(self):
        secret = A.generate_totp_secret()
        assert A.verify_totp(secret, "000000") is False

    def test_empty_inputs(self):
        assert A.verify_totp("", "123456") is False
        assert A.verify_totp(A.generate_totp_secret(), "") is False

    def test_provisioning_uri(self):
        secret = A.generate_totp_secret()
        uri = A.totp_provisioning_uri(secret, "admin")
        assert uri.startswith("otpauth://totp/")
        assert "KuCoinAlSatBot" in uri
        assert secret in uri
