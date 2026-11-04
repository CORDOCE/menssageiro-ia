"""Cálculo de recorrência via RRULE (spec 0005, ADR 0009).

A regra de recorrência é uma **string RRULE** (iCalendar — BRIEFING §9), ex.: `FREQ=MONTHLY;BYMONTHDAY=5`.
O cálculo roda em **America/Sao_Paulo** (`zoneinfo`, como `services/janela.py`) para honrar "toda segunda" /
"dia 5" no fuso certo, e devolve `datetime` **aware em UTC** (as datas no banco são `timestamptz` — §8).

`UNTIL`, quando presente na regra, **deve estar em UTC** (sufixo `Z`): o `dateutil` exige que a
awareness do `UNTIL` combine com a do `dtstart` (aqui aware), então `UNTIL` naive é rejeitado como inválido.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr

_TZ = ZoneInfo("America/Sao_Paulo")
# dtstart de referência (aware) para validar a regra isolada: garante que UNTIL naive seja rejeitado
# com a mesma semântica usada no cálculo (dtstart sempre aware).
_DTSTART_REF = datetime(2000, 1, 1, tzinfo=_TZ)


def _em_sp(momento: datetime) -> datetime:
    """Normaliza para aware em America/Sao_Paulo (naive é assumido UTC, como em `services/janela.py`)."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(_TZ)


def validar_regra(regra: str) -> None:
    """Valida a RRULE. Levanta `ValueError` se a sintaxe for inválida ou `UNTIL` não for UTC (§4 → 422)."""
    rrulestr(regra, dtstart=_DTSTART_REF)


def proxima_ocorrencia(regra: str, dtstart: datetime, apos: datetime) -> datetime | None:
    """Próxima ocorrência **estritamente após `apos`**, ou `None` se a série esgotou (`UNTIL`/`COUNT`).

    `dtstart` é o início da série (1ª ocorrência); define o horário e serve de âncora para `BYDAY`/
    `BYMONTHDAY`. Cálculo em America/Sao_Paulo; retorno aware em UTC.
    """
    regra_rr = rrulestr(regra, dtstart=_em_sp(dtstart))
    proxima = regra_rr.after(_em_sp(apos), inc=False)
    return proxima.astimezone(UTC) if proxima is not None else None
