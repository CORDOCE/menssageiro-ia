"""Schemas Pydantic de contatos (spec 0002).

A normalização E.164 vive no schema: telefone inválido vira 422 (AC-2) e o valor guardado já é
o canônico de dedup (ADR 0006). Consentimento não é definido na criação — nasce ``False`` e é
registrado pelo endpoint dedicado (AC-8).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.telefone import normalizar_e164


class ContatoCreate(BaseModel):
    nome: str
    telefone: str
    grupo: str | None = None
    tags: list[str] = Field(default_factory=list)
    observacoes: str | None = None

    @field_validator("nome")
    @classmethod
    def _nome_obrigatorio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("nome é obrigatório")
        return v

    @field_validator("telefone")
    @classmethod
    def _telefone_canonico(cls, v: str) -> str:
        return normalizar_e164(v)


class ContatoUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    grupo: str | None = None
    tags: list[str] | None = None
    observacoes: str | None = None

    @field_validator("nome")
    @classmethod
    def _nome_obrigatorio(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("nome é obrigatório")
        return v

    @field_validator("telefone")
    @classmethod
    def _telefone_canonico(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalizar_e164(v)


class ContatoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    telefone_e164: str
    grupo: str | None
    tags: list[str]
    consentimento: bool
    consentimento_data: datetime | None
    consentimento_origem: str | None
    descadastrado_em: datetime | None
    ultima_mensagem_recebida_em: datetime | None
    observacoes: str | None
    criado_em: datetime | None = None
    atualizado_em: datetime | None = None


class ContatoLista(BaseModel):
    items: list[ContatoRead]
    total: int
    limit: int
    offset: int


class RegistrarConsentimento(BaseModel):
    """Opt-in deliberado (§5.9): origem (texto livre) + data não futura."""

    origem: str
    data: date

    @field_validator("origem")
    @classmethod
    def _origem_obrigatoria(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("origem é obrigatória")
        return v

    @field_validator("data")
    @classmethod
    def _nao_futura(cls, v: date) -> date:
        if v > datetime.now(UTC).date():
            raise ValueError("data de consentimento não pode ser futura")
        return v
