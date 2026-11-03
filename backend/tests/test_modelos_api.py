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
