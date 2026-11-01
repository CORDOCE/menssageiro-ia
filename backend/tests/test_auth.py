"""Testes de autenticação (spec 0001). Cobre AC-7 e as linhas da matriz de decisão aplicáveis
à task 5 (só senha; as linhas com TOTP são a task 6)."""

import uuid
from datetime import UTC, datetime, timedelta

import app.db.database as db_mod
from app.core.audit import registrar_auditoria
from app.core.security import gerar_token_sessao, hash_password, verify_password
from app.models.usuario import SessaoUsuario, Usuario

EMAIL = "admin@exemplo.com"
SENHA = "senha-super-secreta"


def _criar_usuario(email: str = EMAIL, senha: str = SENHA, ativo: bool = True) -> None:
    sessao = db_mod.SessionLocal()
    try:
        sessao.add(
            Usuario(
                id=str(uuid.uuid4()),
                nome="Admin",
                email=email,
                senha_hash=hash_password(senha),
                ativo=ativo,
            )
        )
        sessao.commit()
    finally:
        sessao.close()


def test_rota_protegida_sem_token_401(client, db):
    # AC-7: rota protegida sem credencial → 401
    assert client.get("/auth/me").status_code == 401


def test_rota_protegida_token_invalido_401(client, db):
    # AC-7: token inexistente → 401
    r = client.get("/auth/me", headers={"Authorization": "Bearer nao-existe"})
    assert r.status_code == 401


def test_login_valido_emite_token_e_acessa_rota_protegida(client, db):
    # AC-7: login válido → credencial → rota protegida 200
    _criar_usuario()
    r = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA})
    assert r.status_code == 200
    token = r.json()["token"]

    r2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == EMAIL


def test_login_senha_errada_401_generico(client, db):
    # Matriz: senha incorreta → 401 genérico
    _criar_usuario()
    r = client.post("/auth/login", json={"email": EMAIL, "senha": "errada"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciais inválidas"


def test_login_usuario_inexistente_401_generico(client, db):
    # Matriz: usuário inexistente → mesma resposta genérica (anti-enumeração)
    r = client.post("/auth/login", json={"email": "ninguem@exemplo.com", "senha": "x"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciais inválidas"


def test_login_usuario_inativo_403(client, db):
    _criar_usuario(ativo=False)
    r = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA})
    assert r.status_code == 403


def test_logout_revoga_sessao(client, db):
    _criar_usuario()
    token = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post("/auth/logout", headers=headers).status_code == 200
    # Após logout o token não vale mais
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_login_multi_dispositivo_duas_sessoes_validas(client, db):
    # AC-13 (ADR 0004): o 2º login NÃO revoga o 1º — ambos os tokens continuam válidos.
    _criar_usuario()
    t1 = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA}).json()["token"]
    t2 = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA}).json()["token"]
    assert t1 != t2
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t1}"}).status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t2}"}).status_code == 200


def test_senha_guardada_com_hash_nao_texto_plano(client, db):
    _criar_usuario()
    sessao = db_mod.SessionLocal()
    try:
        u = sessao.query(Usuario).filter_by(email=EMAIL).one()
        assert u.senha_hash != SENHA
        assert ":" in u.senha_hash  # formato salt:derivada
    finally:
        sessao.close()


def test_sessao_persistida_no_banco(client, db):
    _criar_usuario()
    token = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA}).json()["token"]
    sessao = db_mod.SessionLocal()
    try:
        s = sessao.query(SessaoUsuario).filter_by(token=token).one()
        assert s.revogada is False
    finally:
        sessao.close()


def test_sessao_valida_usuario_inativado_depois_401(client, db):
    # Borda: sessão válida, mas usuário desativado após o login → 401 (auth_deps)
    _criar_usuario()
    token = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA}).json()["token"]
    sessao = db_mod.SessionLocal()
    try:
        u = sessao.query(Usuario).filter_by(email=EMAIL).one()
        u.ativo = False
        sessao.commit()
    finally:
        sessao.close()
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_verify_password_hash_malformado_retorna_false():
    # Borda: hash sem ":" ou com hex inválido não deve quebrar
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


# --- Sessão multi-dispositivo (ADR 0004) ---------------------------------------------------------

def _login(client) -> str:
    return client.post("/auth/login", json={"email": EMAIL, "senha": SENHA}).json()["token"]


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
    token = client.post(
        "/auth/login", json={"email": EMAIL, "senha": SENHA}, headers={"User-Agent": "MeuApp/1.0"}
    ).json()["token"]
    sessao = db_mod.SessionLocal()
    try:
        s = sessao.query(SessaoUsuario).filter_by(token=token).one()
        assert s.user_agent == "MeuApp/1.0"
    finally:
        sessao.close()


def test_user_agent_longo_truncado_sem_erro(client, db):
    # Borda: User-Agent > 255 (controlável pelo cliente) não quebra o login; é truncado.
    _criar_usuario()
    r = client.post(
        "/auth/login", json={"email": EMAIL, "senha": SENHA}, headers={"User-Agent": "A" * 500}
    )
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
