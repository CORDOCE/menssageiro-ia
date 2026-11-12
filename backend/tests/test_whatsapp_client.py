"""Cliente WhatsApp (task 5 / AC-1, AC-2, AC-3). Mock de httpx (payloads da doc oficial); nunca a API real."""

import json

import httpx
import pytest

from app.core.config import get_settings
from app.services.whatsapp_client import (
    WhatsappError,
    componente_documento,
    enviar_template,
    listar_templates,
    upload_midia,
)


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


@pytest.mark.parametrize(
    "exc",
    [httpx.ConnectError("sem conexão"), httpx.ReadTimeout("estourou o tempo")],
)
def test_falha_transporte_vira_whatsapp_error(cfg, exc):
    """Erro de transporte (conexão/timeout) não vaza httpx: vira WhatsappError.

    Sem isto, a exceção httpx escapa até o worker e deixa o envio reservado preso em 'enviando'
    (órfão), pois `_enviar_um` só trata `WhatsappError`.
    """

    def handler(req: httpx.Request) -> httpx.Response:
        raise exc

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(WhatsappError) as ei:
        enviar_template("+5511987654321", "t", "pt_BR", [], client=client)
    assert ei.value.codigo == "transporte"


# --- 0020 T2: classe da falha (AC-1..AC-4) ---
@pytest.mark.parametrize(
    "exc,classe",
    [
        (httpx.ConnectError("x"), "retentavel"),  # AC-1: antes do request, nada entregue
        (httpx.ConnectTimeout("x"), "retentavel"),  # subtipo de ConnectError
        (httpx.ReadTimeout("x"), "ambiguo"),  # AC-2: request pode ter chegado
        (httpx.PoolTimeout("x"), "ambiguo"),
    ],
)
def test_classe_falha_transporte(cfg, exc, classe):
    def handler(req: httpx.Request) -> httpx.Response:
        raise exc

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(WhatsappError) as ei:
        enviar_template("+5511987654321", "t", "pt_BR", [], client=client)
    assert ei.value.classe == classe


@pytest.mark.parametrize(
    "status,codigo,classe",
    [
        (429, 130429, "retentavel"),  # AC-4: HTTP 429 (limite) → retenta
        (400, 131056, "retentavel"),  # AC-4: código Meta na allowlist (pair rate limit)
        (503, 999999, "ambiguo"),  # AC-2: 5xx → ambíguo (pode ter processado)
        (400, 131026, "definitivo"),  # AC-3: código fora da allowlist (número inválido)
    ],
)
def test_classe_erro_http(cfg, monkeypatch, status, codigo, classe):
    monkeypatch.setattr("app.services.whatsapp_client.time.sleep", lambda _s: None)

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"code": codigo, "message": "x"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(WhatsappError) as ei:
        enviar_template("+5511987654321", "t", "pt_BR", [], client=client)
    assert ei.value.classe == classe


# --- AC-4: upload de mídia + cabeçalho DOCUMENT ---
def test_upload_midia_e_componente_documento(cfg):
    capturado = {}

    def handler(req: httpx.Request) -> httpx.Response:
        capturado["path"] = req.url.path
        return httpx.Response(200, json={"id": "MEDIA123"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    media_id = upload_midia(b"%PDF-falso", "application/pdf", client=client)

    assert media_id == "MEDIA123"
    assert capturado["path"] == "/v26.0/123456/media"
    comp = componente_documento(media_id)
    assert comp["type"] == "header"
    assert comp["parameters"][0]["document"]["id"] == "MEDIA123"


def test_listar_templates_segue_paginacao(cfg, monkeypatch):
    """listar_templates faz GET em /{WABA_ID}/message_templates e segue paging.next (2 páginas)."""
    monkeypatch.setattr(cfg, "waba_id", "WABA1")
    pag2 = "https://graph.facebook.com/v26.0/WABA1/message_templates?after=CUR2"

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "GET"
        assert req.headers["Authorization"] == "Bearer TESTTOKEN"
        if "after=CUR2" in str(req.url):
            return httpx.Response(
                200, json={"data": [{"name": "t2", "language": "pt_BR", "status": "PENDING"}]}
            )
        return httpx.Response(
            200,
            json={
                "data": [{"name": "t1", "language": "pt_BR", "status": "APPROVED",
                          "components": [{"type": "BODY", "text": "Oi {{1}}"}]}],
                "paging": {"next": pag2},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    templates = listar_templates(client=client)
    assert [t["name"] for t in templates] == ["t1", "t2"]
