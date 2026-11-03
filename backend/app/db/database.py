"""Camada de acesso ao banco (SQLAlchemy 2) — engine, sessão e Base declarativa.

O engine é criado de forma preguiçosa (só conecta no primeiro uso), então importar este
módulo não exige um banco disponível. A URL vem de `Settings.database_url` (BRIEFING §15).
Migrações são sempre via Alembic (CLAUDE.md §4.5); `create_all()` não é usado fora de testes.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa de todos os modelos. `Base.metadata` alimenta o autogenerate do Alembic."""


def get_db() -> Iterator[Session]:
    """Dependência FastAPI: abre uma sessão por requisição e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
