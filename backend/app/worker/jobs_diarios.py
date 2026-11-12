"""Jobs diários do worker (spec 0022). v1: **06:00 sincronizar modelos**.

Rodados a cada ciclo do loop (`ciclo_jobs_diarios`), mas cada job só dispara na sua janela de horário
(SP) e **1×/dia** (idempotência por auditoria). Degradam sem derrubar o worker (§5.8). Os demais jobs
do §10.3 (07:00 sugestões IA, 07:30 resumo) são das Fases 6/7 — fora do escopo desta spec.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import sentry_sdk
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.database as _db
from app.core.audit import registrar_auditoria
from app.core.config import get_settings
from app.models.auditoria import Auditoria
from app.services.modelos_sync import sincronizar_modelos
from app.services.whatsapp_client import listar_templates

logger = logging.getLogger(__name__)

_TZ_SP = ZoneInfo("America/Sao_Paulo")
_OP_SYNC = "job.sincronizar_modelos"


def _inicio_dia_sp(agora: datetime) -> datetime:
    """Meia-noite do dia-calendário America/Sao_Paulo, em UTC (molde de `alertas.py`)."""
    return (
        agora.astimezone(_TZ_SP).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    )


def _ja_rodou_hoje(sess: Session, agora: datetime) -> bool:
    """True se o job já foi **tentado** hoje (dia SP) — sucesso ou erro contam (1 tentativa/dia)."""
    inicio = _inicio_dia_sp(agora)
    n = sess.execute(
        select(func.count())
        .select_from(Auditoria)
        .where(Auditoria.operacao == _OP_SYNC, Auditoria.criado_em >= inicio)
    ).scalar_one()
    return int(n) > 0


def sincronizar_modelos_job(agora: datetime | None = None) -> None:
    """Sincroniza os modelos 1×/dia a partir de `sync_modelos_hora` (SP). Falha degrada (Sentry +
    auditoria `error`) sem propagar e **conta como a tentativa do dia** (não martela a Meta)."""
    cfg = get_settings()
    # Sem credenciais Meta (produção Fase 0 / testes) → no-op total, sem rede (§5.7): nada a sincronizar.
    if not (cfg.waba_id and cfg.whatsapp_token):
        return
    agora = agora or datetime.now(UTC)
    if agora.astimezone(_TZ_SP).hour < cfg.sync_modelos_hora:
        return
    sess = _db.SessionLocal()
    status = "ok"
    try:
        if _ja_rodou_hoje(sess, agora):
            return
        try:
            templates = listar_templates()
            sincronizar_modelos(sess, templates, ator_email=None)
        except Exception:
            sess.rollback()
            sentry_sdk.capture_exception()
            status = "error"
    finally:
        sess.close()
    registrar_auditoria(_OP_SYNC, status=status)


def ciclo_jobs_diarios(agora: datetime | None = None) -> None:
    """Jobs diários por ciclo (spec 0022). Não-bloqueante: nunca derruba o worker (§5.8)."""
    try:
        sincronizar_modelos_job(agora)
    except Exception:  # pragma: no cover — jobs diários nunca derrubam o worker
        logger.warning("falha nos jobs diários do ciclo")
