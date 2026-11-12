"""Upload de anexos PDF (spec 0025, AC-1..AC-4): POST /anexos autenticado, valida tipo/tamanho/magic."""

from app.core.config import get_settings
from app.models.anexo import Anexo

_PDF = b"%PDF-1.4\n%boleto de teste"


def _upload(client, headers, *, conteudo=_PDF, nome="boleto.pdf", mime="application/pdf"):
    return client.post("/anexos", files={"arquivo": (nome, conteudo, mime)}, headers=headers)


def test_sem_auth_401(client):  # AC-1
    assert _upload(client, {}).status_code == 401


def test_pdf_ok(client, auth_headers, db):  # AC-2
    r = _upload(client, auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["nome_arquivo"] == "boleto.pdf"
    assert body["tamanho"] == len(_PDF)
    db.expire_all()
    anexo = db.query(Anexo).one()
    assert bytes(anexo.conteudo) == _PDF


def test_rejeita_mime_errado(client, auth_headers):  # AC-3
    assert _upload(client, auth_headers, mime="text/plain").status_code == 422


def test_rejeita_sem_magic_pdf(client, auth_headers):  # AC-3
    assert _upload(client, auth_headers, conteudo=b"NAO_EH_PDF", mime="application/pdf").status_code == 422


def test_rejeita_acima_do_limite(client, auth_headers, monkeypatch):  # AC-4
    monkeypatch.setattr(get_settings(), "anexo_max_bytes", 10)
    r = _upload(client, auth_headers, conteudo=b"%PDF-" + b"x" * 100)
    assert r.status_code == 422
