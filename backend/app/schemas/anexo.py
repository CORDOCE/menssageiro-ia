"""Schemas de anexo (spec 0025). Resposta do upload — nunca devolve o conteúdo (bytes)."""

from __future__ import annotations

from pydantic import BaseModel


class AnexoRead(BaseModel):
    id: str
    nome_arquivo: str
    tamanho: int
