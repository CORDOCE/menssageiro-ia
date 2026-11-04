"""Modelo `Modelo` (templates da Meta; BRIEFING §9, spec 0003 / ADR 0007).

Espelha o template aprovado na Cloud API: status Meta (rascunho→pendente→aprovado/rejeitado/pausado),
categoria UTILITY e idioma pt_BR (invariante §5.3). Único por (nome, idioma).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Modelo(Base):
    __tablename__ = "modelos"
    __table_args__ = (UniqueConstraint("nome", "idioma", name="uq_modelos_nome_idioma"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    idioma: Mapped[str] = mapped_column(String(10), default="pt_BR", nullable=False)
    categoria: Mapped[str] = mapped_column(String(20), default="UTILITY", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="rascunho", nullable=False)
    corpo: Mapped[str] = mapped_column(Text, nullable=False)
    cabecalho_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    variaveis: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    motivo_rejeicao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
