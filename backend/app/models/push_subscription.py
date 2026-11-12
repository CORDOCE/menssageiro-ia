"""Inscrição de Web Push (spec 0023 / ADR 0015): um dispositivo inscrito para receber notificações.

Múltiplos dispositivos por operador (celular + desktop). `endpoint` (único) identifica a inscrição no
push service do browser; `p256dh`/`auth` são as chaves do cliente para cifrar a mensagem (RFC 8291).
Inscrições que o push service rejeita (404/410) são removidas no envio.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
