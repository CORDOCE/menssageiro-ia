"""Schemas Pydantic do fluxo de autenticação."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    senha: str


class LoginResponse(BaseModel):
    token: str
    nome: str
    email: str


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    email: str
    ativo: bool
    criado_em: datetime | None = None
