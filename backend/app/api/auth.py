"""Rotas de autenticação (ADR 0001) + sessão multi-dispositivo (ADR 0004).

Task 5: login **só com senha**, logout e `/me` (rota protegida). O 2FA (TOTP) é a task 6 e o rate
limit é a task 7. Falha de credencial retorna resposta genérica (anti-enumeração, CLAUDE.md §6).
Multi-dispositivo: o login não revoga sessões anteriores; `logout` encerra só o dispositivo atual e
`logout-todos` encerra todos.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.core.auth_deps import sessao_atual, usuario_atual
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
def login(
    payload: LoginRequest,
    user_agent: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> LoginResponse:
    usuario = db.execute(select(Usuario).where(Usuario.email == payload.email)).scalar_one_or_none()

    # Resposta genérica + tempo constante: não revela se o e-mail existe (anti-enumeração, §6).
    hash_referencia = usuario.senha_hash if usuario is not None else _HASH_FICTICIO
    senha_confere = verify_password(payload.senha, hash_referencia)
    if usuario is None or not senha_confere:
        registrar_auditoria(operacao="login_falha", ator_email=payload.email, status="failure")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário desativado")

    # Multi-dispositivo (ADR 0004): NÃO revoga as sessões anteriores — cada dispositivo tem a sua.
    agora = datetime.now(UTC)
    token = gerar_token_sessao()
    db.add(
        SessaoUsuario(
            id=str(uuid.uuid4()),
            usuario_id=usuario.id,
            token=token,
            criada_em=agora,
            expira_em=agora + timedelta(days=get_settings().session_inatividade_dias),
            ultimo_uso_em=agora,
            user_agent=user_agent[:255] if user_agent else None,
        )
    )
    db.commit()

    registrar_auditoria(operacao="login", ator_email=usuario.email, alvo_tipo="usuario", alvo_id=usuario.id)
    return LoginResponse(token=token, nome=usuario.nome, email=usuario.email)


@router.post("/logout")
def logout(
    sessao: SessaoUsuario = Depends(sessao_atual),
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Encerra apenas a sessão do dispositivo atual (ADR 0004)."""
    sessao.revogada = True
    db.commit()
    registrar_auditoria(operacao="logout", ator_email=usuario.email, alvo_tipo="usuario", alvo_id=usuario.id)
    return {"ok": True}


@router.post("/logout-todos")
def logout_todos(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Encerra todas as sessões do usuário, em todos os dispositivos (ADR 0004)."""
    db.execute(
        update(SessaoUsuario)
        .where(SessaoUsuario.usuario_id == usuario.id, SessaoUsuario.revogada.is_(False))
        .values(revogada=True)
    )
    db.commit()
    registrar_auditoria(
        operacao="logout_todos", ator_email=usuario.email, alvo_tipo="usuario", alvo_id=usuario.id
    )
    return {"ok": True}


@router.get("/me", response_model=UsuarioRead)
def me(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    return usuario
