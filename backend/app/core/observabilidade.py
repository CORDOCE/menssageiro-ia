"""Inicialização do Sentry (observabilidade — spec 0009 / CLAUDE.md §7).

Sem `SENTRY_DSN` → inerte (no-op). `before_send` mascara PII antes de qualquer envio (§6):
remove corpo/cookies da requisição e mascara telefones em mensagens e exceções.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Literal

import sentry_sdk

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Sequência de 8+ dígitos (telefone e afins): mascara, preservando os 2 últimos para correlação.
_DIGITOS = re.compile(r"\d{8,}")


def _mascarar_texto(texto: str) -> str:
    return _DIGITOS.sub(lambda m: "*" * (len(m.group()) - 2) + m.group()[-2:], texto)


def _mascarar_pii(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """`before_send`: sanitiza o evento. Em falha inesperada, **descarta** o evento (retorna None)
    — nunca deixa PII vazar nem levanta exceção."""
    try:
        req = event.get("request")
        if isinstance(req, dict):
            req.pop("data", None)
            req.pop("cookies", None)
        msg = event.get("message")
        if isinstance(msg, str):
            event["message"] = _mascarar_texto(msg)
        for exc in (event.get("exception", {}) or {}).get("values", []) or []:
            if isinstance(exc.get("value"), str):
                exc["value"] = _mascarar_texto(exc["value"])
        # Mascara PII em `contexts` (ex.: metadados de `alertar_evento` com telefone — spec 0017).
        contexts = event.get("contexts")
        if isinstance(contexts, dict):
            for ctx in contexts.values():
                if isinstance(ctx, dict):
                    for chave, valor in ctx.items():
                        if isinstance(valor, str):
                            ctx[chave] = _mascarar_texto(valor)
        return event
    except Exception:  # pragma: no cover — scrub nunca derruba nem vaza
        logger.warning("falha ao mascarar PII do evento Sentry; evento descartado")
        return None


_NIVEL_SENTRY: dict[str, Literal["error", "warning"]] = {"error": "error", "warning": "warning"}


def alertar_evento(
    operacao: str,
    status: str,
    correlation_id: str | None = None,
    metadados: dict[str, Any] | None = None,
) -> None:
    """Emite um evento de fluxo crítico ao Sentry (spec 0017 / §12). Só alerta em `error`/`warning`;
    no-op sem Sentry inicializado (o `sentry_sdk` já é no-op sem `init`). Passa apenas `operacao` +
    `metadados` (sem PII); `before_send` ainda mascara dígitos. Nunca levanta."""
    nivel = _NIVEL_SENTRY.get(status)
    if nivel is None:
        return
    try:
        sentry_sdk.capture_message(
            operacao,
            level=nivel,
            tags={"correlation_id": correlation_id} if correlation_id else {},
            contexts={"evento": metadados} if metadados else {},
        )
    except Exception:  # pragma: no cover — alerta nunca derruba o fluxo
        logger.warning("falha ao alertar evento ao Sentry: %s", operacao)


def configurar_sentry() -> bool:
    """Inicializa o Sentry se `SENTRY_DSN` existir. Retorna True se inicializou.
    No-op sem DSN; à prova de DSN inválida (não derruba a app)."""
    dsn = get_settings().sentry_dsn
    if not dsn:
        return False
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get("RAILWAY_ENVIRONMENT_NAME"),
            send_default_pii=False,
            traces_sample_rate=0.0,
            before_send=_mascarar_pii,  # type: ignore[arg-type]  # Event/Hint (TypedDict) do sentry vs dict
        )
        return True
    except Exception:  # pragma: no cover — DSN ruim/erro não pode derrubar o startup
        logger.exception("falha ao inicializar o Sentry; seguindo sem observabilidade de erros")
        return False
