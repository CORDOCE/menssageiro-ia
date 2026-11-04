"""Modelo `Envio` (spec 0003 / ADR 0005 estendida pela ADR 0007).

Um envio é identificado pelo `wamid` (id da Meta) para casar os eventos de status do webhook.
`agendamento_id` é nullable (envios avulsos/de teste da Fase 3 não têm agendamento); a unicidade
`(agendamento_id, contato_id)` da ADR 0005 vira índice **parcial** (só quando há agendamento), para
não travar os avulsos. A FK para `agendamentos` foi adicionada na Fase 4 (spec 0004); `NULL` nos avulsos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Envio(Base):
    __tablename__ = "envios"
    __table_args__ = (
        Index(
            "uq_envios_agendamento_contato",
            "agendamento_id",
            "contato_id",
            unique=True,
            postgresql_where=text("agendamento_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contato_id: Mapped[str] = mapped_column(ForeignKey("contatos.id"), index=True, nullable=False)
    modelo_id: Mapped[str | None] = mapped_column(ForeignKey("modelos.id"), nullable=True)
    agendamento_id: Mapped[str | None] = mapped_column(
        ForeignKey("agendamentos.id"), nullable=True
    )
    wamid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="criado", nullable=False)
    pricing: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    conversation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    erro_codigo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    erro_motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
