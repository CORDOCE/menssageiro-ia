"""Schema de agendamentos/configuracoes (spec 0004, AC-1): modelo + CHECK xor + singleton de config."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.agendamento import Agendamento
from app.models.configuracao import ID_CONFIG, JANELA_PADRAO, Configuracao
from app.models.contato import Contato
from app.models.modelo import Modelo


def _modelo(db) -> str:
    mid = str(uuid.uuid4())
    db.add(
        Modelo(
            id=mid, nome=f"t_{mid[:8]}", idioma="pt_BR", categoria="UTILITY",
            status="aprovado", corpo="oi", variaveis=[],
        )
    )
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


def _ag(**kw) -> Agendamento:
    base = dict(id=str(uuid.uuid4()), modelo_id=kw.pop("modelo_id"), executar_em=datetime.now(UTC))
    base.update(kw)
    return Agendamento(**base)


def test_agendamento_para_contato_ok(db):
    # AC-1: contato_id preenchido, grupo None → passa no CHECK xor.
    mid, cid = _modelo(db), _contato(db)
    db.add(_ag(modelo_id=mid, contato_id=cid, variaveis=["x"]))
    db.commit()
    ag = db.query(Agendamento).one()
    assert ag.status == "aprovado" and ag.reagendamentos == 0


def test_agendamento_para_grupo_ok(db):
    # AC-1: grupo preenchido, contato_id None → passa.
    mid = _modelo(db)
    db.add(_ag(modelo_id=mid, grupo="clientes"))
    db.commit()
    assert db.query(Agendamento).one().grupo == "clientes"


def test_xor_rejeita_ambos(db):
    # AC-1: contato_id E grupo juntos → CHECK viola.
    mid, cid = _modelo(db), _contato(db)
    db.add(_ag(modelo_id=mid, contato_id=cid, grupo="x"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_xor_rejeita_nenhum(db):
    # AC-1: nenhum dos dois → CHECK viola.
    mid = _modelo(db)
    db.add(_ag(modelo_id=mid))
    with pytest.raises(IntegrityError):
        db.commit()


def test_configuracao_singleton_defaults(db):
    # AC-1: linha única com defaults (limite 200; sem limite por contato; não pausado; janela padrão).
    db.add(Configuracao(id=ID_CONFIG))
    db.commit()
    c = db.get(Configuracao, ID_CONFIG)
    assert c.limite_diario == 200
    assert c.limite_por_contato_dia is None
    assert c.envios_pausados is False
    assert c.janela_envio == JANELA_PADRAO
