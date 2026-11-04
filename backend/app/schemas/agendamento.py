"""Schemas Pydantic de agendamentos (spec 0004).

A regra `contato_id` **xor** `grupo` vive no schema (vira 422 no endpoint — AC-4), espelhando o `CHECK`
do banco. O agendamento nasce `aprovado`; quem envia é o worker (§5.1).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgendamentoCriar(BaseModel):
    contato_id: str | None = None
    grupo: str | None = None
    modelo_id: str
    variaveis: list[str] = Field(default_factory=list)
    executar_em: datetime
    origem: str = "operador"

    @model_validator(mode="after")
    def _contato_xor_grupo(self) -> AgendamentoCriar:
        if (self.contato_id is None) == (self.grupo is None):
            raise ValueError("informe exatamente um de contato_id ou grupo")
        return self


class AgendamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contato_id: str | None
    grupo: str | None
    modelo_id: str
    variaveis: list[str]
    executar_em: datetime
    status: str
    origem: str
    reagendamentos: int
    motivo_ultima_transicao: str | None
    criado_em: datetime
