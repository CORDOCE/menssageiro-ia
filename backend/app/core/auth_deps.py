"""Dependências de autenticação (ADR 0001): sessão = token Bearer validado no banco."""

from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.usuario import SessaoUsuario, Usuario


def usuario_atual(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    """Resolve o usuário da sessão a partir de `Authorization: Bearer <token>`; 401 se inválida."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Não autenticado")
    token = authorization.removeprefix("Bearer ")

    sessao = db.execute(
        select(SessaoUsuario).where(
            SessaoUsuario.token == token,
            SessaoUsuario.revogada.is_(False),
            SessaoUsuario.expira_em > datetime.now(UTC),
        )
    ).scalar_one_or_none()
    if sessao is None:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")

    usuario = db.get(Usuario, sessao.usuario_id)
    if usuario is None or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Usuário inválido")
    return usuario
