"""Schemas Pydantic de envios (spec 0014): leitura do histórico.

`StatusEnvio` espelha os status internos mapeados do webhook (`webhook_meta.py`); usá-lo no Query
dá 422 para valor fora do conjunto (AC de borda). `EnvioRead` é montado a partir do join
contato/modelo no endpoint (não vem direto do ORM), por isso sem `from_attributes`.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class StatusEnvio(StrEnum):
    criado = "criado"
    enviando = "enviando"
    enviado = "enviado"
    entregue = "entregue"
    lido = "lido"
    aguardando_retry = "aguardando_retry"  # reenvio automático pendente (spec 0020)
    aguardando_decisao = "aguardando_decisao"  # esgotou/ambíguo → decisão humana (spec 0020)
    falhou = "falhou"


class EnvioRead(BaseModel):
    id: str
    contato_id: str
    contato_nome: str
    contato_telefone: str
    modelo_id: str | None
    modelo_nome: str | None
    status: str
    erro_codigo: str | None
    erro_motivo: str | None
    criado_em: datetime
