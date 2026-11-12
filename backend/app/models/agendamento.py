"""Modelo `Agendamento` (BRIEFING §9; ADR 0005, ADR 0008; spec 0004).

Um agendamento é para um `contato_id` **xor** um `grupo` (rótulo dinâmico, resolvido no disparo) — garantido
por `CHECK`. Usa um `modelo` aprovado e `executar_em`. O worker (Fase 4) trava os vencidos com
`FOR UPDATE SKIP LOCKED` e expande o grupo em `envios` idempotentes. As colunas `agendamento_pai_id` e
`recorrencia` nascem **inertes** (recorrência = spec 0005, ADR 0008: "definir antes das migrations").
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Agendamento(Base):
    __tablename__ = "agendamentos"
    __table_args__ = (
        CheckConstraint(
            "(contato_id IS NOT NULL) <> (grupo IS NOT NULL)",
            name="ck_agendamentos_contato_xor_grupo",
        ),
        # Dedup das ocorrências de uma série recorrente (spec 0005, ADR 0005/0009): uma só ocorrência
        # por (raiz, horário). Parcial: mães/avulsos (agendamento_pai_id NULL) não conflitam entre si.
        Index(
            "uq_agendamentos_serie_ocorrencia",
            "agendamento_pai_id",
            "executar_em",
            unique=True,
            postgresql_where=text("agendamento_pai_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contato_id: Mapped[str | None] = mapped_column(ForeignKey("contatos.id"), nullable=True)
    grupo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modelo_id: Mapped[str] = mapped_column(ForeignKey("modelos.id"), nullable=False)
    # Anexo PDF (spec 0024 / ADR 0016): obrigatório quando o modelo tem cabeçalho DOCUMENT (NULL se não).
    anexo_id: Mapped[str | None] = mapped_column(ForeignKey("anexos.id"), nullable=True)
    variaveis: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    executar_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="aprovado", nullable=False)
    origem: Mapped[str] = mapped_column(String(20), default="operador", nullable=False)
    criado_por: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    aprovado_por: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    motivo_ultima_transicao: Mapped[str | None] = mapped_column(Text, nullable=True)
    reagendamentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Recorrência (spec 0005, ADR 0005/0009): `recorrencia` = string RRULE (NULL = avulso);
    # `agendamento_pai_id` aponta para a raiz da série (a mãe tem NULL). Dedup pelo índice parcial acima.
    agendamento_pai_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recorrencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
