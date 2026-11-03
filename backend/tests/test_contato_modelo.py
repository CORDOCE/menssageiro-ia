"""Testes do modelo `Contato` (task 1 / AC-1): defaults de domínio e unicidade do telefone.

Usa o banco de teste (conftest) via `create_all`. Regras comportamentais completas (CRUD,
consentimento, descadastro) ficam nas tasks de API/serviço.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.contato import Contato


def _novo(db, **kw):
    campos = {"id": str(uuid4()), "nome": "Fulano", "telefone_e164": "+5511987654321"}
    campos.update(kw)
    contato = Contato(**campos)
    db.add(contato)
    db.commit()
    db.refresh(contato)
    return contato


def test_defaults_de_dominio(db):
    # Sem opt-in informado, o contato nasce bloqueado: consentimento=False, tags vazias, ativo.
    contato = _novo(db)
    assert contato.consentimento is False
    assert contato.tags == []
    assert contato.descadastrado_em is None
    assert contato.consentimento_data is None
    assert contato.criado_em is not None


def test_telefone_e164_unico(db):
    _novo(db)
    with pytest.raises(IntegrityError):
        _novo(db)  # mesmo telefone_e164 (id novo gerado no helper) -> viola o índice único
