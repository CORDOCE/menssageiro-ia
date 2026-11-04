"""Serviço de recorrência (spec 0005, AC-2..AC-5): cálculo da próxima ocorrência via RRULE.

Unitário, sem banco. Datas de referência (2026): 11-03 = terça, 11-09 = segunda, 11-16 = segunda.
Cálculo em America/Sao_Paulo (honra "toda segunda"/"dia 5" no fuso certo); devolve aware/UTC (§8).
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.recorrencia import proxima_ocorrencia, validar_regra

SP = ZoneInfo("America/Sao_Paulo")


def _sp(mes: int, dia: int, hora: int = 9, minuto: int = 0) -> datetime:
    return datetime(2026, mes, dia, hora, minuto, tzinfo=SP)


# --- proxima_ocorrencia: núcleo RRULE (AC-2) ---
def test_diaria_proxima_e_dia_seguinte():
    r = proxima_ocorrencia("FREQ=DAILY", _sp(11, 3), _sp(11, 3))
    assert r == _sp(11, 4).astimezone(UTC)


def test_semanal_byday_segunda_pula_para_proxima_segunda():
    r = proxima_ocorrencia("FREQ=WEEKLY;BYDAY=MO", _sp(11, 9), _sp(11, 9))
    assert r == _sp(11, 16).astimezone(UTC)


def test_mensal_bymonthday_5_vai_para_mes_seguinte():
    r = proxima_ocorrencia("FREQ=MONTHLY;BYMONTHDAY=5", _sp(11, 5), _sp(11, 5))
    assert r == _sp(12, 5).astimezone(UTC)


def test_intervalo_quinzenal_soma_14_dias():
    r = proxima_ocorrencia("FREQ=WEEKLY;INTERVAL=2", _sp(11, 3), _sp(11, 3))
    assert r == _sp(11, 17).astimezone(UTC)


def test_resultado_e_aware_utc():
    r = proxima_ocorrencia("FREQ=DAILY", _sp(11, 3), _sp(11, 3))
    assert r is not None and r.tzinfo is UTC


def test_apos_naive_assumido_utc():
    # `apos` sem tz é tratado como UTC (não quebra).
    r = proxima_ocorrencia("FREQ=DAILY", _sp(11, 3), datetime(2026, 11, 3, 12, 0))
    assert r == _sp(11, 4).astimezone(UTC)


# --- esgotamento da série → None (AC-3) ---
def test_until_no_passado_esgota_para_none():
    assert proxima_ocorrencia("FREQ=DAILY;UNTIL=20261101T000000Z", _sp(11, 3), _sp(11, 3)) is None


def test_count_1_esgota_para_none():
    assert proxima_ocorrencia("FREQ=DAILY;COUNT=1", _sp(11, 3), _sp(11, 3)) is None


# --- validar_regra (AC-4) ---
def test_validar_regra_invalida_levanta():
    with pytest.raises(ValueError):
        validar_regra("FREQ=BANANA")


def test_validar_regra_valida_nao_levanta():
    validar_regra("FREQ=WEEKLY;BYDAY=MO;UNTIL=20270101T000000Z")


# --- borda fuso/DST: UNTIL deve ser UTC (Z); naive é rejeitada (AC-5) ---
def test_until_aware_z_funciona():
    r = proxima_ocorrencia("FREQ=DAILY;UNTIL=20261231T000000Z", _sp(11, 3), _sp(11, 3))
    assert r == _sp(11, 4).astimezone(UTC)


def test_until_naive_rejeitada():
    with pytest.raises(ValueError):
        validar_regra("FREQ=DAILY;UNTIL=20261231T000000")
