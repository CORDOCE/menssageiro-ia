"""Prova do AC-3: GET /health → 200 com {"status": "ok"}, sem depender de Meta/OpenAI."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
