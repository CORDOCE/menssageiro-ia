"""Rotas de autenticação (ADR 0001) + sessão multi-dispositivo (ADR 0004).

Task 5: login **só com senha**, logout e `/me` (rota protegida). O 2FA (TOTP) é a task 6 e o rate
limit é a task 7. Falha de credencial retorna resposta genérica (anti-enumeração, CLAUDE.md §6).
Multi-dispositivo: o login não revoga sessões anteriores; `logout` encerra só o dispositivo atual e
`logout-todos` encerra todos.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import pyotp
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.core.auth_deps import sessao_atual, usuario_atual
from app.core.config import get_settings
from app.core.security import decifrar_segredo, gerar_token_sessao, hash_password, verify_password
from app.db.database import get_db
from app.models.auditoria import Auditoria
from app.models.usuario import SessaoUsuario, Usuario
from app.schemas.auth import LoginRequest, LoginResponse, UsuarioRead

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie de sessão (ADR 0012): HttpOnly/Secure/SameSite=Strict, first-party via proxy same-origin.
_COOKIE_SESSAO = "sessao"


def _set_cookie_sessao(response: Response, token: str) -> None:
    response.set_cookie(
        key=_COOKIE_SESSAO,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
        max_age=get_settings().session_max_dias * 86400,
    )


def _limpar_cookie_sessao(response: Response) -> None:
    response.delete_cookie(key=_COOKIE_SESSAO, path="/")

# Hash fictício para igualar o custo de tempo quando o e-mail não existe (spec: casos de borda,
# "mesmo custo de tempo"): sempre rodamos scrypt, exista o usuário ou não (anti-enumeração por timing).
_HASH_FICTICIO = hash_password(secrets.token_urlsafe(16))


def _totp_confere(usuario: Usuario | None, codigo: str | None) -> bool:
    """Valida o código TOTP (task 6). Tolera ±1 passo de 30 s (drift, spec: casos de borda).
    Retorna False se não há usuário, segredo TOTP ou código — sem revelar qual faltou."""
    if usuario is None or not usuario.totp_secret or not codigo:
        return False
    # O segredo repousa cifrado (ADR 0011); decifra antes de validar o código.
    segredo = decifrar_segredo(usuario.totp_secret)
    return pyotp.TOTP(segredo).verify(codigo, valid_window=1)


def _bloqueado_por_rate_limit(db: Session, email: str, agora: datetime) -> bool:
    """True se houve falhas de login demais para este e-mail dentro da janela (task 7, §6).
    Conta `login_falha` na auditoria (ator_email + criado_em indexados)."""
    cfg = get_settings()
    desde = agora - timedelta(minutes=cfg.login_janela_min)
    falhas = db.execute(
        select(func.count())
        .select_from(Auditoria)
        .where(
            Auditoria.operacao == "login_falha",
            Auditoria.ator_email == email,
            Auditoria.criado_em >= desde,
        )
    ).scalar_one()
    return falhas >= cfg.login_max_tentativas


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    user_agent: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> LoginResponse:
    agora = datetime.now(UTC)
    # Rate limit (task 7): bloqueia ANTES do scrypt para conter brute-force (ex.: chute de TOTP).
    if _bloqueado_por_rate_limit(db, payload.email, agora):
        registrar_auditoria(operacao="login_bloqueado", ator_email=payload.email, status="failure")
        raise HTTPException(status_code=429, detail="Muitas tentativas de login. Tente novamente mais tarde.")

    usuario = db.execute(select(Usuario).where(Usuario.email == payload.email)).scalar_one_or_none()

    # Resposta genérica + tempo constante: não revela se o e-mail/senha/TOTP falhou (anti-enumeração, §6).
    # Senha e TOTP são sempre avaliados juntos; qualquer falha dá o mesmo 401 genérico.
    hash_referencia = usuario.senha_hash if usuario is not None else _HASH_FICTICIO
    senha_confere = verify_password(payload.senha, hash_referencia)
    totp_confere = _totp_confere(usuario, payload.totp)
    if usuario is None or not senha_confere or not totp_confere:
        registrar_auditoria(operacao="login_falha", ator_email=payload.email, status="failure")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário desativado")

    # Multi-dispositivo (ADR 0004): NÃO revoga as sessões anteriores — cada dispositivo tem a sua.
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

    _set_cookie_sessao(response, token)  # sessão via cookie HttpOnly (ADR 0012)
    registrar_auditoria(operacao="login", ator_email=usuario.email, alvo_tipo="usuario", alvo_id=usuario.id)
    # `token` ainda no corpo durante a transição (frontend migra p/ cookie); removê-lo é follow-up.
    return LoginResponse(token=token, nome=usuario.nome, email=usuario.email)


@router.post("/logout")
def logout(
    response: Response,
    sessao: SessaoUsuario = Depends(sessao_atual),
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Encerra apenas a sessão do dispositivo atual (ADR 0004)."""
    sessao.revogada = True
    db.commit()
    _limpar_cookie_sessao(response)
    registrar_auditoria(operacao="logout", ator_email=usuario.email, alvo_tipo="usuario", alvo_id=usuario.id)
    return {"ok": True}


@router.post("/logout-todos")
def logout_todos(
    response: Response,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Encerra todas as sessões do usuário, em todos os dispositivos (ADR 0004)."""
    _limpar_cookie_sessao(response)
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
