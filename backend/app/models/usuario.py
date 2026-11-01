"""Modelos de autenticação (ADR 0001): usuário admin e sessões.

Sessão = token opaco guardado no banco (não JWT, não cookie). Simplificado para 1 admin, sem papéis.
`totp_secret` e `telefone_whatsapp` (BRIEFING §9) ficam nullable; o 2FA é cabeado na task 6.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telefone_whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessoes: Mapped[list[SessaoUsuario]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class SessaoUsuario(Base):
    __tablename__ = "sessoes_usuario"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="sessoes")
