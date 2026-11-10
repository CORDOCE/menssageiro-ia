"""Schemas Pydantic da configuração de envio (spec 0018).

Edição dos controles que o worker lê a cada ciclo (ADR 0008): janela, limites e pausa.
A validação de domínio vive aqui (vira 422 no endpoint), espelhando a semântica do modelo
`Configuracao`: janela no mesmo dia (`fim > inicio`), limites ≥ 1 com cap defensivo (§6),
e os limites opcionais aceitando `null` = "sem limite".
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

# Teto defensivo (§6): barra valores absurdos/erros de digitação sem travar uso real.
_LIMITE_MAX = 100_000
_Limite = Annotated[int, Field(ge=1, le=_LIMITE_MAX)]
_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")  # HH:MM 24h, sem segundos


class JanelaEnvio(BaseModel):
    """Janela de disparo (mesmo dia): dias da semana (0=segunda … 6=domingo) + [inicio, fim)."""

    model_config = ConfigDict(extra="forbid")

    # inteiros de verdade (sem coerção de bool/str/float); cap de 7 (só há 7 dias) corta
    # listas gigantes antes do validator — defesa contra DoS por payload grande (§6).
    dias: Annotated[list[StrictInt], Field(max_length=7)]
    inicio: str
    fim: str

    @field_validator("dias")
    @classmethod
    def _validar_dias(cls, dias: list[int]) -> list[int]:
        if not dias:
            raise ValueError("informe ao menos um dia")
        if len(set(dias)) != len(dias):
            raise ValueError("dias duplicados")
        if any(d < 0 or d > 6 for d in dias):
            raise ValueError("dia fora de 0..6 (0=segunda … 6=domingo)")
        return sorted(dias)

    @field_validator("inicio", "fim")
    @classmethod
    def _validar_hora(cls, valor: str) -> str:
        if not _HORA.match(valor):
            raise ValueError("hora deve estar no formato HH:MM (24h)")
        return valor

    @model_validator(mode="after")
    def _fim_maior_que_inicio(self) -> JanelaEnvio:
        if self.fim <= self.inicio:
            raise ValueError("fim deve ser maior que inicio (janela no mesmo dia)")
        return self


class ConfiguracaoPatch(BaseModel):
    """PATCH parcial: só os campos presentes mudam. Corpo vazio é rejeitado.

    `limite_diario` é NOT NULL → `null` explícito é inválido; os limites opcionais
    aceitam `null` (= sem limite). A distinção ausente/`null` usa `model_fields_set`.
    """

    model_config = ConfigDict(extra="forbid")

    # Campos NOT NULL no modelo: aceitam ausente (não mexe), mas não `null` explícito.
    _NAO_NULOS = ("janela_envio", "limite_diario", "envios_pausados")

    janela_envio: JanelaEnvio | None = None
    limite_diario: _Limite | None = None
    limite_por_contato_dia: _Limite | None = None
    limite_por_agendamento_dia: _Limite | None = None
    envios_pausados: bool | None = None

    @model_validator(mode="after")
    def _ao_menos_um_campo(self) -> ConfiguracaoPatch:
        if not self.model_fields_set:
            raise ValueError("nenhum campo para atualizar")
        return self

    @model_validator(mode="after")
    def _campos_not_null_nao_nulos(self) -> ConfiguracaoPatch:
        # Ausente = não mexe (ok); null explícito num campo NOT NULL = inválido (422, não 500).
        for campo in self._NAO_NULOS:
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo")
        return self


class ConfiguracaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    janela_envio: dict[str, object]
    limite_diario: int
    limite_por_contato_dia: int | None
    limite_por_agendamento_dia: int | None
    envios_pausados: bool
    atualizado_em: datetime
