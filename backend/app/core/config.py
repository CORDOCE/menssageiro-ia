"""Configuração central lida de variáveis de ambiente (BRIEFING §15, RAILWAY §8).

As variáveis da Meta/OpenAI são opcionais nesta fase: a API precisa subir e responder
`/health` mesmo sem elas configuradas (spec 0001, AC-3). Segredos nunca têm default real.
"""

from functools import lru_cache

from pydantic import Field
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
    # Versão da Graph API (ADR 0007). Confirmada na doc oficial 2026-11-03 (v26.0); configurável.
    graph_api_version: str = "v26.0"
    admin_whatsapp_numbers: str | None = None
    # Número de teste (E.164) — allowlist do POST /modelos/{id}/enviar-teste (§4: nunca número real).
    whatsapp_test_number: str | None = None

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

    # Autenticação (ADR 0001) + sessão multi-dispositivo (ADR 0004)
    session_inatividade_dias: int = 7  # expira após N dias sem uso (janela deslizante)
    session_max_dias: int = 30  # teto absoluto de vida da sessão, vence a renovação
    session_throttle_min: int = 5  # só renova ultimo_uso_em/expira_em se passou disso
    admin_email: str | None = None
    admin_password: str | None = None
    # Cifra do `totp_secret` em repouso (ADR 0011 / spec 0007). Chave(s) no formato Fernet; lista
    # separada por vírgula habilita rotação (MultiFernet: a 1ª cifra, qualquer uma decifra).
    totp_enc_key: str | None = None

    # Rate limit do login (task 7, CLAUDE.md §6): N falhas por e-mail dentro da janela → 429.
    login_max_tentativas: int = 5
    login_janela_min: int = 15

    # Worker (task 8): intervalo do loop de heartbeat.
    worker_intervalo_s: int = 60

    # Disparo (spec 0004 / ADR 0008): a env `LIMITE_DIARIO` é só a **semente** do `limite_diario`
    # inicial da linha de `configuracoes`. A fonte runtime é a tabela (operador muda sem redeploy).
    limite_diario_default: int = Field(default=200, validation_alias="LIMITE_DIARIO")
    # Teto de segurança por disparo (spec 0016 / ADR 0013); semeia `limite_por_agendamento_dia`.
    # None = sem teto. Fonte runtime é a tabela (operador muda sem redeploy).
    limite_por_agendamento_default: int | None = Field(
        default=None, validation_alias="LIMITE_POR_AGENDAMENTO"
    )

    # Importação de contatos (spec 0002): limites configuráveis do upload (AC-17).
    import_max_bytes: int = 5 * 1024 * 1024  # 5 MB
    import_max_linhas: int = 5000

    # Fuso (BRIEFING §9: exibição em America/Sao_Paulo)
    tz: str = "America/Sao_Paulo"


@lru_cache
def get_settings() -> Settings:
    """Settings cacheada (lida uma vez por processo)."""
    return Settings()
