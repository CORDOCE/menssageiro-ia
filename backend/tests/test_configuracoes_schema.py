"""Testes dos schemas de configuração (spec 0018, task 1).

Validação pura de Pydantic (sem banco): janela no mesmo dia, limites com cap,
distinção entre campo ausente (não mexe) e `null` explícito, e corpo vazio.
Cobre AC-6, AC-7, AC-9 e a matriz de decisão da spec.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.configuracao import ConfiguracaoPatch


def _patch(**campos: object) -> ConfiguracaoPatch:
    return ConfiguracaoPatch.model_validate(campos)


# --- Janela ---------------------------------------------------------------

def test_janela_valida() -> None:
    p = _patch(janela_envio={"dias": [0, 1, 2, 3, 4], "inicio": "09:00", "fim": "18:00"})
    assert p.janela_envio is not None
    assert p.janela_envio.dias == [0, 1, 2, 3, 4]


def test_janela_dias_fora_de_ordem_normaliza() -> None:
    p = _patch(janela_envio={"dias": [5, 0, 2], "inicio": "08:00", "fim": "20:00"})
    assert p.janela_envio is not None
    assert p.janela_envio.dias == [0, 2, 5]


@pytest.mark.parametrize(
    "janela",
    [
        {"dias": [], "inicio": "08:00", "fim": "20:00"},          # dias vazio
        {"dias": [7], "inicio": "08:00", "fim": "20:00"},         # fora de 0..6
        {"dias": [-1], "inicio": "08:00", "fim": "20:00"},        # fora de 0..6
        {"dias": [0, 0, 1], "inicio": "08:00", "fim": "20:00"},   # duplicado
        {"dias": [0, 1], "inicio": "18:00", "fim": "09:00"},      # fim <= inicio
        {"dias": [0, 1], "inicio": "08:00", "fim": "08:00"},      # fim == inicio
        {"dias": [0, 1], "inicio": "25:00", "fim": "20:00"},      # hora inválida
        {"dias": [0, 1], "inicio": "8:0", "fim": "20:00"},        # formato
        {"dias": [0, 1], "inicio": "08:00:00", "fim": "20:00"},   # com segundos
        {"dias": [1.5], "inicio": "08:00", "fim": "20:00"},       # dia não-inteiro
        {"dias": [True, False], "inicio": "08:00", "fim": "20:00"},  # bool não é dia
        {"dias": ["1", "2"], "inicio": "08:00", "fim": "20:00"},  # string não é dia
    ],
)
def test_janela_invalida(janela: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _patch(janela_envio=janela)


# --- Limites --------------------------------------------------------------

def test_limite_diario_valido() -> None:
    assert _patch(limite_diario=500).limite_diario == 500


@pytest.mark.parametrize("valor", [0, -1, 100001])
def test_limite_diario_invalido(valor: int) -> None:
    with pytest.raises(ValidationError):
        _patch(limite_diario=valor)


@pytest.mark.parametrize("campo", ["limite_diario", "envios_pausados", "janela_envio"])
def test_campo_not_null_null_explicito_rejeitado(campo: str) -> None:
    # Campos NOT NULL no modelo: null explícito é 422 (≠ ausente, que não mexe).
    with pytest.raises(ValidationError):
        _patch(**{campo: None})


def test_limite_por_contato_null_remove_limite() -> None:
    p = _patch(limite_por_contato_dia=None)
    assert "limite_por_contato_dia" in p.model_fields_set
    assert p.limite_por_contato_dia is None


def test_limite_por_agendamento_null_remove_teto() -> None:
    p = _patch(limite_por_agendamento_dia=None)
    assert "limite_por_agendamento_dia" in p.model_fields_set
    assert p.limite_por_agendamento_dia is None


@pytest.mark.parametrize("campo", ["limite_por_contato_dia", "limite_por_agendamento_dia"])
def test_limites_opcionais_zero_invalido(campo: str) -> None:
    with pytest.raises(ValidationError):
        _patch(**{campo: 0})


# --- Corpo / campos -------------------------------------------------------

def test_corpo_vazio_rejeitado() -> None:
    with pytest.raises(ValidationError):
        _patch()


def test_campo_desconhecido_rejeitado() -> None:
    with pytest.raises(ValidationError):
        _patch(id="outro")


def test_patch_parcial_so_pausa() -> None:
    p = _patch(envios_pausados=True)
    assert p.model_fields_set == {"envios_pausados"}
    assert p.envios_pausados is True
