"""Modelo `Contato` (BRIEFING §9; spec 0002 / ADR 0005, ADR 0006).

`telefone_e164` é a identidade/dedup do contato (único). `consentimento` nasce ``False``
(importação nunca auto-consente, §5.9). Descadastro é soft (`descadastrado_em`), nunca hard
delete (§5.4). Mesmo estilo de `models/usuario.py`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Contato(Base):
    __tablename__ = "contatos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    telefone_e164: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    grupo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    consentimento: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consentimento_data: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consentimento_origem: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descadastrado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultima_mensagem_recebida_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
