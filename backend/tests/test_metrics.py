"""Spec 0024 — `GET /metrics` protegido por token (um teste por AC).

Cada app de teste usa um `CollectorRegistry` próprio (isolamento; evita "Duplicated timeseries").
Não dependem do banco: constroem um app mínimo com `instrumentar(...)`. Métricas de processo
(`process_*`) não são exercitadas aqui — só aparecem em Linux (Railway/CI), não no macOS.
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry

import app.core.metrics as metrics_mod
from app.core.config import get_settings
from app.core.metrics import instrumentar, verificar_token_metrics

TOKEN = "token-de-teste-7a3f9c2b1e"


def _montar_app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    instrumentar(app, registry=CollectorRegistry())
    return app


@pytest.fixture
def client_com_token(monkeypatch: pytest.MonkeyPatch):
    """App com METRICS_TOKEN setado → /metrics registrado e protegido."""
    monkeypatch.setenv("METRICS_TOKEN", TOKEN)
    get_settings.cache_clear()
    try:
        yield TestClient(_montar_app())
    finally:
        get_settings.cache_clear()  # outros testes voltam a ver settings sem o token


@pytest.fixture
def client_sem_token(monkeypatch: pytest.MonkeyPatch):
    """App sem METRICS_TOKEN → /metrics nem é registrado (fail-closed)."""
    monkeypatch.delenv("METRICS_TOKEN", raising=False)
    get_settings.cache_clear()
    try:
        yield TestClient(_montar_app())
    finally:
        get_settings.cache_clear()


# --- AC-1: sem credencial → 401 ---
def test_ac1_sem_authorization_retorna_401(client_com_token: TestClient):
    assert client_com_token.get("/metrics").status_code == 401


# --- AC-2: token errado / esquema errado → 401 ---
def test_ac2_token_errado_retorna_401(client_com_token: TestClient):
    assert client_com_token.get("/metrics", headers={"Authorization": "Bearer errado"}).status_code == 401


def test_ac2_esquema_errado_retorna_401(client_com_token: TestClient):
    # Esquema Basic (não Bearer) é tratado como ausência de token válido.
    assert client_com_token.get("/metrics", headers={"Authorization": f"Basic {TOKEN}"}).status_code == 401


def test_ac2_token_nao_ascii_retorna_401(monkeypatch: pytest.MonkeyPatch):
    # Header com bytes não-ASCII (o Starlette entrega decodificado em latin-1) não pode virar 500:
    # a comparação em bytes evita o TypeError do compare_digest com str não-ASCII. Nível de função
    # porque o cliente HTTP (httpx) nem transmite header não-ASCII.
    monkeypatch.setenv("METRICS_TOKEN", TOKEN)
    get_settings.cache_clear()
    try:
        with pytest.raises(HTTPException) as exc:
            verificar_token_metrics("Bearer café")
        assert exc.value.status_code == 401
    finally:
        get_settings.cache_clear()


# --- AC-3: token certo → 200 + formato Prometheus ---
def test_ac3_token_certo_retorna_200_formato_prometheus(client_com_token: TestClient):
    r = client_com_token.get("/metrics", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    # Content-type de exposição Prometheus da própria lib (hoje "text/plain; version=1.0.0").
    assert r.headers["content-type"] == CONTENT_TYPE_LATEST
    assert r.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in r.text


# --- AC-4: sem METRICS_TOKEN → 404 (rota não registrada), mesmo com credencial ---
def test_ac4_sem_token_configurado_retorna_404(client_sem_token: TestClient):
    assert client_sem_token.get("/metrics").status_code == 404
    assert client_sem_token.get("/metrics", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 404


# --- AC-5: comparação resistente a timing (usa secrets.compare_digest, não ==) ---
def test_ac5_usa_compare_digest(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("METRICS_TOKEN", TOKEN)
    get_settings.cache_clear()
    chamadas = []
    original = metrics_mod.secrets.compare_digest

    def espiao(a: str, b: str) -> bool:
        chamadas.append((a, b))
        return original(a, b)

    monkeypatch.setattr(metrics_mod.secrets, "compare_digest", espiao)
    try:
        # token certo: passa sem exceção e exercitou o compare_digest
        verificar_token_metrics(f"Bearer {TOKEN}")
        assert chamadas, "verificar_token_metrics deveria usar secrets.compare_digest"
        # token errado: 401
        with pytest.raises(HTTPException) as exc:
            verificar_token_metrics("Bearer outro")
        assert exc.value.status_code == 401
    finally:
        get_settings.cache_clear()


# --- AC-6: métricas de requisição presentes com rótulo handler ---
def test_ac6_metricas_de_requisicao_presentes(client_com_token: TestClient):
    client_com_token.get("/ping")  # gera tráfego numa rota de domínio
    corpo = client_com_token.get("/metrics", headers={"Authorization": f"Bearer {TOKEN}"}).text
    assert "http_request_duration_seconds" in corpo
    assert "http_requests_total{" in corpo
    assert 'handler="/ping"' in corpo


# --- AC-7: /metrics fora do OpenAPI ---
def test_ac7_metrics_fora_do_openapi(client_com_token: TestClient):
    paths = client_com_token.get("/openapi.json").json()["paths"]
    assert "/metrics" not in paths


# --- Caso de borda: registro idempotente (dois apps com token não derrubam o registry) ---
def test_borda_dois_apps_nao_duplicam_registry(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("METRICS_TOKEN", TOKEN)
    get_settings.cache_clear()
    try:
        _montar_app()
        _montar_app()  # não pode levantar "Duplicated timeseries in CollectorRegistry"
    finally:
        get_settings.cache_clear()
