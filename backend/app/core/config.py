"""Configuração central lida de variáveis de ambiente (BRIEFING §15, RAILWAY §8).

As variáveis da Meta/OpenAI são opcionais nesta fase: a API precisa subir e responder
`/health` mesmo sem elas configuradas (spec 0001, AC-3). Segredos nunca têm default real.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco. Default = PostgreSQL local do docker-compose (porta 5434). Em staging/produção,
    # a Railway injeta DATABASE_URL e sobrescreve este default (RAILWAY.md).
    database_url: str = "postgresql+psycopg://mensageiro:mensageiro@localhost:5434/mensageiro"

    # WhatsApp Cloud API (Meta) — opcionais até a fase 3
    whatsapp_token: str | None = None
    phone_number_id: str | None = None
    waba_id: str | None = None
    app_secret: str | None = None
    webhook_verify_token: str | None = None
    graph_api_version: str | None = None
    admin_whatsapp_numbers: str | None = None

    # IA (OpenAI) — opcionais até a fase 6
    openai_api_key: str | None = None
    openai_model: str = "gpt-6-luna"

    # E-mail / URLs / observabilidade — opcionais nesta fase
    resend_api_key: str | None = None
    email_from: str | None = None
    email_alertas: str | None = None
    frontend_url: str | None = None
    api_url: str | None = None
    sentry_dsn: str | None = None
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None

    # Fuso (BRIEFING §9: exibição em America/Sao_Paulo)
    tz: str = "America/Sao_Paulo"


@lru_cache
def get_settings() -> Settings:
    """Settings cacheada (lida uma vez por processo)."""
    return Settings()
