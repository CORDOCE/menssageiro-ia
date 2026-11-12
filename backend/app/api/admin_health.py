"""Saúde profunda do sistema (spec 0021 / BRIEFING §12): `GET /admin/health/deep`.

Read-only e autenticado. Monta um retrato operacional do banco: estado do banco, do worker
(heartbeat `saude.ultimo_ciclo_em`), envios do dia por status, taxa de falha do dia, fila de
agendamentos vencidos e gasto estimado do mês. Nenhuma chamada externa — token/qualidade do
número da Meta dependem da Fase 0 e ficam fora (spec 0021, "Fora de escopo"). Não muda estado.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.auth_deps import usuario_atual
from app.core.config import get_settings
from app.db.database import get_db
from app.models.agendamento import Agendamento
from app.models.envio import Envio
from app.models.saude import Saude
from app.schemas.saude import BancoSaude, GastoMes, SaudeDeep, TaxaFalha, WorkerSaude

router = APIRouter(prefix="/admin/health", tags=["saude"], dependencies=[Depends(usuario_atual)])

_TZ_SP = ZoneInfo("America/Sao_Paulo")
_WORKER_PARADO_S = 300  # 5 min (BRIEFING §12)
# Espelham worker/disparo.py (0020) e worker/alertas.py (0019) — mesma semântica de falha/tentativa.
_SUCESSO_COBRADO = ("enviado", "entregue", "lido")
_FALHAS = ("falhou", "aguardando_decisao")
_TENTATIVAS = ("enviando", "enviado", "entregue", "lido", "aguardando_retry", *_FALHAS)


def _inicio_dia_sp(agora: datetime) -> datetime:
    """Meia-noite do dia-calendário America/Sao_Paulo, em UTC (molde de `alertas.py`)."""
    return (
        agora.astimezone(_TZ_SP).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    )


def _inicio_mes_sp(agora: datetime) -> datetime:
    """Primeiro instante do mês-calendário America/Sao_Paulo, em UTC."""
    return (
        agora.astimezone(_TZ_SP)
        .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        .astimezone(UTC)
    )


def _checar_banco(db: Session) -> BancoSaude:
    """`SELECT 1` degradável: falha vira `erro` (com rollback) sem derrubar o endpoint (AC-3)."""
    try:
        db.execute(text("SELECT 1"))
        return BancoSaude(status="ok")
    except Exception:
        db.rollback()
        return BancoSaude(status="erro")


def _estado_worker(db: Session, agora: datetime) -> WorkerSaude:
    saude = db.execute(select(Saude)).scalars().first()
    if saude is None:
        return WorkerSaude(status="desconhecido", ultimo_ciclo_em=None, segundos_desde=None)
    desde = int((agora - saude.ultimo_ciclo_em).total_seconds())
    status = "vivo" if desde <= _WORKER_PARADO_S else "parado"
    return WorkerSaude(status=status, ultimo_ciclo_em=saude.ultimo_ciclo_em, segundos_desde=desde)


def _envios_por_status(db: Session, desde: datetime) -> dict[str, int]:
    rows = db.execute(
        select(Envio.status, func.count()).where(Envio.criado_em >= desde).group_by(Envio.status)
    ).all()
    return {status: int(n) for status, n in rows}


def _taxa_falha(contagem: dict[str, int]) -> TaxaFalha:
    """Deriva a taxa do dia das contagens por status (mesma definição da 0019)."""
    tentativas = sum(n for s, n in contagem.items() if s in _TENTATIVAS)
    falhas = sum(n for s, n in contagem.items() if s in _FALHAS)
    pct = round(100.0 * falhas / tentativas, 1) if tentativas else 0.0
    return TaxaFalha(tentativas=tentativas, falhas=falhas, percentual=pct)


def _fila(db: Session, agora: datetime) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(Agendamento)
            .where(Agendamento.status == "aprovado", Agendamento.executar_em <= agora)
        ).scalar_one()
    )


def _gasto_mes(db: Session, desde_mes: datetime, tarifa: float) -> GastoMes:
    n = int(
        db.execute(
            select(func.count())
            .select_from(Envio)
            .where(Envio.status.in_(_SUCESSO_COBRADO), Envio.criado_em >= desde_mes)
        ).scalar_one()
    )
    return GastoMes(
        valor=round(n * tarifa, 3),
        moeda="BRL",
        estimado=True,
        base=f"{n} envio(s) com sucesso × R$ {tarifa:.3f} (tarifa UTILITY, §4.4)",
    )


@router.get("/deep", response_model=SaudeDeep)
def deep(db: Session = Depends(get_db)) -> SaudeDeep:
    """Retrato de saúde operacional (spec 0021, AC-2..AC-9). 401 sem sessão (dependência do router)."""
    agora = datetime.now(UTC)
    envios_hoje = _envios_por_status(db, _inicio_dia_sp(agora))
    return SaudeDeep(
        banco=_checar_banco(db),
        worker=_estado_worker(db, agora),
        envios_hoje=envios_hoje,
        taxa_falha_hoje=_taxa_falha(envios_hoje),
        fila=_fila(db, agora),
        gasto_mes_estimado=_gasto_mes(db, _inicio_mes_sp(agora), get_settings().tarifa_utility_brl),
    )
