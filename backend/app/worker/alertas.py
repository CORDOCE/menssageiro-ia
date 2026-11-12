"""Alertas de agregação do worker (spec 0019 / §12).

Dois sinais que a 0017 deixou de fora:
- **Alerta A — worker parado > 5 min:** check-in de liveness ao Sentry (Cron Monitor) a cada ciclo; a
  ausência dos check-ins é detectada por um observador externo (cobre worker morto, que não se auto-alerta).
- **Alerta B — taxa de falha > 5 %/dia:** computa falhas/tentativas nas últimas 24 h; se passar do limite
  com volume mínimo, emite **1 alerta/dia** (idempotência por auditoria, dia-calendário America/Sao_Paulo).

No-op sem `SENTRY_DSN` (o `sentry_sdk` já é inerte sem `init`). Nunca derruba o ciclo (§5.8).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import sentry_sdk.crons
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.database as _db
from app.core.audit import registrar_auditoria
from app.models.auditoria import Auditoria
from app.models.envio import Envio
from app.worker.disparo import _CONTAM_LIMITE

logger = logging.getLogger(__name__)

# Alerta A — Cron Monitor (upsert inline). Worker faz check-in a cada ciclo; sem check-in além da
# margem (= worker parado > 5 min) o monitor dispara "missed".
# OBS: o `schedule` assume o intervalo padrão do worker (`worker_intervalo_s=60` → 1 min). Se esse
# intervalo mudar, revise o `schedule` aqui para o monitor não acusar "missed" falso.
_MONITOR_SLUG = "worker-ciclo"
_MONITOR_CONFIG: dict[str, Any] = {
    "schedule": {"type": "interval", "value": 1, "unit": "minute"},
    "checkin_margin": 5,  # minutos de tolerância antes de marcar "missed" (= parado > 5 min)
    "max_runtime": 5,
    "failure_issue_threshold": 1,
    "recovery_threshold": 1,
}

# Alerta B — taxa de falha nas últimas 24 h.
# tentativas = reservados/entregues/retry + não-entregas (falhou, aguardando_decisao); exclui 'criado'.
# falhas = não-entregas reais (spec 0020 Q8: aguardando_decisao conta como falha; aguardando_retry não).
_FALHAS = ("falhou", "aguardando_decisao")
_TENTATIVAS = (*_CONTAM_LIMITE, *_FALHAS)
_PISO_VOLUME = 20  # abaixo disto não alerta (anti-ruído) — decisão da spec
_LIMITE_PCT = 5.0
_OP_TAXA = "envios.taxa_falha_alta"
_TZ_SP = ZoneInfo("America/Sao_Paulo")


def checkin_worker() -> None:
    """Alerta A: emite um check-in 'ok' ao Sentry Cron Monitor (upsert inline do schedule). No-op sem
    `SENTRY_DSN`; nunca levanta."""
    try:
        sentry_sdk.crons.capture_checkin(
            monitor_slug=_MONITOR_SLUG,
            status="ok",
            monitor_config=_MONITOR_CONFIG,  # type: ignore[arg-type]  # MonitorConfig é TypedDict (total=False)
        )
    except Exception:  # pragma: no cover — instrumentação nunca derruba o ciclo
        logger.warning("falha ao emitir check-in do worker ao Sentry")


def _contar_24h(sess: Session, agora: datetime) -> tuple[int, int]:
    """(tentativas, falhas) por `Envio.criado_em` nas últimas 24 h. Molde de janela de `disparo.py:142`."""
    desde = agora - timedelta(hours=24)
    tentativas = sess.execute(
        select(func.count())
        .select_from(Envio)
        .where(Envio.status.in_(_TENTATIVAS), Envio.criado_em >= desde)
    ).scalar_one()
    falhas = sess.execute(
        select(func.count())
        .select_from(Envio)
        .where(Envio.status.in_(_FALHAS), Envio.criado_em >= desde)
    ).scalar_one()
    return int(tentativas), int(falhas)


def _ja_alertou_hoje(sess: Session, agora: datetime) -> bool:
    """True se já houve alerta de taxa **hoje** (dia-calendário SP). Molde de `auth.py:68-77`."""
    inicio_dia = (
        agora.astimezone(_TZ_SP).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    )
    n = sess.execute(
        select(func.count())
        .select_from(Auditoria)
        .where(Auditoria.operacao == _OP_TAXA, Auditoria.criado_em >= inicio_dia)
    ).scalar_one()
    return int(n) > 0


def verificar_taxa_falha(agora: datetime | None = None) -> None:
    """Alerta B: se falhas/tentativas > 5 % nas últimas 24 h com volume ≥ piso, emite **1 alerta/dia**.
    Metadados só agregados (sem PII)."""
    agora = agora or datetime.now(UTC)
    sess = _db.SessionLocal()
    try:
        tentativas, falhas = _contar_24h(sess, agora)
        if tentativas < _PISO_VOLUME:
            return
        pct = 100.0 * falhas / tentativas
        if pct <= _LIMITE_PCT:
            return
        if _ja_alertou_hoje(sess, agora):
            return
    finally:
        sess.close()
    registrar_auditoria(
        _OP_TAXA,
        status="warning",
        alertar=True,
        metadados={"tentativas": tentativas, "falhas": falhas, "pct": round(pct, 1)},
    )


def ciclo_alertas() -> None:
    """Alertas de agregação por ciclo (spec 0019). Não-bloqueante: nunca derruba o worker (§5.8)."""
    try:
        checkin_worker()
        verificar_taxa_falha()
    except Exception:  # pragma: no cover — alertas nunca derrubam o worker
        logger.warning("falha nos alertas de agregação do ciclo")
