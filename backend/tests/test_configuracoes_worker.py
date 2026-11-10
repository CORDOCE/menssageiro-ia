"""Integração config↔worker (spec 0018, AC-3/AC-4): a config editada via PATCH /configuracoes
é lida pelo worker a cada ciclo (fonte runtime, ADR 0008).

Os testes de `test_worker_disparo.py` setam a config direto no banco; aqui o fio é ponta a ponta:
PATCH pela API → `processar_ciclo` observa o efeito. Nenhum envio real (§5.7): `FakeEnviar`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.agendamento import Agendamento
from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo
from app.worker.disparo import processar_ciclo

AGORA = datetime(2026, 11, 3, 13, 0, tzinfo=UTC)  # terça 10:00 SP, dentro da janela padrão


class FakeEnviar:
    def __init__(self) -> None:
        self.chamadas: list[str] = []

    def __call__(self, telefone: str, nome: str, idioma: str, componentes: list) -> str:
        self.chamadas.append(telefone)
        return f"wamid.{uuid.uuid4().hex[:8]}"


def _modelo(db) -> str:
    mid = str(uuid.uuid4())
    db.add(Modelo(id=mid, nome=f"t_{mid[:8]}", corpo="oi", status="aprovado"))
    db.commit()
    return mid


def _contato(db) -> str:
    cid = str(uuid.uuid4())
    db.add(Contato(id=cid, nome="C", telefone_e164=f"+5531{uuid.uuid4().int % 100000000:08d}",
                   consentimento=True))
    db.commit()
    return cid


def _agendamento(db, modelo_id, contato_id) -> str:
    aid = str(uuid.uuid4())
    db.add(Agendamento(id=aid, modelo_id=modelo_id, contato_id=contato_id,
                       executar_em=AGORA - timedelta(minutes=1), status="aprovado", variaveis=["x"]))
    db.commit()
    return aid


def test_pausa_via_api_worker_nao_dispara(client, auth_headers, db):  # AC-4 ponta a ponta
    aid = _agendamento(db, _modelo(db), _contato(db))
    r = client.patch("/configuracoes", headers=auth_headers, json={"envios_pausados": True})
    assert r.status_code == 200

    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)

    db.expire_all()
    assert fake.chamadas == []
    assert db.query(Envio).count() == 0
    assert db.get(Agendamento, aid).status == "aprovado"  # intacto, só não disparou


def test_limite_diario_via_api_respeitado(client, auth_headers, db):  # AC-3 ponta a ponta
    # 1 envio recente conta p/ as 24h; com o default (200) ainda enviaria.
    db.add(Envio(id=str(uuid.uuid4()), contato_id=_contato(db), status="enviado",
                 wamid=f"w.{uuid.uuid4().hex[:6]}"))
    db.commit()
    aid = _agendamento(db, _modelo(db), _contato(db))

    r = client.patch("/configuracoes", headers=auth_headers, json={"limite_diario": 1})
    assert r.status_code == 200

    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)

    db.expire_all()
    ag = db.get(Agendamento, aid)
    # worker leu limite=1 (via API) → enviados(1) >= limite → adia, não dispara.
    assert fake.chamadas == []
    assert ag.status == "aprovado" and ag.executar_em > AGORA
