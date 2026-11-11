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
    """Falha da Cloud API (ou resposta inesperada), com código, motivo legível e **classe** de reenvio
    (spec 0020 / ADR 0014): `retentavel` (certeza de não-entrega) · `ambiguo` (pode ter entregue) ·
    `definitivo` (não adianta reenviar). Default `definitivo` (conservador)."""

    def __init__(self, codigo: int | str, motivo: str, classe: str = "definitivo") -> None:
        super().__init__(f"[{codigo}] {motivo}")
        self.codigo = codigo
        self.motivo = motivo
        self.classe = classe


# Códigos Meta temporários **e de não-entrega** (retentáveis). Fonte: Cloud API error codes,
# https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes/ (consultado 2026-11-11).
# Só limite de taxa e serviço indisponível — mensagem rejeitada antes da entrega (at-most-once, ADR 0014).
_ALLOWLIST_RETENTAVEL: frozenset[str] = frozenset(
    {
        "4", "80007", "130429", "131056", "131057", "133016",  # limites de taxa
        "2", "131016", "133004", "2494100",  # serviço temporariamente indisponível
    }
)


def _classificar(status: int, codigo: int | str) -> str:
    """Classe de reenvio da falha HTTP/aplicacional (ADR 0014). Retentável só com certeza de não-entrega."""
    if status == 429:
        return "retentavel"
    if status >= 500:
        return "ambiguo"  # 5xx: a Meta pode ter processado — não reenvia automaticamente
    if str(codigo) in _ALLOWLIST_RETENTAVEL:
        return "retentavel"
    return "definitivo"


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


def listar_templates(*, client: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Lê os message templates da WABA (`GET /{WABA_ID}/message_templates`), seguindo a paginação
    (`paging.next`). Só leitura — não envia nem cria nada. Versão via `GRAPH_API_VERSION`.
    Doc: developers.facebook.com/docs/graph-api/reference/whats-app-business-account/message_templates/
    (consultada 2026-11-05)."""
    cfg = get_settings()
    url: str | None = (
        f"https://graph.facebook.com/{cfg.graph_api_version}/{cfg.waba_id}/message_templates?limit=100"
    )
    headers = {"Authorization": f"Bearer {cfg.whatsapp_token}"}
    criado = client is None
    c = client or httpx.Client(timeout=30.0)
    templates: list[dict[str, Any]] = []
    try:
        while url:
            resposta = c.get(url, headers=headers)
            if resposta.status_code >= 400:
                raise _erro_da_resposta(resposta)
            dados: dict[str, Any] = resposta.json()
            templates.extend(dados.get("data", []))
            url = (dados.get("paging") or {}).get("next")
    finally:
        if criado:
            c.close()
    return templates


def componente_documento(media_id: str) -> dict[str, Any]:
    """Monta o componente de cabeçalho DOCUMENT para `enviar_template` (PDF via media id)."""
    return {"type": "header", "parameters": [{"type": "document", "document": {"id": media_id}}]}


def _post_com_retry(
    client: httpx.Client, url: str, corpo: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    for tentativa in range(_MAX_TENTATIVAS):
        try:
            resposta = client.post(url, json=corpo, headers=headers)
        except httpx.RequestError as exc:
            # Falha de transporte (conexão/timeout): não deixa a exceção httpx vazar — o chamador
            # só trata WhatsappError e, sem isto, a linha reservada fica presa em 'enviando' (órfão).
            # Falha na fase de conexão = nada enviado (retentável); demais = pode ter chegado (ambíguo).
            conexao = isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout))
            classe = "retentavel" if conexao else "ambiguo"
            raise WhatsappError(
                "transporte", f"falha de transporte: {type(exc).__name__}", classe=classe
            ) from exc
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
    return WhatsappError(codigo, motivo, classe=_classificar(resposta.status_code, codigo))
