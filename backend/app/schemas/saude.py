"""Schemas Pydantic da saúde profunda (spec 0021 / BRIEFING §12).

Resposta de `GET /admin/health/deep`: retrato operacional montado no endpoint a partir do banco
(`saude`, `envios`, `agendamentos`). Só leitura; nenhum campo vem direto do ORM.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BancoSaude(BaseModel):
    status: str  # "ok" | "erro"


class WorkerSaude(BaseModel):
    status: str  # "vivo" | "parado" | "desconhecido"
    ultimo_ciclo_em: datetime | None
    segundos_desde: int | None


class TaxaFalha(BaseModel):
    tentativas: int
    falhas: int
    percentual: float


class GastoMes(BaseModel):
    valor: float
    moeda: str
    estimado: bool
    base: str  # descrição legível do cálculo (nº de envios × tarifa)


class SaudeDeep(BaseModel):
    banco: BancoSaude
    worker: WorkerSaude
    envios_hoje: dict[str, int]  # status → contagem (dia-calendário SP)
    taxa_falha_hoje: TaxaFalha
    fila: int  # agendamentos aprovados já vencidos à espera do worker
    gasto_mes_estimado: GastoMes
