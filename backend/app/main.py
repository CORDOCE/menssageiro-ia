"""Aplicação FastAPI (processo `api`). Ponto de entrada: `app.main:app`.

Nesta fase expõe apenas o healthcheck shallow `/health` (RAILWAY §4). O `/admin/health/deep`
(BRIEFING §12) e os routers de domínio entram nas fases seguintes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.auth import router as auth_router
from app.api.contatos import router as contatos_router
from app.api.modelos import router as modelos_router
from app.api.webhook_meta import router as webhook_router
from app.core.config import get_settings

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
app.include_router(webhook_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness shallow: não depende de banco, Meta ou OpenAI (spec 0001, AC-3)."""
    return HealthResponse(status="ok")
