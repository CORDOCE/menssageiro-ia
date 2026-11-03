"""Endpoint POST /contatos/importar (task 8): multipart + limites (AC-9, AC-17, AC-18)."""

import csv
import io

from sqlalchemy import func, select

import app.db.database as db_mod
from app.core.config import get_settings
from app.models.contato import Contato

COLS = ["nome", "telefone", "grupo", "tags", "consentimento_origem", "consentimento_data", "observacoes"]


def _csv(linhas: list[dict[str, str]]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS)
    w.writeheader()
    for linha in linhas:
        w.writerow({c: linha.get(c, "") for c in COLS})
    return buf.getvalue().encode("utf-8")


def _arquivo(conteudo: bytes, nome: str = "c.csv"):
    return {"arquivo": (nome, conteudo, "text/csv")}


def _total() -> int:
    sessao = db_mod.SessionLocal()
    try:
        return sessao.execute(select(func.count()).select_from(Contato)).scalar_one()
    finally:
        sessao.close()


def test_importar_sucesso(client, auth_headers, db):
    conteudo = _csv([{"nome": "A", "telefone": "11987654321"}])
    r = client.post("/contatos/importar", files=_arquivo(conteudo), headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["criados"] == 1


def test_importar_sem_auth_401(client):
    r = client.post("/contatos/importar", files=_arquivo(_csv([{"nome": "A", "telefone": "11987654321"}])))
    assert r.status_code == 401


def test_importar_arquivo_grande_413(client, auth_headers, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "import_max_bytes", 10)
    conteudo = _csv([{"nome": "A", "telefone": "11987654321"}])  # > 10 bytes
    r = client.post("/contatos/importar", files=_arquivo(conteudo), headers=auth_headers)
    assert r.status_code == 413
    assert _total() == 0


def test_importar_muitas_linhas_422(client, auth_headers, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "import_max_linhas", 1)
    conteudo = _csv(
        [{"nome": "A", "telefone": "11987654321"}, {"nome": "B", "telefone": "11987650000"}]
    )
    r = client.post("/contatos/importar", files=_arquivo(conteudo), headers=auth_headers)
    assert r.status_code == 422
    assert _total() == 0
