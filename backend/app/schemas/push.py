"""Schemas de Web Push (spec 0023).

Inscrição validada: `endpoint` deve ser https e limitado em tamanho (hardening §6, anti-SSRF/abuso).
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class ChavePublica(BaseModel):
    chave: str | None


class InscricaoKeys(BaseModel):
    p256dh: str
    auth: str


class InscricaoEntrada(BaseModel):
    endpoint: str
    keys: InscricaoKeys

    @field_validator("endpoint")
    @classmethod
    def _endpoint_https(cls, v: str) -> str:
        # Só https e tamanho limitado — o endpoint é usado como alvo de requisição (anti-SSRF/abuso).
        if not v.startswith("https://") or len(v) > 1024:
            raise ValueError("endpoint inválido")
        return v
