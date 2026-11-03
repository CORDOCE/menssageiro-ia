"""Testes de `core/telefone.py`: normalização E.164 (dedup) e mascaramento (logs/PII).

Regras de domínio (spec 0002 AC-1, AC-16; ADR 0006). Unitário puro, sem banco.
"""

import pytest

from app.core.telefone import mascarar_telefone, normalizar_e164


def test_normalizar_variacoes_br_para_mesmo_canonico():
    # Formatações diferentes do mesmo número devem colapsar no mesmo E.164 canônico.
    canonico = "+5511987654321"
    for entrada in ["(11) 98765-4321", "11 98765-4321", "+55 11 98765-4321", "5511987654321"]:
        assert normalizar_e164(entrada) == canonico


def test_normalizar_invalido_levanta_valueerror():
    with pytest.raises(ValueError):
        normalizar_e164("123")


def test_normalizar_vazio_levanta_valueerror():
    with pytest.raises(ValueError):
        normalizar_e164("")


def test_mascarar_telefone_oculta_miolo():
    # AC-16: mantém DDI+DDD+1 e os 4 últimos; mascara o miolo.
    assert mascarar_telefone("+5511999990000") == "+55119****0000"
