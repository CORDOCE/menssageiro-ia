"""Aplicação FastAPI (processo `api`). Ponto de entrada: `app.main:app`.

Expõe o healthcheck shallow `/health` (RAILWAY §4) e o `/admin/health/deep` (BRIEFING §12,
spec 0021), além dos routers de domínio.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.admin_health import router as admin_health_router
from app.api.agendamentos import router as agendamentos_router
from app.api.auth import router as auth_router
from app.api.configuracoes import router as configuracoes_router
from app.api.contatos import router as contatos_router
from app.api.envios import router as envios_router
from app.api.modelos import router as modelos_router
from app.api.push import router as push_router
from app.api.webhook_meta import router as webhook_router
from app.core.config import get_settings
from app.core.metrics import instrumentar
from app.core.observabilidade import configurar_sentry

# Observabilidade (§7): inicializa o Sentry antes de criar o app (auto-instrumenta FastAPI).
# No-op sem SENTRY_DSN.
configurar_sentry()

app = FastAPI(title="Mensageiro API", version="0.1.0")

# CORS restrito ao domínio do frontend (CLAUDE.md §6). Sem cookies (sessão via Bearer),
# então allow_credentials=False. Sem FRONTEND_URL configurado, nenhuma origem é liberada.
_frontend_url = get_settings().frontend_url
_origens: list[str] = [_frontend_url] if _frontend_url else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(auth_router)
app.include_router(contatos_router)
app.include_router(modelos_router)
app.include_router(agendamentos_router)
app.include_router(envios_router)
app.include_router(configuracoes_router)
app.include_router(webhook_router)
app.include_router(admin_health_router)
app.include_router(push_router)

# Expõe GET /metrics (Prometheus) protegido por token, raspado pela Central de Observabilidade
# (spec 0024). No-op fail-closed sem METRICS_TOKEN.
instrumentar(app)


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness shallow: não depende de banco, Meta ou OpenAI (spec 0001, AC-3)."""
    return HealthResponse(status="ok")
