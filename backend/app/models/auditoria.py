"""Registro de auditoria (BRIEFING §9). Invariante CLAUDE.md §5.8: toda ação que muda estado grava aqui."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    ator_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    operacao: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    alvo_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alvo_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), server_default="success", nullable=False)
    metadados: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
