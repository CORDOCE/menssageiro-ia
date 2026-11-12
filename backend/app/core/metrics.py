"""Exposição de métricas Prometheus para a Central de Observabilidade (spec 0024).

O `GET /metrics` é máquina-a-máquina: raspado pelo Prometheus da central com um Bearer token
estático (`METRICS_TOKEN`), **não** pela sessão de usuário (o Prometheus não faz login). É
**fail-closed**: sem `metrics_token` configurado, a rota nem é registrada (responde 404).

As métricas são o conjunto padrão do `prometheus-fastapi-instrumentator`
(`http_requests_total`, `http_request_duration_seconds*`, `http_request_duration_highr_seconds*`)
somado às métricas de processo do `prometheus_client` (`process_resident_memory_bytes`,
`process_cpu_seconds_total`) — estas só aparecem em Linux (Railway/CI), não no macOS (sem `/proc`).
É exatamente o que as regras da central traduzem para os nomes `sistema:...`.
"""

import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, status
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import get_settings

_PREFIXO = "Bearer "


def verificar_token_metrics(authorization: str | None = Header(default=None)) -> None:
    """Dependência: exige `Authorization: Bearer <METRICS_TOKEN>`. 401 se faltar/errar.

    Comparação em tempo constante (`secrets.compare_digest`) para não vazar o token por timing.
    """
    esperado = get_settings().metrics_token
    if not esperado:
        # Defensivo: normalmente a rota nem existe sem token (ver `instrumentar`).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    fornecido = authorization[len(_PREFIXO) :] if authorization and authorization.startswith(_PREFIXO) else ""
    # Compara em bytes: `compare_digest` com `str` não-ASCII levanta TypeError, e o Starlette entrega
    # o header decodificado em latin-1 (um cliente pode mandar bytes 0x80–0xFF) — bytes nunca levanta.
    if not fornecido or not secrets.compare_digest(fornecido.encode(), esperado.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token de métricas inválido",
        )


def instrumentar(app: FastAPI, registry: CollectorRegistry | None = None) -> None:
    """Liga a coleta e expõe `GET /metrics` protegido — **só** se `metrics_token` estiver setado.

    Fail-closed: sem token, não registra nada (métricas nunca ficam expostas sem proteção).
    `registry` é só para os testes isolarem o `CollectorRegistry`; em produção fica `None` (usa o
    REGISTRY default, que inclui as métricas de processo `process_*`).
    """
    if not get_settings().metrics_token:
        return
    Instrumentator(registry=registry).instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        dependencies=[Depends(verificar_token_metrics)],
    )
