"""Saúde do worker (task 8): heartbeat do loop. Linha única, atualizada a cada ciclo.

Em memória nunca (BRIEFING §5); a tela "Saúde do sistema" (fase posterior) lê daqui.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Saude(Base):
    __tablename__ = "saude"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ultimo_ciclo_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
