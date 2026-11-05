"""Endpoint de envio de teste (task 11 / AC-14, AC-15, AC-16).

Restrito ao número de teste (§4: nunca número real). `enviar_template` é mockado (nunca a API real).
"""

from uuid import uuid4

import app.db.database as db_mod
from app.core.config import get_settings
from app.core.telefone import mascarar_telefone
from app.models.auditoria import Auditoria
from app.models.modelo import Modelo

_TESTE = "+5511999990000"


def _modelo() -> str:
    sessao = db_mod.SessionLocal()
    try:
        mid = str(uuid4())
        sessao.add(Modelo(id=mid, nome="cobranca", corpo="Olá {{1}}", status="aprovado"))
        sessao.commit()
        return mid
    finally:
        sessao.close()


def _seed_modelo(nome: str, status: str = "aprovado") -> None:
    sessao = db_mod.SessionLocal()
    try:
        sessao.add(Modelo(id=str(uuid4()), nome=nome, corpo=f"Corpo {nome}", status=status))
        sessao.commit()
    finally:
        sessao.close()


# --- GET /modelos (spec 0010) ---------------------------------------------------------------------
def test_listar_modelos_sem_auth_401(client, db):
    r = client.get("/modelos")
    assert r.status_code == 401


def test_listar_modelos_ordenado_por_nome(client, db, auth_headers):
    _seed_modelo("banana")
    _seed_modelo("abacaxi")
    r = client.get("/modelos", headers=auth_headers)
    assert r.status_code == 200
    nomes = [m["nome"] for m in r.json()]
    assert nomes == ["abacaxi", "banana"]
    assert r.json()[0]["variaveis"] == []  # default


def test_listar_modelos_filtra_por_status(client, db, auth_headers):
    _seed_modelo("aprovado1", status="aprovado")
    _seed_modelo("rascunho1", status="rascunho")
    r = client.get("/modelos?status=aprovado", headers=auth_headers)
    assert r.status_code == 200
    nomes = [m["nome"] for m in r.json()]
    assert nomes == ["aprovado1"]


def test_listar_modelos_status_invalido_422(client, db, auth_headers):
    r = client.get("/modelos?status=xpto", headers=auth_headers)
    assert r.status_code == 422


def test_listar_modelos_vazio(client, db, auth_headers):
    r = client.get("/modelos", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_enviar_teste_sem_auth_401(client, db):
    mid = _modelo()
    r = client.post(f"/modelos/{mid}/enviar-teste", json={"telefone": _TESTE})
    assert r.status_code == 401


def test_enviar_teste_numero_de_teste_ok(client, db, auth_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "whatsapp_test_number", _TESTE)
    monkeypatch.setattr("app.api.modelos.enviar_template", lambda *a, **k: "wamid.TESTE")
    mid = _modelo()
    r = client.post(
        f"/modelos/{mid}/enviar-teste",
        json={"telefone": "(11) 99999-0000"},  # mesmo número, formatação diferente
        headers=auth_headers,
    )
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["wamid"] == "wamid.TESTE"
    assert corpo["status"] == "enviado"


def test_enviar_teste_numero_diferente_403_nao_envia(client, db, auth_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "whatsapp_test_number", _TESTE)
    chamou = {"n": 0}

    def _fake(*a, **k):
        chamou["n"] += 1
        return "x"

    monkeypatch.setattr("app.api.modelos.enviar_template", _fake)
    mid = _modelo()
    r = client.post(
        f"/modelos/{mid}/enviar-teste", json={"telefone": "11988887777"}, headers=auth_headers
    )
    assert r.status_code == 403
    assert chamou["n"] == 0  # nunca chamou o cliente / nunca enviou


def test_enviar_teste_audita_sem_pii(client, db, auth_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "whatsapp_test_number", _TESTE)
    monkeypatch.setattr("app.api.modelos.enviar_template", lambda *a, **k: "wamid.T")
    mid = _modelo()
    client.post(f"/modelos/{mid}/enviar-teste", json={"telefone": _TESTE}, headers=auth_headers)
    sessao = db_mod.SessionLocal()
    try:
        regs = sessao.query(Auditoria).filter(Auditoria.operacao == "envio_teste").all()
    finally:
        sessao.close()
    assert len(regs) == 1
    meta = regs[0].metadados or ""
    assert "5511999990000" not in meta  # telefone cheio NÃO aparece
    assert mascarar_telefone(_TESTE) in meta  # máscara presente


# --- POST /modelos/sincronizar (spec 0010) --------------------------------------------------------
_TEMPLATES_META = [
    {"name": "cobranca", "language": "pt_BR", "category": "UTILITY", "status": "APPROVED",
     "components": [
         {"type": "HEADER", "format": "TEXT"},
         {"type": "BODY", "text": "Olá {{1}}, fatura {{2}}"},
     ]},
    {"name": "promo", "language": "pt_BR", "category": "MARKETING", "status": "REJECTED",
     "components": [{"type": "BODY", "text": "Oferta"}]},
    {"name": "aviso", "language": "pt_BR", "category": "UTILITY", "status": "PAUSED", "components": []},
]


def test_sincronizar_sem_auth_401(client, db):
    r = client.post("/modelos/sincronizar")
    assert r.status_code == 401


def test_sincronizar_cria_e_mapeia_status(client, db, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.modelos.listar_templates", lambda: _TEMPLATES_META)
    r = client.post("/modelos/sincronizar", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"total": 3, "criados": 3, "atualizados": 0}
    cob = db.query(Modelo).filter_by(nome="cobranca").one()
    assert cob.status == "aprovado"
    assert cob.variaveis == ["1", "2"]
    assert cob.cabecalho_tipo == "TEXT"
    assert db.query(Modelo).filter_by(nome="promo").one().status == "rejeitado"
    assert db.query(Modelo).filter_by(nome="aviso").one().status == "pausado"


def test_sincronizar_atualiza_existente(client, db, auth_headers, monkeypatch):
    _seed_modelo("cobranca", status="pendente")
    monkeypatch.setattr(
        "app.api.modelos.listar_templates",
        lambda: [{"name": "cobranca", "language": "pt_BR", "category": "UTILITY",
                  "status": "APPROVED", "components": [{"type": "BODY", "text": "Oi"}]}],
    )
    r = client.post("/modelos/sincronizar", headers=auth_headers)
    assert r.json() == {"total": 1, "criados": 0, "atualizados": 1}
    assert db.query(Modelo).filter_by(nome="cobranca").one().status == "aprovado"
