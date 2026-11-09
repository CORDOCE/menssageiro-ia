"""Janela de envio e configuração runtime (spec 0004, ADR 0008).

Comparações sempre em **America/Sao_Paulo** (`zoneinfo`, sem dependência nova); as datas no banco são
`timestamptz`. A janela é `[inicio, fim)` (início inclusive, fim exclusivo) nos dias de semana permitidos
(`dias` em `weekday()`, 0=segunda). `proximo_inicio` (reagenda) e `inicio_dia_seguinte` (adia por limite)
devolvem `datetime` **aware em UTC**.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.configuracao import ID_CONFIG, Configuracao

_TZ = ZoneInfo("America/Sao_Paulo")


def _parse_hora(texto: str) -> time:
    horas, minutos = texto.split(":")
    return time(int(horas), int(minutos))


def _em_sp(agora: datetime) -> datetime:
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=UTC)
    return agora.astimezone(_TZ)


def dentro_da_janela(agora: datetime, janela: dict[str, Any]) -> bool:
    """True se `agora` cai num dia permitido e em `[inicio, fim)` (fim exclusivo → 20:00 fica fora)."""
    sp = _em_sp(agora)
    if sp.weekday() not in janela["dias"]:
        return False
    return _parse_hora(janela["inicio"]) <= sp.time() < _parse_hora(janela["fim"])


def proximo_inicio(agora: datetime, janela: dict[str, Any]) -> datetime:
    """Próximo início de janela válida **>= agora** (usado no reagenda). Devolve UTC."""
    sp = _em_sp(agora)
    inicio = _parse_hora(janela["inicio"])
    for delta in range(8):
        dia = sp.date() + timedelta(days=delta)
        if dia.weekday() in janela["dias"]:
            inicio_dt = datetime.combine(dia, inicio, tzinfo=_TZ)
            if inicio_dt >= sp:
                return inicio_dt.astimezone(UTC)
    raise ValueError("janela sem dias válidos")


def inicio_dia_seguinte(agora: datetime, janela: dict[str, Any]) -> datetime:
    """Início da janela do **próximo dia válido a partir de amanhã** (usado no adia). Devolve UTC."""
    sp = _em_sp(agora)
    inicio = _parse_hora(janela["inicio"])
    amanha = sp.date() + timedelta(days=1)
    for delta in range(8):
        dia = amanha + timedelta(days=delta)
        if dia.weekday() in janela["dias"]:
            return datetime.combine(dia, inicio, tzinfo=_TZ).astimezone(UTC)
    raise ValueError("janela sem dias válidos")


def obter_configuracao(db: Session) -> Configuracao:
    """Lê a linha única de `configuracoes`; cria com defaults (semeando `limite_diario` do env) se faltar.

    Em bancos migrados a linha já existe (seed da migração); o create-if-missing cobre o caminho de
    `create_all` (testes) e qualquer ambiente sem o seed.
    """
    cfg = db.get(Configuracao, ID_CONFIG)
    if cfg is None:
        cfg = Configuracao(
            id=ID_CONFIG,
            limite_diario=get_settings().limite_diario_default,
            limite_por_agendamento_dia=get_settings().limite_por_agendamento_default,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg
