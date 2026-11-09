"""Schemas Pydantic de agendamentos (spec 0004).

A regra `contato_id` **xor** `grupo` vive no schema (vira 422 no endpoint — AC-4), espelhando o `CHECK`
do banco. O agendamento nasce `aprovado`; quem envia é o worker (§5.1).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Cap defensivo (§6/R1): cada variável limitada em tamanho; a lista limitada em nº de itens.
_Variavel = Annotated[str, StringConstraints(max_length=1000)]


class AgendamentoCriar(BaseModel):
    contato_id: str | None = None
    grupo: str | None = None
    modelo_id: str
    variaveis: list[_Variavel] = Field(default_factory=list, max_length=50)
    executar_em: datetime
    origem: str = "operador"
    # string RRULE (spec 0005); None = avulso. Cap defensivo (§6): RRULE é curta.
    recorrencia: str | None = Field(default=None, max_length=500)

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
    recorrencia: str | None
    agendamento_pai_id: str | None
    reagendamentos: int
    motivo_ultima_transicao: str | None
    criado_em: datetime
