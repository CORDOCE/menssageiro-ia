"""Janela de envio e config runtime (spec 0004, AC-12/AC-13 parcial): bordas de horário/semana + singleton.

Datas de referência (2026): 11-03 = terça, 11-04 = quarta, 11-07 = sábado, 11-08 = domingo, 11-09 = segunda.
"""

from datetime import UTC, datetime

from app.models.configuracao import JANELA_PADRAO
from app.services.janela import (
    _TZ,
    dentro_da_janela,
    inicio_dia_seguinte,
    obter_configuracao,
    proximo_inicio,
)

J = JANELA_PADRAO  # seg–sáb 08:00–20:00


def _sp(mes: int, dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, mes, dia, hora, minuto, tzinfo=_TZ)


def _assert_sp(dt: datetime, mes: int, dia: int, hora: int) -> None:
    sp = dt.astimezone(_TZ)
    assert (sp.month, sp.day, sp.hour, sp.minute) == (mes, dia, hora, 0)


def test_dentro_dia_util_meio():
    assert dentro_da_janela(_sp(11, 3, 10), J) is True


def test_dentro_fim_exclusivo():
    # 20:00 exato = fim → fora (reagenda).
    assert dentro_da_janela(_sp(11, 3, 20), J) is False


def test_dentro_inicio_inclusivo():
    assert dentro_da_janela(_sp(11, 3, 8), J) is True


def test_fora_antes_do_inicio():
    assert dentro_da_janela(_sp(11, 3, 7, 59), J) is False


def test_fora_domingo():
    assert dentro_da_janela(_sp(11, 8, 10), J) is False


def test_dentro_converte_de_utc():
    # 13:00 UTC = 10:00 em America/Sao_Paulo (UTC-3) → dentro.
    assert dentro_da_janela(datetime(2026, 11, 3, 13, 0, tzinfo=UTC), J) is True


def test_proximo_inicio_apos_fim_vai_para_amanha():
    _assert_sp(proximo_inicio(_sp(11, 3, 21), J), 11, 4, 8)  # ter 21h → qua 08h


def test_proximo_inicio_antes_do_inicio_e_hoje():
    _assert_sp(proximo_inicio(_sp(11, 3, 6), J), 11, 3, 8)  # ter 06h → ter 08h


def test_proximo_inicio_sabado_noite_pula_domingo():
    _assert_sp(proximo_inicio(_sp(11, 7, 21), J), 11, 9, 8)  # sáb 21h → seg 08h


def test_inicio_dia_seguinte_dia_util():
    _assert_sp(inicio_dia_seguinte(_sp(11, 3, 10), J), 11, 4, 8)  # ter → qua 08h


def test_inicio_dia_seguinte_sabado_pula_domingo():
    _assert_sp(inicio_dia_seguinte(_sp(11, 7, 10), J), 11, 9, 8)  # sáb → seg 08h


def test_obter_configuracao_cria_singleton_com_semente(db):
    cfg = obter_configuracao(db)
    assert cfg.limite_diario == 200  # semente do env (default)
    assert cfg.envios_pausados is False
    # idempotente: segunda chamada não duplica.
    obter_configuracao(db)
    from app.models.configuracao import Configuracao

    assert db.query(Configuracao).count() == 1
