"""
Faz 1 — CryptoVault (master key şifreleme) testleri.
"""

import pytest

from src.auth.crypto_vault import CryptoVault


def _vault():
    # Testte deterministik: açıkça üretilmiş bir key ver
    return CryptoVault(master_key=CryptoVault.generate_key())


class TestCryptoVault:
    def test_encrypt_decrypt_roundtrip(self):
        v = _vault()
        secret = "my-kucoin-api-secret-123"
        token = v.encrypt(secret)
        assert token != secret  # şifreli, düz metin değil
        assert v.decrypt(token) == secret

    def test_empty_string(self):
        v = _vault()
        assert v.decrypt(v.encrypt("")) == ""

    def test_wrong_key_fails(self):
        v1 = _vault()
        v2 = _vault()  # farklı key
        token = v1.encrypt("gizli")
        with pytest.raises(ValueError):
            v2.decrypt(token)

    def test_invalid_token_raises(self):
        v = _vault()
        with pytest.raises(ValueError):
            v.decrypt("bu-gecerli-bir-token-degil")

    def test_generate_key_unique(self):
        assert CryptoVault.generate_key() != CryptoVault.generate_key()

    def test_env_master_key_used(self, monkeypatch):
        """MASTER_KEY ortam değişkeni verildiğinde iki vault aynı key'i kullanır."""
        key = CryptoVault.generate_key()
        monkeypatch.setenv("MASTER_KEY", key)
        v1 = CryptoVault()
        v2 = CryptoVault()
        token = v1.encrypt("paylasimli")
        assert v2.decrypt(token) == "paylasimli"
