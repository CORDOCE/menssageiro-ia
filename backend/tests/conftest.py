"""Fixtures de teste: banco PostgreSQL dedicado (`<db>_test`), criado/dropado por sessão.

Repontamos `engine`/`SessionLocal` globais para o banco de teste — assim tanto `get_db` quanto a
auditoria (que abre sua própria sessão) usam o mesmo banco. Isolamento por TRUNCATE antes de cada teste.
"""

import os

# Define uma origem de frontend ANTES de importar o app (get_settings é cacheada no import),
# para que o CORS tenha uma origem liberada nos testes.
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

# Chave de cifra do totp_secret (ADR 0011) p/ os testes que exercitam a cifra (get_settings é cacheada).
from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("TOTP_ENC_KEY", Fernet.generate_key().decode())

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.db.database as db_mod  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.database import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.agendamento import Agendamento  # noqa: E402, F401 (registra a tabela no create_all)
from app.models.configuracao import Configuracao  # noqa: E402, F401 (registra a tabela no create_all)
from app.models.contato import Contato  # noqa: E402, F401 (registra a tabela no create_all)
from app.models.envio import Envio  # noqa: E402, F401 (registra a tabela no create_all)
from app.models.modelo import Modelo  # noqa: E402, F401 (registra a tabela no create_all)
from app.models.saude import Saude  # noqa: E402, F401 (registra a tabela no create_all)


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
    sessao.execute(
        text(
            "TRUNCATE usuarios, sessoes_usuario, auditoria, saude, contatos, modelos, envios, "
            "agendamentos, configuracoes RESTART IDENTITY CASCADE"
        )
    )
    sessao.commit()
    try:
        yield sessao
    finally:
        sessao.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(db):
    """Cria um admin + sessão válida no banco e devolve o header de **cookie** de sessão (ADR 0012)."""
    import uuid
    from datetime import UTC, datetime, timedelta

    from app.core.security import gerar_token_sessao
    from app.models.usuario import SessaoUsuario, Usuario

    usuario_id = str(uuid.uuid4())
    token = gerar_token_sessao()
    db.add(Usuario(id=usuario_id, nome="Admin", email="admin@teste.com", senha_hash="x", ativo=True))
    db.add(
        SessaoUsuario(
            id=str(uuid.uuid4()),
            usuario_id=usuario_id,
            token=token,
            expira_em=datetime.now(UTC) + timedelta(days=7),
        )
    )
    db.commit()
    return {"Cookie": f"sessao={token}"}
