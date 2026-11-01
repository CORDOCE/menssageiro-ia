"""Fixtures de teste: banco PostgreSQL dedicado (`<db>_test`), criado/dropado por sessão.

Repontamos `engine`/`SessionLocal` globais para o banco de teste — assim tanto `get_db` quanto a
auditoria (que abre sua própria sessão) usam o mesmo banco. Isolamento por TRUNCATE antes de cada teste.
"""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.db.database as db_mod
from app.core.config import get_settings
from app.db.database import Base
from app.main import app
from app.models.saude import Saude  # noqa: F401 (registra a tabela no create_all)


def _url_teste(url: str) -> str:
    base, _, nome = url.rpartition("/")
    return f"{base}/{nome}_test"


def _criar_banco_teste(url: str) -> None:
    raw = url.replace("postgresql+psycopg://", "postgresql://")
    base, _, nome = raw.rpartition("/")
    with psycopg.connect(f"{base}/postgres", autocommit=True) as conn:
        existe = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (f"{nome}_test",)).fetchone()
        if not existe:
            conn.execute(f'CREATE DATABASE "{nome}_test"')


@pytest.fixture(scope="session", autouse=True)
def _preparar_banco():
    url = get_settings().database_url
    _criar_banco_teste(url)
    engine = create_engine(_url_teste(url))
    db_mod.engine = engine
    db_mod.SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db():
    """Sessão de teste; limpa as tabelas antes de cada teste para isolamento."""
    sessao = db_mod.SessionLocal()
    sessao.execute(text("TRUNCATE usuarios, sessoes_usuario, auditoria, saude RESTART IDENTITY CASCADE"))
    sessao.commit()
    try:
        yield sessao
    finally:
        sessao.close()


@pytest.fixture
def client():
    return TestClient(app)
