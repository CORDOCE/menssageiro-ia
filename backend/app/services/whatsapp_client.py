"""Cliente da WhatsApp Cloud API (spec 0003 / ADR 0007).

Envia mensagem `type: template` via `POST {GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages` e devolve
o `wamid`. Retry exponencial (429/5xx, máx. 3); erro definitivo → `WhatsappError` com código/motivo.
Versão da Graph API sempre via `GRAPH_API_VERSION` (nunca fixa). Testes mockam `httpx`, nunca a API real.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import get_settings

_MAX_TENTATIVAS = 3
_BACKOFF_BASE_S = 0.5


class WhatsappError(Exception):
    """Falha definitiva da Cloud API (ou resposta inesperada), com código e motivo legível."""

    def __init__(self, codigo: int | str, motivo: str) -> None:
        super().__init__(f"[{codigo}] {motivo}")
        self.codigo = codigo
        self.motivo = motivo


def enviar_template(
    telefone_e164: str,
    nome_template: str,
    idioma: str,
    componentes: list[dict[str, Any]],
    *,
    client: httpx.Client | None = None,
) -> str:
    """Envia um template e devolve o `wamid` (`messages[0].id`)."""
    cfg = get_settings()
    url = f"https://graph.facebook.com/{cfg.graph_api_version}/{cfg.phone_number_id}/messages"
    corpo: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": telefone_e164.lstrip("+"),
        "type": "template",
        "template": {"name": nome_template, "language": {"code": idioma}, "components": componentes},
    }
    headers = {"Authorization": f"Bearer {cfg.whatsapp_token}"}

    criado = client is None
    c = client or httpx.Client(timeout=30.0)
    try:
        dados = _post_com_retry(c, url, corpo, headers)
    finally:
        if criado:
            c.close()

    mensagens = dados.get("messages")
    if not mensagens:
        raise WhatsappError("resposta_invalida", "resposta da Meta sem messages[].id")
    return str(mensagens[0]["id"])


def upload_midia(
    conteudo: bytes, tipo_mime: str, nome_arquivo: str = "arquivo", *, client: httpx.Client | None = None
) -> str:
    """Sobe uma mídia (ex.: PDF) e devolve o `id` para usar no cabeçalho DOCUMENT do template."""
    cfg = get_settings()
    url = f"https://graph.facebook.com/{cfg.graph_api_version}/{cfg.phone_number_id}/media"
    headers = {"Authorization": f"Bearer {cfg.whatsapp_token}"}
    criado = client is None
    c = client or httpx.Client(timeout=60.0)
    try:
        resposta = c.post(
            url,
            headers=headers,
            data={"messaging_product": "whatsapp", "type": tipo_mime},
            files={"file": (nome_arquivo, conteudo, tipo_mime)},
        )
    finally:
        if criado:
            c.close()
    if resposta.status_code >= 400:
        raise _erro_da_resposta(resposta)
    dados: dict[str, Any] = resposta.json()
    media_id = dados.get("id")
    if not media_id:
        raise WhatsappError("resposta_invalida", "upload de mídia sem id")
    return str(media_id)


def componente_documento(media_id: str) -> dict[str, Any]:
    """Monta o componente de cabeçalho DOCUMENT para `enviar_template` (PDF via media id)."""
    return {"type": "header", "parameters": [{"type": "document", "document": {"id": media_id}}]}


def _post_com_retry(
    client: httpx.Client, url: str, corpo: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    for tentativa in range(_MAX_TENTATIVAS):
        resposta = client.post(url, json=corpo, headers=headers)
        if resposta.status_code < 400:
            dados: dict[str, Any] = resposta.json()
            return dados
        if _retentavel(resposta.status_code) and tentativa < _MAX_TENTATIVAS - 1:
            time.sleep(_BACKOFF_BASE_S * (2**tentativa))
            continue
        raise _erro_da_resposta(resposta)
    raise WhatsappError("inesperado", "laço de retry terminou sem resposta")  # pragma: no cover


def _retentavel(status: int) -> bool:
    return status == 429 or status >= 500


def _erro_da_resposta(resposta: httpx.Response) -> WhatsappError:
    codigo: int | str = resposta.status_code
    motivo = f"HTTP {resposta.status_code}"
    try:
        err = resposta.json().get("error", {})
    except (ValueError, TypeError):
        err = {}
    if isinstance(err, dict):
        if "code" in err:
            codigo = err["code"]
        if "message" in err:
            motivo = str(err["message"])
    return WhatsappError(codigo, motivo)
