"""Testes de autenticação (spec 0001): AC-5/AC-6 (2FA TOTP), AC-7 (rota protegida)
e sessão multi-dispositivo (AC-13..AC-16, ADR 0004)."""

import time
import uuid
from datetime import UTC, datetime, timedelta

import pyotp

import app.db.database as db_mod
from app.core.audit import registrar_auditoria
from app.core.security import (
    cifrar_segredo,
    decifrar_segredo,
    gerar_token_sessao,
    hash_password,
    verify_password,
)
from app.models.auditoria import Auditoria
from app.models.usuario import SessaoUsuario, Usuario

EMAIL = "admin@exemplo.com"
SENHA = "senha-super-secreta"
TOTP_SECRET = pyotp.random_base32()

_SEM_TOTP = object()  # sentinela: "envie o código atual" (default) vs None ("omita o campo")


def _codigo_totp(secret: str = TOTP_SECRET) -> str:
    return pyotp.TOTP(secret).now()


def _criar_usuario(
    email: str = EMAIL, senha: str = SENHA, ativo: bool = True, totp_secret: str = TOTP_SECRET
) -> None:
    sessao = db_mod.SessionLocal()
    try:
        sessao.add(
            Usuario(
                id=str(uuid.uuid4()),
                nome="Admin",
                email=email,
                senha_hash=hash_password(senha),
                ativo=ativo,
                totp_secret=cifrar_segredo(totp_secret),  # repouso cifrado (ADR 0011)
            )
        )
        sessao.commit()
    finally:
        sessao.close()


def _post_login(
    client,
    *,
    email: str = EMAIL,
    senha: str = SENHA,
    totp: object = _SEM_TOTP,
    headers: dict[str, str] | None = None,
):
    body: dict[str, str] = {"email": email, "senha": senha}
    if totp is _SEM_TOTP:
        body["totp"] = _codigo_totp()
    elif isinstance(totp, str):
        body["totp"] = totp
    # totp is None → omite o campo (simula código ausente, AC-6)
    return client.post("/auth/login", json=body, headers=headers or {})


def _login(client) -> str:
    return _post_login(client).json()["token"]


def _ajustar_sessao(token: str, **campos: object) -> None:
    """Edita colunas da sessão direto no banco (para simular inatividade/idade)."""
    sessao = db_mod.SessionLocal()
    try:
        s = sessao.query(SessaoUsuario).filter_by(token=token).one()
        for chave, valor in campos.items():
            setattr(s, chave, valor)
        sessao.commit()
    finally:
        sessao.close()


# --- Rota protegida (AC-7) ------------------------------------------------------------------------

def test_rota_protegida_sem_token_401(client, db):
    assert client.get("/auth/me").status_code == 401


def test_rota_protegida_token_invalido_401(client, db):
    r = client.get("/auth/me", headers={"Authorization": "Bearer nao-existe"})
    assert r.status_code == 401


def test_login_valido_emite_token_e_acessa_rota_protegida(client, db):
    # AC-7: login válido (senha + TOTP) → credencial → rota protegida 200
    _criar_usuario()
    token = _login(client)
    r2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == EMAIL


# --- Matriz de decisão do login: senha × TOTP (AC-5, AC-6) ----------------------------------------

def test_login_senha_e_totp_validos_200(client, db):
    # AC-5: senha correta + TOTP válido → 200 com credencial.
    _criar_usuario()
    r = _post_login(client)
    assert r.status_code == 200
    assert "token" in r.json()


def test_login_totp_ausente_401_generico(client, db):
    # AC-6: senha correta + TOTP ausente → 401 genérico, sem credencial.
    _criar_usuario()
    r = _post_login(client, totp=None)
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciais inválidas"


def test_login_totp_invalido_401_generico(client, db):
    # AC-6: senha correta + TOTP inválido → 401 genérico.
    _criar_usuario()
    r = _post_login(client, totp="000000")
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciais inválidas"


def test_login_senha_errada_totp_valido_401_generico(client, db):
    # Matriz: senha incorreta (+ TOTP válido) → mesmo 401 genérico (não revela que a senha falhou).
    _criar_usuario()
    r = _post_login(client, senha="errada")
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciais inválidas"


def test_login_usuario_inexistente_401_generico(client, db):
    # Matriz: usuário inexistente → mesma resposta genérica (anti-enumeração).
    r = _post_login(client, email="ninguem@exemplo.com", senha="x", totp="000000")
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciais inválidas"


def test_login_totp_drift_passo_anterior_aceito(client, db):
    # Borda: código do passo imediatamente anterior (drift de 30s) é aceito (valid_window=1).
    _criar_usuario()
    # Evita a borda do passo de 30s: se o verify cruzar o limite, o "passo anterior" viraria
    # 2 passos atrás e seria rejeitado (teste flaky). Com margem, o passo anterior é estável.
    if datetime.now(UTC).second % 30 > 27:
        time.sleep(3)
    codigo_anterior = pyotp.TOTP(TOTP_SECRET).at(datetime.now(UTC) - timedelta(seconds=30))
    r = _post_login(client, totp=codigo_anterior)
    assert r.status_code == 200


def test_login_usuario_inativo_403(client, db):
    # Credenciais válidas mas usuário inativo → 403.
    _criar_usuario(ativo=False)
    r = _post_login(client)
    assert r.status_code == 403


# --- Hash / token / auditoria ---------------------------------------------------------------------

def test_senha_guardada_com_hash_nao_texto_plano(client, db):
    _criar_usuario()
    sessao = db_mod.SessionLocal()
    try:
        u = sessao.query(Usuario).filter_by(email=EMAIL).one()
        assert u.senha_hash != SENHA
        assert ":" in u.senha_hash  # formato salt:derivada
    finally:
        sessao.close()


def test_totp_secret_guardado_cifrado_nao_texto_plano(client, db):
    """AC-1: o segredo TOTP repousa cifrado (token Fernet), decifrável para o original."""
    _criar_usuario()
    sessao = db_mod.SessionLocal()
    try:
        u = sessao.query(Usuario).filter_by(email=EMAIL).one()
        assert u.totp_secret != TOTP_SECRET
        assert decifrar_segredo(u.totp_secret) == TOTP_SECRET
    finally:
        sessao.close()


# --- Sessão em cookie HttpOnly (spec 0008 / ADR 0012) ---------------------------------------------
def test_login_seta_cookie_sessao_seguro(client, db):
    """AC-1: login emite Set-Cookie `sessao` com HttpOnly/Secure/SameSite=Strict/Path=/."""
    _criar_usuario()
    r = _post_login(client)
    assert r.status_code == 200
    sc = r.headers.get("set-cookie", "").lower()
    assert "sessao=" in sc
    assert "httponly" in sc
    assert "secure" in sc
    assert "samesite=strict" in sc
    assert "path=/" in sc


def test_rota_protegida_via_cookie_sem_authorization(client, db):
    """AC-2: cookie `sessao` autentica a rota protegida sem header Authorization."""
    _criar_usuario()
    token = _post_login(client).json()["token"]
    r = client.get("/auth/me", headers={"Cookie": f"sessao={token}"})
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL


def test_cookie_tem_precedencia_sobre_bearer(client, db):
    """Caso de borda: com cookie válido e Bearer inválido, o cookie vence."""
    _criar_usuario()
    token = _post_login(client).json()["token"]
    r = client.get(
        "/auth/me",
        headers={"Cookie": f"sessao={token}", "Authorization": "Bearer invalido"},
    )
    assert r.status_code == 200


def test_logout_expira_cookie(client, db):
    """AC-4: logout expira o cookie `sessao` (Max-Age=0)."""
    _criar_usuario()
    token = _post_login(client).json()["token"]
    r = client.post("/auth/logout", headers={"Cookie": f"sessao={token}"})
    assert r.status_code == 200
    assert "max-age=0" in r.headers.get("set-cookie", "").lower()


def test_verify_password_hash_malformado_retorna_false():
    assert verify_password("x", "sem-dois-pontos") is False
    assert verify_password("x", "zz:zz") is False


def test_verify_password_correta_e_errada():
    h = hash_password("abc")
    assert verify_password("abc", h) is True
    assert verify_password("abcd", h) is False


def test_gerar_token_sessao_unico_e_nao_vazio():
    t1, t2 = gerar_token_sessao(), gerar_token_sessao()
    assert t1 != t2
    assert len(t1) >= 32


def test_auditoria_nunca_levanta(monkeypatch):
    # Borda: falha ao gravar auditoria não propaga (CLAUDE.md §5.8/§7)
    def _boom() -> object:
        raise RuntimeError("banco indisponível")

    monkeypatch.setattr(db_mod, "SessionLocal", _boom)
    registrar_auditoria(operacao="teste_falha")  # não deve levantar


# --- Sessão multi-dispositivo (ADR 0004) ----------------------------------------------------------

def test_logout_revoga_sessao(client, db):
    _criar_usuario()
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_login_multi_dispositivo_duas_sessoes_validas(client, db):
    # AC-13: o 2º login NÃO revoga o 1º — ambos os tokens continuam válidos.
    _criar_usuario()
    t1, t2 = _login(client), _login(client)
    assert t1 != t2
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t1}"}).status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t2}"}).status_code == 200


def test_sessao_persistida_no_banco(client, db):
    _criar_usuario()
    token = _login(client)
    sessao = db_mod.SessionLocal()
    try:
        s = sessao.query(SessaoUsuario).filter_by(token=token).one()
        assert s.revogada is False
    finally:
        sessao.close()


def test_sessao_valida_usuario_inativado_depois_401(client, db):
    # Borda: sessão válida, mas usuário desativado após o login → 401 (auth_deps)
    _criar_usuario()
    token = _login(client)
    sessao = db_mod.SessionLocal()
    try:
        u = sessao.query(Usuario).filter_by(email=EMAIL).one()
        u.ativo = False
        sessao.commit()
    finally:
        sessao.close()
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_isola_dispositivo_atual(client, db):
    # AC-14: logout revoga só a sessão do token usado; a outra continua válida.
    _criar_usuario()
    t1, t2 = _login(client), _login(client)
    assert client.post("/auth/logout", headers={"Authorization": f"Bearer {t1}"}).status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t1}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t2}"}).status_code == 200


def test_logout_todos_revoga_todas_as_sessoes(client, db):
    # AC-14: logout-todos derruba todas as sessões do usuário.
    _criar_usuario()
    t1, t2 = _login(client), _login(client)
    r = client.post("/auth/logout-todos", headers={"Authorization": f"Bearer {t1}"})
    assert r.status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t1}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t2}"}).status_code == 401


def test_user_agent_persistido_na_sessao(client, db):
    # AC-16: o user_agent do dispositivo é gravado na sessão.
    _criar_usuario()
    token = _post_login(client, headers={"User-Agent": "MeuApp/1.0"}).json()["token"]
    sessao = db_mod.SessionLocal()
    try:
        s = sessao.query(SessaoUsuario).filter_by(token=token).one()
        assert s.user_agent == "MeuApp/1.0"
    finally:
        sessao.close()


def test_user_agent_longo_truncado_sem_erro(client, db):
    # Borda: User-Agent > 255 (controlável pelo cliente) não quebra o login; é truncado.
    _criar_usuario()
    r = _post_login(client, headers={"User-Agent": "A" * 500})
    assert r.status_code == 200
    sessao = db_mod.SessionLocal()
    try:
        s = sessao.query(SessaoUsuario).filter_by(token=r.json()["token"]).one()
        assert len(s.user_agent) == 255
    finally:
        sessao.close()


def test_sessao_expira_por_inatividade_401(client, db):
    # AC-15: expira_em no passado (inatividade além da janela) → 401.
    _criar_usuario()
    token = _login(client)
    _ajustar_sessao(token, expira_em=datetime.now(UTC) - timedelta(minutes=1))
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_teto_absoluto_401_mesmo_com_uso_recente(client, db):
    # AC-15: criada_em além do teto vence a renovação, mesmo com expira_em futuro.
    _criar_usuario()
    token = _login(client)
    _ajustar_sessao(
        token,
        criada_em=datetime.now(UTC) - timedelta(days=31),
        expira_em=datetime.now(UTC) + timedelta(days=1),
        ultimo_uso_em=datetime.now(UTC),
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_renovacao_desliza_expira_em(client, db):
    # AC-15: uso após o throttle renova expira_em para ~agora + inatividade.
    _criar_usuario()
    token = _login(client)
    _ajustar_sessao(
        token,
        ultimo_uso_em=datetime.now(UTC) - timedelta(hours=1),
        expira_em=datetime.now(UTC) + timedelta(minutes=10),
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    sessao = db_mod.SessionLocal()
    try:
        s = sessao.query(SessaoUsuario).filter_by(token=token).one()
        assert s.expira_em > datetime.now(UTC) + timedelta(days=6)
    finally:
        sessao.close()


# --- Rate limit do login (task 7, AC-8) -----------------------------------------------------------

def _inserir_falhas(email: str, n: int, minutos_atras: int = 0) -> None:
    """Grava N `login_falha` na auditoria (exercita o rate limit sem rodar N scrypt)."""
    sessao = db_mod.SessionLocal()
    try:
        quando = datetime.now(UTC) - timedelta(minutes=minutos_atras)
        for _ in range(n):
            sessao.add(
                Auditoria(
                    id=str(uuid.uuid4()),
                    operacao="login_falha",
                    ator_email=email,
                    status="failure",
                    criado_em=quando,
                )
            )
        sessao.commit()
    finally:
        sessao.close()


def test_rate_limit_apos_limite_de_falhas_429(client, db):
    # AC-8: excedido o limite de falhas (por e-mail) na janela → 429, mesmo com credenciais válidas.
    _criar_usuario()
    _inserir_falhas(EMAIL, n=5)  # login_max_tentativas (default) = 5
    assert _post_login(client).status_code == 429


def test_rate_limit_isolado_por_email(client, db):
    # AC-8: o bloqueio é por e-mail; outro e-mail não é afetado.
    _criar_usuario()
    _criar_usuario(email="outro@exemplo.com")
    _inserir_falhas(EMAIL, n=5)
    assert _post_login(client).status_code == 429
    assert _post_login(client, email="outro@exemplo.com").status_code == 200


def test_rate_limit_so_conta_falhas_dentro_da_janela(client, db):
    # Borda: falhas fora da janela (15 min) não contam (contador expira — spec: casos de borda).
    _criar_usuario()
    _inserir_falhas(EMAIL, n=5, minutos_atras=20)
    assert _post_login(client).status_code == 200
