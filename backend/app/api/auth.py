"""Rotas de autenticação (ADR 0001).

Task 5: login **só com senha**, logout e `/me` (rota protegida). O 2FA (TOTP) é a task 6 e o rate
limit é a task 7. Falha de credencial retorna resposta genérica (anti-enumeração, CLAUDE.md §6).
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.core.auth_deps import usuario_atual
from app.core.config import get_settings
from app.core.security import gerar_token_sessao, hash_password, verify_password
from app.db.database import get_db
from app.models.usuario import SessaoUsuario, Usuario
from app.schemas.auth import LoginRequest, LoginResponse, UsuarioRead

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash fictício para igualar o custo de tempo quando o e-mail não existe (spec: casos de borda,
# "mesmo custo de tempo"): sempre rodamos scrypt, exista o usuário ou não (anti-enumeração por timing).
_HASH_FICTICIO = hash_password(secrets.token_urlsafe(16))


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    usuario = db.execute(select(Usuario).where(Usuario.email == payload.email)).scalar_one_or_none()

    # Resposta genérica + tempo constante: não revela se o e-mail existe (anti-enumeração, §6).
    hash_referencia = usuario.senha_hash if usuario is not None else _HASH_FICTICIO
    senha_confere = verify_password(payload.senha, hash_referencia)
    if usuario is None or not senha_confere:
        registrar_auditoria(operacao="login_falha", ator_email=payload.email, status="failure")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário desativado")

    # 1 sessão ativa por usuário: revoga as anteriores antes de emitir a nova.
    db.execute(
        update(SessaoUsuario)
        .where(SessaoUsuario.usuario_id == usuario.id, SessaoUsuario.revogada.is_(False))
        .values(revogada=True)
    )

    token = gerar_token_sessao()
    db.add(
        SessaoUsuario(
            id=str(uuid.uuid4()),
            usuario_id=usuario.id,
            token=token,
            expira_em=datetime.now(UTC) + timedelta(hours=get_settings().session_horas),
        )
    )
    db.commit()

    registrar_auditoria(operacao="login", ator_email=usuario.email, alvo_tipo="usuario", alvo_id=usuario.id)
    return LoginResponse(token=token, nome=usuario.nome, email=usuario.email)


@router.post("/logout")
def logout(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)) -> dict[str, bool]:
    db.execute(
        update(SessaoUsuario)
        .where(SessaoUsuario.usuario_id == usuario.id, SessaoUsuario.revogada.is_(False))
        .values(revogada=True)
    )
    db.commit()
    registrar_auditoria(operacao="logout", ator_email=usuario.email, alvo_tipo="usuario", alvo_id=usuario.id)
    return {"ok": True}


@router.get("/me", response_model=UsuarioRead)
def me(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    return usuario
