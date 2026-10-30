"""Aplicação FastAPI (processo `api`). Ponto de entrada: `app.main:app`.

Nesta fase expõe apenas o healthcheck shallow `/health` (RAILWAY §4). O `/admin/health/deep`
(BRIEFING §12) e os routers de domínio entram nas fases seguintes.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from app.api.auth import router as auth_router

app = FastAPI(title="Mensageiro API", version="0.1.0")
app.include_router(auth_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness shallow: não depende de banco, Meta ou OpenAI (spec 0001, AC-3)."""
    return HealthResponse(status="ok")
