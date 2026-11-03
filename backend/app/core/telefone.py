"""Normalização E.164 e mascaramento de telefone (ADR 0006).

O E.164 canônico (ex.: ``+5511987654321``) é a chave de deduplicação de contato.
O mascaramento protege PII (telefone) em logs e auditoria (CLAUDE §6 / AC-16).
"""

from __future__ import annotations

import phonenumbers


def normalizar_e164(raw: str, regiao: str = "BR") -> str:
    """Normaliza um telefone em texto livre para o E.164 canônico.

    Aceita variações de formatação (espaços, parênteses, com/sem ``+55``). Levanta
    ``ValueError`` se o número for vazio, não parseável ou inválido — a camada de API
    traduz isso em 422 (AC-2).
    """
    try:
        numero = phonenumbers.parse(raw, regiao)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("telefone inválido") from exc
    if not phonenumbers.is_valid_number(numero):
        raise ValueError("telefone inválido")
    return phonenumbers.format_number(numero, phonenumbers.PhoneNumberFormat.E164)


def mascarar_telefone(e164: str) -> str:
    """Mascara o miolo de um telefone para log/auditoria.

    Mantém DDI+DDD+1º dígito e os 4 últimos; mascara o resto. Ex.:
    ``+5511999990000`` -> ``+55119****0000``. Nunca registrar o número completo (§6).
    """
    if len(e164) <= 10:
        # Número curto/atípico: preserva no máximo os 2 últimos dígitos.
        return e164[:2] + "*" * max(0, len(e164) - 4) + e164[-2:]
    return e164[:6] + "*" * (len(e164) - 10) + e164[-4:]
