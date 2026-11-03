"""Modelos `Modelo` e `Envio` (task 2 / AC-12, AC-13): defaults e unicidade parcial de envios."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo


def _contato(db) -> str:
    cid = str(uuid4())
    db.add(Contato(id=cid, nome="Fulano", telefone_e164="+5511987654321"))
    db.commit()
    return cid


def _envio(db, contato_id: str, **kw) -> None:
    campos = {"id": str(uuid4()), "contato_id": contato_id}
    campos.update(kw)
    db.add(Envio(**campos))
    db.commit()


def test_modelo_defaults(db):
    modelo = Modelo(id=str(uuid4()), nome="cobranca", corpo="Olá {{1}}")
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    assert modelo.status == "rascunho"
    assert modelo.idioma == "pt_BR"
    assert modelo.categoria == "UTILITY"
    assert modelo.variaveis == []


def test_envio_defaults(db):
    cid = _contato(db)
    envio = Envio(id=str(uuid4()), contato_id=cid)
    db.add(envio)
    db.commit()
    db.refresh(envio)
    assert envio.status == "criado"
    assert envio.wamid is None
    assert envio.agendamento_id is None


def test_envio_wamid_unico(db):
    cid = _contato(db)
    _envio(db, cid, wamid="wamid.ABC")
    with pytest.raises(IntegrityError):
        _envio(db, cid, wamid="wamid.ABC")


def test_envio_unicidade_parcial_agendamento(db):
    cid = _contato(db)
    # Avulsos (agendamento_id NULL) ao mesmo contato → permitidos (envio de teste/Fase 3).
    _envio(db, cid)
    _envio(db, cid)
    # Mesmo (agendamento_id não-nulo, contato_id) → viola o índice único parcial (idempotência do worker).
    _envio(db, cid, agendamento_id="ag-1")
    with pytest.raises(IntegrityError):
        _envio(db, cid, agendamento_id="ag-1")
