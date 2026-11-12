"""Anexo de agendamento (spec 0025 / ADR 0016): PDF (boleto) guardado em `bytea` até o disparo.

O worker sobe à Meta (`upload_midia`) no momento do envio e o inclui no cabeçalho DOCUMENT do template.
Só PDF no v1. O backend nunca executa/parseia o conteúdo — só valida o header e o repassa.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Anexo(Base):
    __tablename__ = "anexos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamanho: Mapped[int] = mapped_column(Integer, nullable=False)
    conteudo: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
