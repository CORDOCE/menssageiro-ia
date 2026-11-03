"""Descadastro (task 5 / AC-7, §5.4) e registro de consentimento (task 6 / AC-8, §5.9)."""

import uuid


def _criar(client, auth_headers, telefone="11987654321"):
    return client.post(
        "/contatos", json={"nome": "Fulano", "telefone": telefone}, headers=auth_headers
    ).json()["id"]


# --- AC-7: descadastro é soft e imediato; contato permanece e fica marcado ---
def test_descadastrar_marca_e_mantem(client, auth_headers):
    cid = _criar(client, auth_headers)
    r = client.post(f"/contatos/{cid}/descadastrar", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["descadastrado_em"] is not None
    # permanece no banco (prova LGPD/auditoria), acessível no GET
    assert client.get(f"/contatos/{cid}", headers=auth_headers).json()["descadastrado_em"] is not None


def test_descadastrar_sem_auth_401(client):
    assert client.post(f"/contatos/{uuid.uuid4()}/descadastrar").status_code == 401


# --- AC-8: registrar consentimento (bool + data + origem) ---
def test_registrar_consentimento(client, auth_headers):
    cid = _criar(client, auth_headers)
    r = client.post(
        f"/contatos/{cid}/consentimento",
        json={"origem": "formulário no site", "data": "2026-10-30"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["consentimento"] is True
    assert corpo["consentimento_origem"] == "formulário no site"
    assert corpo["consentimento_data"] is not None


def test_consentimento_data_futura_422(client, auth_headers):
    cid = _criar(client, auth_headers)
    r = client.post(
        f"/contatos/{cid}/consentimento",
        json={"origem": "x", "data": "2099-01-01"},
        headers=auth_headers,
    )
    assert r.status_code == 422
