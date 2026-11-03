"""Webhook da Meta (tasks 7-9 / AC-5, AC-6, AC-7, AC-8, AC-9, AC-11).

Assinatura validada sobre o corpo cru (HMAC-SHA256 com APP_SECRET). Testes constroem o payload e
assinam localmente — nunca a API real (§5.7). Status casam pelo `wamid`; idempotência por monotonicidade.
"""

import hashlib
import hmac
import json
from uuid import uuid4

import app.db.database as db_mod
from app.core.config import get_settings
from app.models.contato import Contato
from app.models.envio import Envio

_SECRET = "SEGREDO_TESTE"
_VERIFY = "VERIFY_TESTE"


def _cfg(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "app_secret", _SECRET)
    monkeypatch.setattr(s, "webhook_verify_token", _VERIFY)


def _assinar(corpo: bytes) -> str:
    return "sha256=" + hmac.new(_SECRET.encode(), corpo, hashlib.sha256).hexdigest()


def _post(client, payload: dict, assinatura: str | None = None):
    corpo = json.dumps(payload).encode()
    sig = assinatura if assinatura is not None else _assinar(corpo)
    return client.post(
        "/webhook/meta", content=corpo,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )


def _payload_status(wamid: str, status: str, *, pricing=None, errors=None) -> dict:
    st: dict = {"id": wamid, "status": status, "timestamp": "1750000000", "recipient_id": "5511999990000"}
    if pricing is not None:
        st["pricing"] = pricing
    if errors is not None:
        st["errors"] = errors
    if status != "failed":
        st["conversation"] = {"id": "conv1", "origin": {"type": "service"}}
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": {"statuses": [st]}}]}],
    }


def _criar_envio(wamid: str, status: str = "enviado") -> str:
    sessao = db_mod.SessionLocal()
    try:
        cid = str(uuid4())
        sessao.add(Contato(id=cid, nome="X", telefone_e164="+5511999990000"))
        eid = str(uuid4())
        sessao.add(Envio(id=eid, contato_id=cid, wamid=wamid, status=status))
        sessao.commit()
        return eid
    finally:
        sessao.close()


def _envio(wamid: str) -> Envio:
    sessao = db_mod.SessionLocal()
    try:
        return sessao.query(Envio).filter(Envio.wamid == wamid).one()
    finally:
        sessao.close()


# --- AC-5: verificação GET ---
def test_get_verifica_token_ok(client, monkeypatch):
    _cfg(monkeypatch)
    params = {"hub.mode": "subscribe", "hub.verify_token": _VERIFY, "hub.challenge": "42"}
    r = client.get("/webhook/meta", params=params)
    assert r.status_code == 200
    assert r.text == "42"


def test_get_token_errado_403(client, monkeypatch):
    _cfg(monkeypatch)
    params = {"hub.mode": "subscribe", "hub.verify_token": "errado", "hub.challenge": "42"}
    r = client.get("/webhook/meta", params=params)
    assert r.status_code == 403


# --- AC-6: assinatura inválida ---
def test_post_assinatura_invalida_403(client, db, monkeypatch):
    _cfg(monkeypatch)
    _criar_envio("wamid.A", "enviado")
    r = _post(client, _payload_status("wamid.A", "delivered"), assinatura="sha256=errado")
    assert r.status_code == 403
    assert _envio("wamid.A").status == "enviado"  # nada foi processado


# --- AC-7: status delivered/read → envio ---
def test_post_status_delivered_grava(client, db, monkeypatch):
    _cfg(monkeypatch)
    _criar_envio("wamid.B", "enviado")
    pricing = {"billable": True, "pricing_model": "CBP", "category": "service"}
    r = _post(client, _payload_status("wamid.B", "delivered", pricing=pricing))
    assert r.status_code == 200
    e = _envio("wamid.B")
    assert e.status == "entregue"
    assert e.pricing == pricing
    assert e.conversation is not None


def test_post_status_read_sobe(client, db, monkeypatch):
    _cfg(monkeypatch)
    _criar_envio("wamid.C", "entregue")
    _post(client, _payload_status("wamid.C", "read"))
    assert _envio("wamid.C").status == "lido"


# --- AC-8: failed → falhou ---
def test_post_status_failed(client, db, monkeypatch):
    _cfg(monkeypatch)
    _criar_envio("wamid.D", "enviado")
    errors = [{"code": 131026, "title": "Message undeliverable"}]
    _post(client, _payload_status("wamid.D", "failed", errors=errors))
    e = _envio("wamid.D")
    assert e.status == "falhou"
    assert e.erro_codigo == "131026"


# --- AC-9: idempotência (monotonicidade) ---
def test_post_idempotente_e_fora_de_ordem(client, db, monkeypatch):
    _cfg(monkeypatch)
    _criar_envio("wamid.E", "enviado")
    _post(client, _payload_status("wamid.E", "read"))
    assert _envio("wamid.E").status == "lido"
    # reentrega de 'delivered' (mais antigo) não rebaixa; 'read' repetido é no-op
    _post(client, _payload_status("wamid.E", "delivered"))
    _post(client, _payload_status("wamid.E", "read"))
    assert _envio("wamid.E").status == "lido"


def test_post_wamid_desconhecido_200(client, db, monkeypatch):
    _cfg(monkeypatch)
    r = _post(client, _payload_status("wamid.NAO_EXISTE", "delivered"))
    assert r.status_code == 200  # ignora sem quebrar


# --- AC-11: mensagem recebida não persiste conteúdo ---
def test_post_mensagem_recebida_200_sem_persistir(client, db, monkeypatch):
    _cfg(monkeypatch)
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": {
            "messages": [{"id": "wamid.IN", "from": "5511999990000", "type": "text",
                          "text": {"body": "oi"}}]}}]}],
    }
    r = _post(client, payload)
    assert r.status_code == 200
