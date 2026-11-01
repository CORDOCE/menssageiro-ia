"""Dependências de autenticação (ADR 0001): sessão = token Bearer validado no banco.

Sessão multi-dispositivo (ADR 0004): várias sessões simultâneas por usuário (o login não
revoga as outras); renovação deslizante por inatividade com throttle e teto absoluto.
"""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.models.usuario import SessaoUsuario, Usuario


def sessao_atual(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> SessaoUsuario:
    """Resolve a sessão do `Authorization: Bearer <token>`, aplicando janela deslizante e
    teto absoluto; 401 se ausente, inválida, expirada por inatividade ou além do teto."""
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

    cfg = get_settings()
    agora = datetime.now(UTC)

    # Teto absoluto: vence a renovação deslizante (ADR 0004).
    if sessao.criada_em + timedelta(days=cfg.session_max_dias) <= agora:
        sessao.revogada = True
        db.commit()
        raise HTTPException(status_code=401, detail="Sessão expirada")

    # Renovação deslizante com throttle (não grava a cada requisição).
    if agora - sessao.ultimo_uso_em >= timedelta(minutes=cfg.session_throttle_min):
        sessao.ultimo_uso_em = agora
        sessao.expira_em = agora + timedelta(days=cfg.session_inatividade_dias)
        db.commit()

    return sessao


def usuario_atual(
    sessao: SessaoUsuario = Depends(sessao_atual),
    db: Session = Depends(get_db),
) -> Usuario:
    """Usuário dono da sessão atual; 401 se o usuário sumiu ou foi desativado."""
    usuario = db.get(Usuario, sessao.usuario_id)
    if usuario is None or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Usuário inválido")
    return usuario
