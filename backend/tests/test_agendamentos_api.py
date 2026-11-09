"""API de agendamentos (spec 0004, AC-3..AC-7): criar/listar/cancelar/reenviar protegidos.

A API só registra (§5.1): nenhum caminho chama a Meta.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.agendamento import Agendamento
from app.models.contato import Contato
from app.models.modelo import Modelo


def _modelo(db) -> str:
    mid = str(uuid.uuid4())
    db.add(Modelo(id=mid, nome=f"m_{mid[:8]}", corpo="oi", status="aprovado"))
    db.commit()
    return mid


def _contato(db) -> str:
    cid = str(uuid.uuid4())
    db.add(
        Contato(
            id=cid, nome="C", telefone_e164=f"+5531{uuid.uuid4().int % 100000000:08d}",
            consentimento=True,
        )
    )
    db.commit()
    return cid


def _payload(modelo_id: str, **kw) -> dict:
    base = {"modelo_id": modelo_id, "executar_em": datetime.now(UTC).isoformat()}
    base.update(kw)
    return base


def test_criar_para_contato_201(client, auth_headers, db):
    mid, cid = _modelo(db), _contato(db)
    r = client.post(
        "/agendamentos", json=_payload(mid, contato_id=cid, variaveis=["x"]), headers=auth_headers
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "aprovado"
    assert db.get(Agendamento, body["id"]).criado_por is not None  # AC-3: criado_por gravado


def test_criar_sem_auth_401(client, db):
    mid = _modelo(db)
    r = client.post("/agendamentos", json=_payload(mid, grupo="g"))
    assert r.status_code == 401


def test_criar_xor_ambos_422(client, auth_headers, db):
    mid, cid = _modelo(db), _contato(db)
    r = client.post("/agendamentos", json=_payload(mid, contato_id=cid, grupo="g"), headers=auth_headers)
    assert r.status_code == 422


def test_criar_xor_nenhum_422(client, auth_headers, db):
    mid = _modelo(db)
    r = client.post("/agendamentos", json=_payload(mid), headers=auth_headers)
    assert r.status_code == 422


def test_criar_modelo_inexistente_404(client, auth_headers, db):
    r = client.post("/agendamentos", json=_payload("nao-existe", grupo="g"), headers=auth_headers)
    assert r.status_code == 404


def test_criar_nao_chama_meta(client, auth_headers, db, monkeypatch):
    # AC-3 / §5.1: a API nunca envia. Se o fluxo chamar enviar_template, falha.
    import app.services.whatsapp_client as wc

    def _boom(*a, **k):
        raise AssertionError("A API não pode enviar (§5.1)")

    monkeypatch.setattr(wc, "enviar_template", _boom)
    mid, cid = _modelo(db), _contato(db)
    r = client.post("/agendamentos", json=_payload(mid, contato_id=cid), headers=auth_headers)
    assert r.status_code == 201


def test_listar(client, auth_headers, db):
    mid = _modelo(db)
    for _ in range(2):
        client.post("/agendamentos", json=_payload(mid, grupo="g"), headers=auth_headers)
    r = client.get("/agendamentos", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) == 2


def test_cancelar_e_409_em_terminal(client, auth_headers, db):
    mid = _modelo(db)
    aid = client.post("/agendamentos", json=_payload(mid, grupo="g"), headers=auth_headers).json()["id"]
    r = client.post(f"/agendamentos/{aid}/cancelar", headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "cancelado"
    r2 = client.post(f"/agendamentos/{aid}/cancelar", headers=auth_headers)
    assert r2.status_code == 409  # já terminal


def test_reenviar_de_aguardando_decisao(client, auth_headers, db):
    mid = _modelo(db)
    aid = client.post("/agendamentos", json=_payload(mid, grupo="g"), headers=auth_headers).json()["id"]
    ag = db.get(Agendamento, aid)
    ag.status = "aguardando_decisao"
    db.commit()
    r = client.post(f"/agendamentos/{aid}/reenviar", headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "aprovado"


def test_reenviar_status_invalido_409(client, auth_headers, db):
    mid = _modelo(db)
    aid = client.post("/agendamentos", json=_payload(mid, grupo="g"), headers=auth_headers).json()["id"]
    r = client.post(f"/agendamentos/{aid}/reenviar", headers=auth_headers)  # status aprovado
    assert r.status_code == 409


# --- recorrência (spec 0005) ---
def test_criar_com_recorrencia_valida_201(client, auth_headers, db):  # AC-11
    mid, cid = _modelo(db), _contato(db)
    r = client.post(
        "/agendamentos",
        json=_payload(mid, contato_id=cid, recorrencia="FREQ=WEEKLY;BYDAY=MO"),
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["recorrencia"] == "FREQ=WEEKLY;BYDAY=MO"
    ag = db.get(Agendamento, r.json()["id"])
    assert ag.recorrencia == "FREQ=WEEKLY;BYDAY=MO" and ag.agendamento_pai_id is None  # nasce raiz


def test_criar_com_recorrencia_invalida_422(client, auth_headers, db):  # AC-12
    mid, cid = _modelo(db), _contato(db)
    r = client.post(
        "/agendamentos",
        json=_payload(mid, contato_id=cid, recorrencia="FREQ=BANANA"),
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_criar_recorrencia_longa_demais_422(client, auth_headers, db):  # §6 endurecimento
    mid, cid = _modelo(db), _contato(db)
    r = client.post(
        "/agendamentos",
        json=_payload(mid, contato_id=cid, recorrencia="FREQ=DAILY;" + "X" * 600),
        headers=auth_headers,
    )
    assert r.status_code == 422


def _ocorrencia(db, mid, cid, raiz_id, *, executar_em, status) -> str:
    oid = str(uuid.uuid4())
    db.add(
        Agendamento(
            id=oid, modelo_id=mid, contato_id=cid, recorrencia="FREQ=DAILY",
            agendamento_pai_id=raiz_id, executar_em=executar_em, status=status,
        )
    )
    db.commit()
    return oid


def test_cancelar_serie_so_futuras_pendentes(client, auth_headers, db):  # AC-13
    mid, cid = _modelo(db), _contato(db)
    agora = datetime.now(UTC)
    raiz = str(uuid.uuid4())
    db.add(Agendamento(id=raiz, modelo_id=mid, contato_id=cid, recorrencia="FREQ=DAILY",
                       executar_em=agora - timedelta(days=1), status="enviado"))
    db.commit()
    fut1 = _ocorrencia(db, mid, cid, raiz, executar_em=agora + timedelta(days=1), status="aprovado")
    fut2 = _ocorrencia(db, mid, cid, raiz, executar_em=agora + timedelta(days=2), status="aprovado")
    enviada = _ocorrencia(db, mid, cid, raiz, executar_em=agora - timedelta(hours=1), status="enviado")
    # passar o id de uma FILHA deve resolver a raiz e cancelar a série inteira (futuras pendentes).
    r = client.post(f"/agendamentos/{fut1}/cancelar-serie", headers=auth_headers)
    assert r.status_code == 200
    db.expire_all()
    assert db.get(Agendamento, fut1).status == "cancelado"
    assert db.get(Agendamento, fut2).status == "cancelado"
    assert db.get(Agendamento, enviada).status == "enviado"  # enviada fica intacta


def test_cancelar_serie_inexistente_404(client, auth_headers, db):
    r = client.post("/agendamentos/nao-existe/cancelar-serie", headers=auth_headers)
    assert r.status_code == 404


# --- hardening (spec 0015 / dívida R1) ---
def test_criar_contato_inexistente_404(client, auth_headers, db):  # AC-1
    mid = _modelo(db)
    r = client.post(
        "/agendamentos", json=_payload(mid, contato_id="nao-existe"), headers=auth_headers
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Contato não encontrado"
    # nada criado
    assert db.execute(select(Agendamento)).scalars().first() is None


def test_criar_variaveis_itens_demais_422(client, auth_headers, db):  # AC-3
    mid, cid = _modelo(db), _contato(db)
    r = client.post(
        "/agendamentos",
        json=_payload(mid, contato_id=cid, variaveis=[str(i) for i in range(51)]),
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_criar_variavel_longa_demais_422(client, auth_headers, db):  # AC-3
    mid, cid = _modelo(db), _contato(db)
    r = client.post(
        "/agendamentos",
        json=_payload(mid, contato_id=cid, variaveis=["x" * 1001]),
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_criar_variaveis_no_limite_201(client, auth_headers, db):  # AC-4
    mid, cid = _modelo(db), _contato(db)
    r = client.post(
        "/agendamentos",
        json=_payload(mid, contato_id=cid, variaveis=["x" * 1000] * 50),
        headers=auth_headers,
    )
    assert r.status_code == 201
