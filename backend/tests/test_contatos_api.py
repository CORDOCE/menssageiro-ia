"""Testes do CRUD de contatos (task 4): AC-1..AC-6, AC-18.

Rota protegida (Depends(usuario_atual)). Normalização E.164 no schema (telefone inválido → 422).
"""

import uuid
from datetime import UTC, datetime

import app.db.database as db_mod
from app.models.contato import Contato


def _inserir(**kw):
    campos = {"id": str(uuid.uuid4()), "nome": "Fulano", "telefone_e164": "+5511987654321"}
    campos.update(kw)
    sessao = db_mod.SessionLocal()
    try:
        sessao.add(Contato(**campos))
        sessao.commit()
    finally:
        sessao.close()


# --- AC-1: criação normaliza e nasce sem consentimento ---
def test_post_cria_normalizado_sem_consentimento(client, auth_headers):
    r = client.post("/contatos", json={"nome": "Fulano", "telefone": "(11) 98765-4321"}, headers=auth_headers)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["telefone_e164"] == "+5511987654321"
    assert corpo["consentimento"] is False


# --- AC-2: telefone inválido → 422 e nada persiste ---
def test_post_telefone_invalido_422(client, auth_headers):
    r = client.post("/contatos", json={"nome": "Fulano", "telefone": "123"}, headers=auth_headers)
    assert r.status_code == 422
    assert client.get("/contatos", headers=auth_headers).json()["total"] == 0


# --- AC-3: telefone duplicado (canônico) → 409 ---
def test_post_duplicado_409(client, auth_headers):
    client.post("/contatos", json={"nome": "A", "telefone": "11987654321"}, headers=auth_headers)
    r = client.post("/contatos", json={"nome": "B", "telefone": "+55 11 98765-4321"}, headers=auth_headers)
    assert r.status_code == 409


# --- AC-4: lista protegida e paginada ---
def test_get_lista_sem_auth_401(client):
    assert client.get("/contatos").status_code == 401


def test_get_lista_com_auth_paginada(client, auth_headers):
    _inserir(telefone_e164="+5511987654321")
    _inserir(telefone_e164="+5511987654322")
    corpo = client.get("/contatos", headers=auth_headers).json()
    assert corpo["total"] == 2
    assert len(corpo["items"]) == 2


# --- AC-5: filtros grupo/tag/status ---
def test_get_filtros(client, auth_headers):
    _inserir(telefone_e164="+5511900000001", grupo="amigos", tags=["vip"])
    _inserir(telefone_e164="+5511900000002", grupo="trabalho", tags=["lead"])
    _inserir(telefone_e164="+5511900000003", grupo="amigos", tags=["vip"],
             descadastrado_em=datetime.now(UTC))

    assert client.get("/contatos?grupo=amigos", headers=auth_headers).json()["total"] == 2
    assert client.get("/contatos?tag=lead", headers=auth_headers).json()["total"] == 1
    assert client.get("/contatos?status=descadastrado", headers=auth_headers).json()["total"] == 1
    assert client.get("/contatos?status=ativo", headers=auth_headers).json()["total"] == 2


# --- AC-6: PATCH altera campos (telefone re-normalizado); colisão → 409 ---
def test_patch_altera_e_renormaliza(client, auth_headers):
    cid = client.post(
        "/contatos", json={"nome": "Fulano", "telefone": "11987654321"}, headers=auth_headers
    ).json()["id"]
    r = client.patch(
        f"/contatos/{cid}", json={"nome": "Beltrano", "telefone": "(11) 98765-0000"}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["nome"] == "Beltrano"
    assert r.json()["telefone_e164"] == "+5511987650000"


def test_patch_colisao_telefone_409(client, auth_headers):
    client.post("/contatos", json={"nome": "A", "telefone": "11987654321"}, headers=auth_headers)
    cid_b = client.post(
        "/contatos", json={"nome": "B", "telefone": "11987650000"}, headers=auth_headers
    ).json()["id"]
    r = client.patch(f"/contatos/{cid_b}", json={"telefone": "11987654321"}, headers=auth_headers)
    assert r.status_code == 409


# --- AC-18: endpoints protegidos sem credencial → 401 ---
def test_endpoints_sem_auth_401(client):
    assert client.post("/contatos", json={"nome": "X", "telefone": "11987654321"}).status_code == 401
    assert client.get(f"/contatos/{uuid.uuid4()}").status_code == 401
    assert client.patch(f"/contatos/{uuid.uuid4()}", json={"nome": "Y"}).status_code == 401
