"""Hashing de senha (scrypt, stdlib) e geração de token de sessão.

Herdado do projeto antigo (`document-ai-system`) e endurecido (CLAUDE.md §6):
comparação em tempo constante com `hmac.compare_digest` e token via `secrets`.
"""

import hashlib
import hmac
import os
import secrets

# Parâmetros scrypt (mantidos do projeto antigo).
_N, _R, _P = 16384, 8, 1


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
