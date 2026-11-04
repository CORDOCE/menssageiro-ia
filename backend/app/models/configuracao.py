"""Modelo `Configuracao` (BRIEFING §9; ADR 0008; spec 0004).

Linha **única** (`id="default"`) com os controles de envio que o worker lê **a cada ciclo** (§5.6):
janela de horário (JSONB), limite diário, limite por contato (`NULL` = sem limite) e pausa geral.
Fonte única runtime (ADR 0008); a env `LIMITE_DIARIO` só semeia o `limite_diario` inicial.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

ID_CONFIG = "default"
# dias em Python weekday() (0=segunda … 6=domingo); padrão seg–sáb 08:00–20:00 (BRIEFING §10.3).
JANELA_PADRAO: dict[str, Any] = {"dias": [0, 1, 2, 3, 4, 5], "inicio": "08:00", "fim": "20:00"}


class Configuracao(Base):
    __tablename__ = "configuracoes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=ID_CONFIG)
    janela_envio: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=lambda: dict(JANELA_PADRAO)
    )
    limite_diario: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    limite_por_contato_dia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    envios_pausados: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
