"""API de configuração de envio (spec 0018, AC-1..AC-9): GET/PATCH protegidos.

Edita a linha única `configuracoes` (ADR 0008). PATCH parcial; toda alteração audita (§5.8).
Nenhum caminho aqui envia nada (§5.7).
"""

from __future__ import annotations

from sqlalchemy import select

from app.models.auditoria import Auditoria


def test_get_retorna_config_default(client, auth_headers, db):  # AC-1
    r = client.get("/configuracoes", headers=auth_headers)
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) >= {
        "janela_envio",
        "limite_diario",
        "limite_por_contato_dia",
        "limite_por_agendamento_dia",
        "envios_pausados",
        "atualizado_em",
    }
    assert corpo["janela_envio"] == {"dias": [0, 1, 2, 3, 4, 5], "inicio": "08:00", "fim": "20:00"}
    assert corpo["limite_diario"] == 200
    assert corpo["limite_por_contato_dia"] is None
    assert corpo["envios_pausados"] is False


def test_get_sem_auth_401(client, db):  # AC-2
    assert client.get("/configuracoes").status_code == 401


def test_patch_sem_auth_401(client, db):  # AC-2
    assert client.patch("/configuracoes", json={"envios_pausados": True}).status_code == 401


def test_patch_limite_diario_persiste(client, auth_headers, db):  # AC-3
    r = client.patch("/configuracoes", headers=auth_headers, json={"limite_diario": 500})
    assert r.status_code == 200
    assert r.json()["limite_diario"] == 500
    assert client.get("/configuracoes", headers=auth_headers).json()["limite_diario"] == 500


def test_patch_pausa_persiste(client, auth_headers, db):  # AC-4 (efeito no worker é test_worker)
    r = client.patch("/configuracoes", headers=auth_headers, json={"envios_pausados": True})
    assert r.status_code == 200
    assert r.json()["envios_pausados"] is True


def test_patch_janela_persiste(client, auth_headers, db):  # AC-5
    nova = {"dias": [0, 1, 2, 3, 4], "inicio": "09:00", "fim": "18:00"}
    r = client.patch("/configuracoes", headers=auth_headers, json={"janela_envio": nova})
    assert r.status_code == 200
    assert r.json()["janela_envio"] == nova


def test_patch_parcial_nao_mexe_nos_demais(client, auth_headers, db):  # AC-3/parcial
    client.patch("/configuracoes", headers=auth_headers, json={"limite_diario": 300})
    client.patch("/configuracoes", headers=auth_headers, json={"envios_pausados": True})
    corpo = client.get("/configuracoes", headers=auth_headers).json()
    assert corpo["limite_diario"] == 300  # mantido pelo segundo PATCH
    assert corpo["envios_pausados"] is True


def test_patch_invalido_422_nada_muda(client, auth_headers, db):  # AC-6
    r = client.patch("/configuracoes", headers=auth_headers, json={"limite_diario": 0})
    assert r.status_code == 422
    assert client.get("/configuracoes", headers=auth_headers).json()["limite_diario"] == 200


def test_patch_null_campo_not_null_422_nao_500(client, auth_headers, db):  # AC-6 (double-check)
    # envios_pausados é NOT NULL: null explícito deve ser 422, nunca 500.
    r = client.patch("/configuracoes", headers=auth_headers, json={"envios_pausados": None})
    assert r.status_code == 422


def test_patch_limite_opcional_null_remove(client, auth_headers, db):  # AC-7
    client.patch("/configuracoes", headers=auth_headers, json={"limite_por_contato_dia": 10})
    r = client.patch("/configuracoes", headers=auth_headers, json={"limite_por_contato_dia": None})
    assert r.status_code == 200
    assert r.json()["limite_por_contato_dia"] is None


def test_patch_corpo_vazio_422(client, auth_headers, db):  # AC-9
    assert client.patch("/configuracoes", headers=auth_headers, json={}).status_code == 422


def _auditorias(db) -> list[Auditoria]:
    return list(
        db.execute(
            select(Auditoria).where(Auditoria.operacao == "configuracao.atualizada")
        ).scalars()
    )


def test_patch_valido_gera_auditoria(client, auth_headers, db):  # AC-8
    client.patch("/configuracoes", headers=auth_headers, json={"limite_diario": 400})
    linhas = _auditorias(db)
    assert len(linhas) == 1
    assert linhas[0].ator_email == "admin@teste.com"
    assert linhas[0].alvo_id == "default"
    # Sem PII; registra o campo alterado e o novo valor.
    assert "limite_diario" in (linhas[0].metadados or "")
    assert "400" in (linhas[0].metadados or "")


def test_patch_noop_nao_audita(client, auth_headers, db):  # AC-8 (diff real)
    atual = client.get("/configuracoes", headers=auth_headers).json()["limite_diario"]
    r = client.patch("/configuracoes", headers=auth_headers, json={"limite_diario": atual})
    assert r.status_code == 200
    assert _auditorias(db) == []  # nada mudou → nada a auditar
