"""Hashing de senha (scrypt, stdlib), geração de token de sessão e cifra de segredos em repouso.

Herdado do projeto antigo (`document-ai-system`) e endurecido (CLAUDE.md §6):
comparação em tempo constante com `hmac.compare_digest` e token via `secrets`.
Cifra em repouso (ADR 0011 / spec 0007): Fernet na aplicação; a chave vive em `TOTP_ENC_KEY`,
nunca no banco nem no SQL.
"""

import hashlib
import hmac
import logging
import os
import re
import secrets

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Parâmetros scrypt (mantidos do projeto antigo).
_N, _R, _P = 16384, 8, 1

# Segredo TOTP legado em claro é base32 (A–Z, 2–7, com padding opcional); usado só na janela de corte.
_BASE32 = re.compile(r"[A-Z2-7]+=*\Z")


def _multifernet() -> MultiFernet:
    """Monta o MultiFernet a partir de `TOTP_ENC_KEY` (lazy: lido no uso, não no import).
    Chave ausente → erro explícito (nunca cai em texto puro)."""
    chaves_raw = get_settings().totp_enc_key
    chaves = [c.strip().encode() for c in (chaves_raw or "").split(",") if c.strip()]
    if not chaves:
        raise RuntimeError("TOTP_ENC_KEY não configurada: cifra de segredo indisponível (ADR 0011).")
    return MultiFernet([Fernet(c) for c in chaves])


def cifrar_segredo(claro: str) -> str:
    """Cifra um segredo para repouso; a primeira chave de `TOTP_ENC_KEY` é a ativa."""
    return _multifernet().encrypt(claro.encode()).decode()


def decifrar_segredo(cifra: str) -> str:
    """Decifra um segredo cifrado. Tolera **uma vez** valor legado em claro (base32) na janela de
    corte (ADR 0011) — removido em follow-up. Token adulterado/ininteligível → levanta."""
    try:
        return _multifernet().decrypt(cifra.encode()).decode()
    except InvalidToken:
        if _BASE32.match(cifra):
            logger.warning("totp_secret legado em claro aceito (migração de cifra pendente)")
            return cifra
        raise


def hash_password(senha: str) -> str:
    """Gera `saltHex:derivadaHex` com salt aleatório por senha."""
    salt = os.urandom(16)
    dk = hashlib.scrypt(senha.encode(), salt=salt, n=_N, r=_R, p=_P)
    return salt.hex() + ":" + dk.hex()


def verify_password(senha: str, hashed: str) -> bool:
    """Confere a senha em tempo constante; qualquer hash malformado retorna False."""
    try:
        salt_hex, dk_hex = hashed.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(senha.encode(), salt=salt, n=_N, r=_R, p=_P)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


def gerar_token_sessao() -> str:
    """Token opaco de sessão, aleatório e URL-safe (~43 chars a partir de 32 bytes)."""
    return secrets.token_urlsafe(32)
