"""Web Push (spec 0023 / ADR 0015): inscrição de dispositivos + envio de notificações.

`enviar_push` é **no-op sem chaves VAPID** (Fase 0 / testes → sem rede, §5.7), remove inscrições que o
push service rejeita (404/410) e **nunca levanta** (molde de `alertar_evento`). O corpo não leva PII (§6).
"""

from __future__ import annotations

import json
import logging
import uuid

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.database as _db
from app.core.config import get_settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)

# Claim `sub` exigido pelo VAPID (contato do remetente). Não é PII de contato.
_VAPID_SUB = "mailto:alertas@mensageiro"


def chave_publica() -> str | None:
    """Chave pública VAPID para o browser inscrever (ou None se não configurada → UI degrada)."""
    return get_settings().vapid_public_key


def inscrever(db: Session, endpoint: str, p256dh: str, auth: str) -> PushSubscription:
    """Upsert da inscrição por `endpoint` (reinscrição do mesmo dispositivo não duplica)."""
    existente = db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    ).scalar_one_or_none()
    if existente is not None:
        existente.p256dh = p256dh
        existente.auth = auth
        db.commit()
        return existente
    sub = PushSubscription(id=str(uuid.uuid4()), endpoint=endpoint, p256dh=p256dh, auth=auth)
    db.add(sub)
    db.commit()
    return sub


def enviar_push(titulo: str, corpo: str, url: str | None = None) -> None:
    """Notifica todas as inscrições. No-op sem VAPID; remove inscrições 404/410; nunca levanta."""
    cfg = get_settings()
    if not (cfg.vapid_private_key and cfg.vapid_public_key):
        return  # sem VAPID (Fase 0 / testes) → no-op, sem rede (§5.7)
    payload = json.dumps({"titulo": titulo, "corpo": corpo, "url": url or "/"})
    db = _db.SessionLocal()
    try:
        for sub in db.execute(select(PushSubscription)).scalars().all():
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    },
                    data=payload,
                    vapid_private_key=cfg.vapid_private_key,
                    vapid_claims={"sub": _VAPID_SUB},
                )
            except WebPushException as exc:
                status = getattr(exc.response, "status_code", None)
                if status in (404, 410):  # inscrição expirada → remover
                    db.delete(sub)
                    db.commit()
                else:
                    logger.warning("falha ao enviar push (status %s)", status)
            except Exception:  # um envio ruim não impede os demais
                logger.warning("erro inesperado ao enviar push")
    finally:
        db.close()
