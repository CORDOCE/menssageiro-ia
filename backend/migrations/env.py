from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.db.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata para o autogenerate. Importar os modelos aqui conforme forem criados, para o
# autogenerate enxergar as tabelas. Ex. (task 5): from app.models import usuario  # noqa: F401
target_metadata = Base.metadata


def get_database_url() -> str:
    """URL do banco a partir de Settings (CLAUDE.md §6: segredos só em env).

    Lida direto do Settings — NÃO via configparser do Alembic (`sqlalchemy.url`), que faz
    interpolação de `%` e quebraria com senhas contendo `%` (ex.: DATABASE_URL da Railway).
    """
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (gera SQL a partir só da URL, sem engine)."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (engine real, conexão com o banco)."""
    connectable = create_engine(get_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
