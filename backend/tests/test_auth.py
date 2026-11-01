"""Testes de autenticação (spec 0001). Cobre AC-7 e as linhas da matriz de decisão aplicáveis
à task 5 (só senha; as linhas com TOTP são a task 6)."""

import uuid

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


def test_login_revoga_sessao_anterior(client, db):
    # 1 sessão ativa por usuário: o 2º login invalida o token do 1º
    _criar_usuario()
    t1 = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA}).json()["token"]
    t2 = client.post("/auth/login", json={"email": EMAIL, "senha": SENHA}).json()["token"]
    assert t1 != t2
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {t1}"}).status_code == 401
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
