"""Schemas Pydantic do fluxo de autenticação."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    senha: str
    # 2FA TOTP (task 6). Opcional no schema para que "código ausente" caia na resposta genérica
    # 401 (AC-6), e não num 422 de validação que revelaria o motivo.
    totp: str | None = None


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
