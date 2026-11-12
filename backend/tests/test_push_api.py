"""API de Web Push (spec 0023, AC-1..AC-3 + hardening): chave pública + inscrição, autenticadas."""

from app.models.push_subscription import PushSubscription

_SUB = {"endpoint": "https://push.example/1", "keys": {"p256dh": "p", "auth": "a"}}


def test_chave_sem_auth_401(client):  # AC-1
    assert client.get("/push/chave-publica").status_code == 401


def test_chave_com_auth(client, auth_headers):  # AC-1
    r = client.get("/push/chave-publica", headers=auth_headers)
    assert r.status_code == 200
    assert "chave" in r.json()  # null sem VAPID configurada


def test_inscrever_sem_auth_401(client):  # AC-2
    assert client.post("/push/inscrever", json=_SUB).status_code == 401


def test_inscrever_cria(client, auth_headers, db):  # AC-2
    r = client.post("/push/inscrever", headers=auth_headers, json=_SUB)
    assert r.status_code == 201
    db.expire_all()
    assert db.query(PushSubscription).filter_by(endpoint=_SUB["endpoint"]).count() == 1


def test_inscrever_upsert(client, auth_headers, db):  # AC-3
    client.post("/push/inscrever", headers=auth_headers, json=_SUB)
    client.post(
        "/push/inscrever",
        headers=auth_headers,
        json={**_SUB, "keys": {"p256dh": "p2", "auth": "a2"}},
    )
    db.expire_all()
    assert db.query(PushSubscription).filter_by(endpoint=_SUB["endpoint"]).count() == 1


def test_inscrever_endpoint_nao_https_422(client, auth_headers):  # hardening §6 (anti-SSRF/abuso)
    r = client.post(
        "/push/inscrever",
        headers=auth_headers,
        json={"endpoint": "http://push.example/1", "keys": {"p256dh": "p", "auth": "a"}},
    )
    assert r.status_code == 422
