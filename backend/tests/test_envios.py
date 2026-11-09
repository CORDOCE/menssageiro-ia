"""API de histórico de envios (spec 0014, AC-1..AC-7): GET /envios read-only protegido.

Lista os envios realizados com join de contato/modelo, filtros de status e período, paginação.
Nenhum caminho chama a Meta (§5.7): o teste só semeia o banco.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo


def _contato(db, *, nome="C", tel=None) -> str:
    cid = str(uuid.uuid4())
    tel = tel or f"+5531{uuid.uuid4().int % 100000000:08d}"
    db.add(Contato(id=cid, nome=nome, telefone_e164=tel, consentimento=True))
    db.commit()
    return cid


def _modelo(db, *, nome=None) -> str:
    mid = str(uuid.uuid4())
    db.add(Modelo(id=mid, nome=nome or f"m_{mid[:8]}", corpo="oi", status="aprovado"))
    db.commit()
    return mid


def _envio(db, contato_id, *, modelo_id=None, status="enviado", criado_em=None,
           erro_codigo=None, erro_motivo=None) -> str:
    eid = str(uuid.uuid4())
    kw = {"criado_em": criado_em} if criado_em is not None else {}
    db.add(Envio(id=eid, contato_id=contato_id, modelo_id=modelo_id, status=status,
                 erro_codigo=erro_codigo, erro_motivo=erro_motivo, **kw))
    db.commit()
    return eid


def test_lista_ordena_desc_e_campos(client, auth_headers, db):  # AC-1, AC-4
    cid = _contato(db, nome="Alice", tel="+5531999990001")
    mid = _modelo(db, nome="boas_vindas")
    base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    e_velho = _envio(db, cid, modelo_id=mid, status="enviado", criado_em=base)
    e_novo = _envio(db, cid, modelo_id=mid, status="entregue", criado_em=base + timedelta(hours=1))
    r = client.get("/envios", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert [e["id"] for e in body] == [e_novo, e_velho]  # mais recentes primeiro
    item = body[0]
    assert item["contato_nome"] == "Alice"
    assert item["contato_telefone"] == "+5531999990001"
    assert item["modelo_nome"] == "boas_vindas"
    assert item["status"] == "entregue"


def test_filtro_status(client, auth_headers, db):  # AC-2
    cid = _contato(db)
    _envio(db, cid, status="falhou")
    _envio(db, cid, status="enviado")
    r = client.get("/envios?status=falhou", headers=auth_headers)
    assert r.status_code == 200
    assert [e["status"] for e in r.json()] == ["falhou"]


def test_filtro_periodo_inclusivo(client, auth_headers, db):  # AC-3
    cid = _contato(db)
    base = datetime(2026, 6, 1, tzinfo=UTC)
    _envio(db, cid, criado_em=base - timedelta(days=2))  # fora
    dentro = _envio(db, cid, criado_em=base)
    _envio(db, cid, criado_em=base + timedelta(days=5))  # fora
    desde = (base - timedelta(days=1)).isoformat()
    ate = (base + timedelta(days=1)).isoformat()
    r = client.get("/envios", params={"desde": desde, "ate": ate}, headers=auth_headers)
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == [dentro]


def test_envio_avulso_modelo_nulo(client, auth_headers, db):  # AC-4 (borda)
    cid = _contato(db)
    _envio(db, cid, modelo_id=None)
    item = client.get("/envios", headers=auth_headers).json()[0]
    assert item["modelo_id"] is None and item["modelo_nome"] is None


def test_sem_auth_401(client, db):  # AC-5
    assert client.get("/envios").status_code == 401


def test_erro_so_em_falhou(client, auth_headers, db):  # AC-6
    cid = _contato(db)
    _envio(db, cid, status="falhou", erro_codigo="131026", erro_motivo="indisponível",
           criado_em=datetime(2026, 1, 2, tzinfo=UTC))
    _envio(db, cid, status="enviado", criado_em=datetime(2026, 1, 1, tzinfo=UTC))
    body = client.get("/envios", headers=auth_headers).json()
    falhou, ok = body[0], body[1]
    assert falhou["erro_codigo"] == "131026" and falhou["erro_motivo"] == "indisponível"
    assert ok["erro_codigo"] is None and ok["erro_motivo"] is None


def test_paginacao(client, auth_headers, db):  # AC-7
    cid = _contato(db)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    ids = [_envio(db, cid, criado_em=base + timedelta(minutes=i)) for i in range(3)]
    # desc → ids[2], ids[1], ids[0]; offset=1,limit=1 → ids[1]
    r = client.get("/envios?limit=1&offset=1", headers=auth_headers)
    assert [e["id"] for e in r.json()] == [ids[1]]


def test_limit_invalido_422(client, auth_headers, db):  # AC-7
    assert client.get("/envios?limit=0", headers=auth_headers).status_code == 422
    assert client.get("/envios?limit=201", headers=auth_headers).status_code == 422


def test_status_invalido_422(client, auth_headers, db):  # borda
    assert client.get("/envios?status=banana", headers=auth_headers).status_code == 422
