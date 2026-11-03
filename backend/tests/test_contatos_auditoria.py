"""Auditoria da importação (task 9 / AC-16, §5.8): registra contagens, nunca PII."""

import csv
import io
import json

from sqlalchemy import select

from app.models.auditoria import Auditoria
from app.services.contatos_import import importar

COLS = ["nome", "telefone", "grupo", "tags", "consentimento_origem", "consentimento_data", "observacoes"]


def _csv(linhas: list[dict[str, str]]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS)
    w.writeheader()
    for linha in linhas:
        w.writerow({c: linha.get(c, "") for c in COLS})
    return buf.getvalue().encode("utf-8")


def test_importacao_audita_contagens_sem_telefone(db):
    importar(
        _csv([{"nome": "A", "telefone": "11987654321"}, {"nome": "B", "telefone": "11987650000"}]),
        "c.csv",
        db,
        ator_email="admin@teste.com",
    )
    registros = (
        db.execute(select(Auditoria).where(Auditoria.operacao == "contatos_importados"))
        .scalars()
        .all()
    )
    assert len(registros) == 1
    meta = registros[0].metadados or ""
    # contagens presentes
    assert json.loads(meta)["criados"] == 2
    # nenhum telefone (completo ou nacional) vaza na auditoria
    assert "11987654321" not in meta
    assert "5511987654321" not in meta
