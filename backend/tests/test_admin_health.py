"""Saúde profunda (spec 0021, AC-1..AC-9): GET /admin/health/deep read-only autenticado.

Só semeia o banco (saude, envios, agendamentos) e lê o retrato; nenhum caminho chama a Meta (§5.7).
Fronteiras de dia/mês em America/Sao_Paulo são tomadas das helpers do módulo para determinismo.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.api.admin_health import _checar_banco, _inicio_dia_sp, _inicio_mes_sp
from app.models.agendamento import Agendamento
from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo
from app.models.saude import Saude


def _contato(db, *, tel=None) -> str:
    cid = str(uuid.uuid4())
    tel = tel or f"+5531{uuid.uuid4().int % 100000000:08d}"
    db.add(Contato(id=cid, nome="C", telefone_e164=tel, consentimento=True))
    db.commit()
    return cid


def _modelo(db) -> str:
    mid = str(uuid.uuid4())
    db.add(Modelo(id=mid, nome=f"m_{mid[:8]}", corpo="oi", status="aprovado"))
    db.commit()
    return mid


def _envio(db, contato_id, *, status="enviado", criado_em=None) -> None:
    kw = {"criado_em": criado_em} if criado_em is not None else {}
    db.add(Envio(id=str(uuid.uuid4()), contato_id=contato_id, status=status, **kw))
    db.commit()


def _agendamento(db, contato_id, modelo_id, *, executar_em, status="aprovado") -> None:
    db.add(
        Agendamento(
            id=str(uuid.uuid4()),
            contato_id=contato_id,
            modelo_id=modelo_id,
            executar_em=executar_em,
            status=status,
            variaveis=[],
        )
    )
    db.commit()


def _saude(db, *, ultimo_ciclo_em) -> None:
    db.add(Saude(id=str(uuid.uuid4()), ultimo_ciclo_em=ultimo_ciclo_em))
    db.commit()


def test_sem_sessao_401(client):  # AC-1
    assert client.get("/admin/health/deep").status_code == 401


def test_retrato_200_seis_secoes(client, auth_headers, db):  # AC-2
    _saude(db, ultimo_ciclo_em=datetime.now(UTC))
    r = client.get("/admin/health/deep", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {
        "banco",
        "worker",
        "envios_hoje",
        "taxa_falha_hoje",
        "fila",
        "gasto_mes_estimado",
    }
    assert body["banco"]["status"] == "ok"


def test_banco_degrada_sem_derrubar():  # AC-3
    class _FakeSess:
        def execute(self, *a):
            raise RuntimeError("db down")

        def rollback(self):
            pass

    assert _checar_banco(_FakeSess()).status == "erro"


def test_worker_vivo(client, auth_headers, db):  # AC-4
    _saude(db, ultimo_ciclo_em=datetime.now(UTC) - timedelta(seconds=60))
    r = client.get("/admin/health/deep", headers=auth_headers)
    assert r.json()["worker"]["status"] == "vivo"


def test_worker_parado(client, auth_headers, db):  # AC-4
    _saude(db, ultimo_ciclo_em=datetime.now(UTC) - timedelta(minutes=10))
    r = client.get("/admin/health/deep", headers=auth_headers)
    assert r.json()["worker"]["status"] == "parado"


def test_worker_desconhecido(client, auth_headers, db):  # AC-5
    r = client.get("/admin/health/deep", headers=auth_headers)
    assert r.json()["worker"]["status"] == "desconhecido"


def test_envios_hoje_por_status(client, auth_headers, db):  # AC-6
    agora = datetime.now(UTC)
    cid = _contato(db)
    _envio(db, cid, status="entregue", criado_em=agora)
    _envio(db, cid, status="falhou", criado_em=agora)
    _envio(db, cid, status="enviado", criado_em=agora)
    _envio(db, cid, status="entregue", criado_em=_inicio_dia_sp(agora) - timedelta(seconds=1))
    r = client.get("/admin/health/deep", headers=auth_headers)
    assert r.json()["envios_hoje"] == {"entregue": 1, "falhou": 1, "enviado": 1}


def test_taxa_falha_dia_50pct(client, auth_headers, db):  # AC-7
    agora = datetime.now(UTC)
    cid = _contato(db)
    for s in ("falhou", "aguardando_decisao", "enviado", "entregue"):
        _envio(db, cid, status=s, criado_em=agora)
    t = client.get("/admin/health/deep", headers=auth_headers).json()["taxa_falha_hoje"]
    assert t["tentativas"] == 4
    assert t["falhas"] == 2
    assert t["percentual"] == 50.0


def test_taxa_falha_zero_sem_envios(client, auth_headers, db):  # AC-7
    r = client.get("/admin/health/deep", headers=auth_headers)
    assert r.json()["taxa_falha_hoje"]["percentual"] == 0.0


def test_fila_conta_aprovados_vencidos(client, auth_headers, db):  # AC-8
    agora = datetime.now(UTC)
    cid = _contato(db)
    mid = _modelo(db)
    _agendamento(db, cid, mid, executar_em=agora - timedelta(minutes=1), status="aprovado")
    _agendamento(db, cid, mid, executar_em=agora - timedelta(minutes=1), status="aprovado")
    _agendamento(db, cid, mid, executar_em=agora + timedelta(hours=1), status="aprovado")  # futuro
    _agendamento(db, cid, mid, executar_em=agora - timedelta(minutes=1), status="cancelado")
    assert client.get("/admin/health/deep", headers=auth_headers).json()["fila"] == 2


def test_gasto_mes_estimado(client, auth_headers, db):  # AC-9
    agora = datetime.now(UTC)
    cid = _contato(db)
    for s in ("entregue", "lido", "enviado"):
        _envio(db, cid, status=s, criado_em=agora)
    _envio(db, cid, status="falhou", criado_em=agora)  # não conta no gasto
    _envio(db, cid, status="entregue", criado_em=_inicio_mes_sp(agora) - timedelta(seconds=1))
    g = client.get("/admin/health/deep", headers=auth_headers).json()["gasto_mes_estimado"]
    assert g["valor"] == 0.105  # 3 × 0,035
    assert g["moeda"] == "BRL"
    assert g["estimado"] is True
