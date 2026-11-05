"""Cifra do `totp_secret` em repouso (spec 0007 / ADR 0011).

Cobre os AC de cifra isolada; AC-2/AC-3 (login 2FA com segredo cifrado) ficam em `test_auth.py`,
e AC-4/AC-7 (migração) no ciclo Alembic do CI.
"""

import logging
import os

import pyotp
import pytest
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings
from app.core.security import _BASE32, cifrar_segredo, decifrar_segredo


def test_round_trip_e_valor_nao_e_base32():
    """AC-1: o valor cifrado difere do original, não parece base32, e decifra de volta."""
    segredo = pyotp.random_base32()
    cifra = cifrar_segredo(segredo)
    assert cifra != segredo
    assert not _BASE32.match(cifra)  # token Fernet (base64url) não é base32
    assert decifrar_segredo(cifra) == segredo


def test_chave_ausente_levanta():
    """AC-5: sem TOTP_ENC_KEY, cifrar/decifrar levantam — nunca caem em texto puro."""
    original = os.environ.pop("TOTP_ENC_KEY", None)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            cifrar_segredo("ABC")
        with pytest.raises(RuntimeError):
            decifrar_segredo("gAAAAAqualquer")
    finally:
        if original is not None:
            os.environ["TOTP_ENC_KEY"] = original
        get_settings.cache_clear()


def test_rotacao_multifernet():
    """AC-6: decifra token da chave velha; novo cifrado usa a nova (primeira)."""
    k_velha = Fernet.generate_key()
    k_nova = Fernet.generate_key()
    segredo = pyotp.random_base32()
    token_velho = MultiFernet([Fernet(k_velha)]).encrypt(segredo.encode()).decode()

    original = os.environ.get("TOTP_ENC_KEY")
    os.environ["TOTP_ENC_KEY"] = f"{k_nova.decode()},{k_velha.decode()}"
    get_settings.cache_clear()
    try:
        assert decifrar_segredo(token_velho) == segredo  # decifra com a velha
        novo = cifrar_segredo(segredo)
        assert Fernet(k_nova).decrypt(novo.encode()).decode() == segredo  # cifrou com a nova
    finally:
        if original is not None:
            os.environ["TOTP_ENC_KEY"] = original
        else:
            os.environ.pop("TOTP_ENC_KEY", None)
        get_settings.cache_clear()


def test_legado_em_claro_tolerado(caplog):
    """Tolerância de corte (ADR 0011): segredo legado em claro decifra como ele mesmo, com WARN."""
    segredo = pyotp.random_base32()
    with caplog.at_level(logging.WARNING):
        assert decifrar_segredo(segredo) == segredo
    assert any("legado" in r.message for r in caplog.records)


def test_token_adulterado_levanta():
    """Token Fernet adulterado (HMAC inválido) e não-base32 → InvalidToken (não autentica)."""
    cifra = cifrar_segredo(pyotp.random_base32())
    adulterado = cifra[:-6] + ("aaaaaa" if not cifra.endswith("aaaaaa") else "bbbbbb")
    with pytest.raises(InvalidToken):
        decifrar_segredo(adulterado)
