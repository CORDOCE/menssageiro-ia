"""Webhook da Meta (spec 0003 / ADR 0007).

Público (a Meta chama); a segurança é a **assinatura**, não auth de sessão. `GET` faz a verificação
(`hub.*`); `POST` valida `X-Hub-Signature-256` (HMAC-SHA256 do corpo cru com `APP_SECRET`) ANTES de
parsear, responde 200 rápido, e aplica os `statuses` no `envio` pelo `wamid`. Idempotência por
monotonicidade (um status não rebaixa outro já aplicado).

Fontes (2026-11-03): `.../cloud-api/webhooks/payload-examples`, `.../graph-api/webhooks/getting-started`.
`message_template_status_update` (AC-10) fica para a task 10, após confirmar o payload exato na doc.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.models.envio import Envio

router = APIRouter(prefix="/webhook/meta", tags=["webhook"])

# status da Meta → status interno, com rank para monotonicidade/idempotência.
_STATUS_META = {"sent": "enviado", "delivered": "entregue", "read": "lido"}
_RANK = {"criado": 0, "enviando": 1, "enviado": 2, "entregue": 3, "lido": 4, "falhou": 5}


@router.get("")
def verificar(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    """Handshake de verificação: devolve `hub.challenge` se o verify token confere."""
    cfg = get_settings()
    if hub_mode == "subscribe" and hub_verify_token and hub_verify_token == cfg.webhook_verify_token:
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="verificação inválida")


@router.post("")
async def receber(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """Valida a assinatura sobre o corpo cru (antes de parsear) e processa os eventos."""
    corpo = await request.body()
    if not _assinatura_valida(corpo, request.headers.get("X-Hub-Signature-256", "")):
        raise HTTPException(status_code=403, detail="assinatura inválida")
    try:
        evento: dict[str, Any] = json.loads(corpo)
    except ValueError:
        return {"status": "ignorado"}  # 200: nunca devolve erro à Meta por payload estranho
    _processar(db, evento)
    return {"status": "ok"}


def _assinatura_valida(corpo: bytes, header: str) -> bool:
    cfg = get_settings()
    if not cfg.app_secret or not header.startswith("sha256="):
        return False
    esperado = hmac.new(cfg.app_secret.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest("sha256=" + esperado, header)


def _processar(db: Session, evento: dict[str, Any]) -> None:
    for entry in evento.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for status in value.get("statuses", []):
                _aplicar_status(db, status)
            # `messages` recebidas → 200-ack, sem persistir conteúdo (AC-11; conteúdo é Fase 8).
            # `message_template_status_update` → task 10 (após confirmar o payload na doc).


def _aplicar_status(db: Session, status: dict[str, Any]) -> None:
    wamid = status.get("id")
    if not wamid:
        return
    envio = db.execute(select(Envio).where(Envio.wamid == wamid)).scalar_one_or_none()
    if envio is None:
        return  # wamid desconhecido: ignora sem quebrar

    meta_status = status.get("status")
    if meta_status == "failed":
        envio.status = "falhou"
        erros = status.get("errors") or []
        if erros:
            envio.erro_codigo = str(erros[0].get("code", ""))
            envio.erro_motivo = str(erros[0].get("title") or erros[0].get("message") or "")
        db.commit()
        return

    novo = _STATUS_META.get(meta_status or "")
    if novo is None:
        return
    # Monotonicidade: só avança; reentrega/fora de ordem é no-op (idempotência, AC-9).
    if _RANK.get(novo, 0) > _RANK.get(envio.status, 0):
        envio.status = novo
        if "pricing" in status:
            envio.pricing = status["pricing"]
        if "conversation" in status:
            envio.conversation = status["conversation"]
        db.commit()
