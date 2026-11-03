"""Prova do AC-3: GET /health → 200 com {"status": "ok"}, sem depender de Meta/OpenAI."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_cors_libera_origem_do_frontend() -> None:
    # conftest define FRONTEND_URL=http://localhost:3000 → CORS deve liberar essa origem.
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_preflight_login_ok() -> None:
    # O preflight do POST /auth/login (que era 405 e quebrava o login no browser) agora passa.
    resp = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_bloqueia_origem_desconhecida() -> None:
    resp = client.get("/health", headers={"Origin": "https://malicioso.example"})
    assert resp.headers.get("access-control-allow-origin") != "https://malicioso.example"
