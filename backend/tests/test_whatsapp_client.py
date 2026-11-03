"""Cliente WhatsApp (task 5 / AC-1, AC-2, AC-3). Mock de httpx (payloads da doc oficial); nunca a API real."""

import json

import httpx
import pytest

from app.core.config import get_settings
from app.services.whatsapp_client import WhatsappError, enviar_template


@pytest.fixture
def cfg(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "phone_number_id", "123456")
    monkeypatch.setattr(s, "whatsapp_token", "TESTTOKEN")
    monkeypatch.setattr(s, "graph_api_version", "v26.0")
    return s


def _componentes():
    return [{"type": "body", "parameters": [{"type": "text", "text": "João"}]}]


def test_envia_template_monta_corpo_e_retorna_wamid(cfg):
    capturado = {}

    def handler(req: httpx.Request) -> httpx.Response:
        capturado["url"] = str(req.url)
        capturado["auth"] = req.headers.get("authorization")
        capturado["body"] = json.loads(req.content)
        return httpx.Response(200, json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.XYZ"}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    wamid = enviar_template("+5511987654321", "cobranca", "pt_BR", _componentes(), client=client)

    assert wamid == "wamid.XYZ"
    assert capturado["url"] == "https://graph.facebook.com/v26.0/123456/messages"
    assert capturado["auth"] == "Bearer TESTTOKEN"
    corpo = capturado["body"]
    assert corpo["messaging_product"] == "whatsapp"
    assert corpo["to"] == "5511987654321"  # E.164 sem o '+'
    assert corpo["type"] == "template"
    assert corpo["template"]["name"] == "cobranca"
    assert corpo["template"]["language"]["code"] == "pt_BR"


def test_retry_exponencial_em_5xx(cfg, monkeypatch):
    monkeypatch.setattr("app.services.whatsapp_client.time.sleep", lambda _s: None)
    chamadas = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"messages": [{"id": "wamid.OK"}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    wamid = enviar_template("+5511987654321", "t", "pt_BR", [], client=client)
    assert wamid == "wamid.OK"
    assert chamadas["n"] == 3  # 2 falhas + 1 sucesso


def test_erro_definitivo_levanta_sem_retry(cfg):
    chamadas = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        return httpx.Response(400, json={"error": {"code": 131026, "message": "Message undeliverable"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(WhatsappError) as exc:
        enviar_template("+5511987654321", "t", "pt_BR", [], client=client)
    assert chamadas["n"] == 1  # 4xx não-retentável: sem retry
    assert exc.value.codigo == 131026
