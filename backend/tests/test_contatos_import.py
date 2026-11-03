"""Importação CSV/XLSX (task 7): matriz de decisão + casos de borda (AC-9..AC-16).

Testa o serviço diretamente (o endpoint multipart é a task 8). O serviço comita por linha
(persistência parcial, AC-11) e deduplica pelo E.164 canônico.
"""

import csv
import io

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select

from app.core.telefone import mascarar_telefone
from app.models.contato import Contato
from app.services.contatos_import import ImportacaoError, importar

COLS = ["nome", "telefone", "grupo", "tags", "consentimento_origem", "consentimento_data", "observacoes"]


def _csv(linhas: list[dict[str, str]]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS)
    w.writeheader()
    for linha in linhas:
        w.writerow({c: linha.get(c, "") for c in COLS})
    return buf.getvalue().encode("utf-8")


def _xlsx(linhas: list[dict[str, str]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(COLS)
    for linha in linhas:
        ws.append([linha.get(c, "") for c in COLS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _total(db) -> int:
    return db.execute(select(func.count()).select_from(Contato)).scalar_one()


def _por_telefone(db, e164: str) -> Contato:
    return db.execute(select(Contato).where(Contato.telefone_e164 == e164)).scalar_one()


# --- AC-9/AC-12/AC-13: cria com e sem consentimento ---
def test_csv_cria_com_e_sem_consentimento(db):
    rel = importar(
        _csv(
            [
                {"nome": "A", "telefone": "11987654321",
                 "consentimento_origem": "site", "consentimento_data": "2026-10-30"},
                {"nome": "B", "telefone": "11987650000"},
            ]
        ),
        "c.csv",
        db,
    )
    assert rel.criados == 2
    assert _por_telefone(db, "+5511987654321").consentimento is True
    assert _por_telefone(db, "+5511987654321").consentimento_origem == "site"
    assert _por_telefone(db, "+5511987650000").consentimento is False
    assert rel.linhas[0].status == "criado"


# --- AC-11: parcial por linha (nome vazio e telefone inválido falham; válida persiste) ---
def test_csv_linhas_invalidas_parcial(db):
    rel = importar(
        _csv(
            [
                {"nome": "", "telefone": "11987654321"},
                {"nome": "C", "telefone": "123"},
                {"nome": "D", "telefone": "11987650000"},
            ]
        ),
        "c.csv",
        db,
    )
    assert rel.erros == 2
    assert rel.criados == 1
    assert _total(db) == 1
    assert any(r.motivo and "nome" in r.motivo for r in rel.linhas)
    assert any(r.motivo and "telefone" in r.motivo for r in rel.linhas)


# --- AC-14: reimport atualiza, não duplica ---
def test_reimport_atualiza_nao_duplica(db):
    importar(_csv([{"nome": "D", "telefone": "11987650000"}]), "c.csv", db)
    rel = importar(_csv([{"nome": "D2", "telefone": "+55 11 98765-0000"}]), "c.csv", db)
    assert _total(db) == 1
    assert _por_telefone(db, "+5511987650000").nome == "D2"
    assert rel.linhas[0].status == "atualizado"


# --- AC-15: telefone descadastrado é ignorado (não reativa) ---
def test_descadastrado_ignorado(db):
    from datetime import UTC, datetime
    from uuid import uuid4

    db.add(
        Contato(
            id=str(uuid4()), nome="Antigo", telefone_e164="+5511987650000",
            descadastrado_em=datetime.now(UTC),
        )
    )
    db.commit()
    rel = importar(_csv([{"nome": "Novo", "telefone": "11987650000"}]), "c.csv", db)
    assert rel.linhas[0].status == "ignorado"
    assert "descadastrado" in (rel.linhas[0].motivo or "")
    contato = _por_telefone(db, "+5511987650000")
    assert contato.nome == "Antigo"
    assert contato.descadastrado_em is not None


# --- Matriz linha 4: reimport sem consentimento NÃO revoga o opt-in existente ---
def test_reimport_sem_consentimento_mantem_optin(db):
    importar(
        _csv([{"nome": "A", "telefone": "11987654321",
               "consentimento_origem": "site", "consentimento_data": "2026-10-30"}]),
        "c.csv", db,
    )
    importar(_csv([{"nome": "A2", "telefone": "11987654321"}]), "c.csv", db)
    contato = _por_telefone(db, "+5511987654321")
    assert contato.consentimento is True
    assert contato.consentimento_origem == "site"


# --- Borda: duas linhas na mesma planilha com o mesmo telefone → last-wins ---
def test_duplicata_mesma_planilha_last_wins(db):
    rel = importar(
        _csv([{"nome": "X1", "telefone": "11987654321"},
              {"nome": "X2", "telefone": "+55 11 98765-4321"}]),
        "c.csv", db,
    )
    assert _total(db) == 1
    assert _por_telefone(db, "+5511987654321").nome == "X2"
    assert rel.linhas[0].status == "criado"
    assert rel.linhas[1].status == "atualizado"


# --- Borda: cabeçalho sem coluna obrigatória → erro de arquivo inteiro, nada persiste ---
def test_cabecalho_invalido_levanta(db):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["nome", "email"])
    w.writeheader()
    w.writerow({"nome": "A", "email": "a@x.com"})
    with pytest.raises(ImportacaoError):
        importar(buf.getvalue().encode("utf-8"), "c.csv", db)
    assert _total(db) == 0


# --- AC-10: XLSX equivalente ao CSV ---
def test_xlsx_equivalente(db):
    rel = importar(
        _xlsx(
            [
                {"nome": "A", "telefone": "11987654321",
                 "consentimento_origem": "site", "consentimento_data": "2026-10-30"},
                {"nome": "B", "telefone": "11987650000"},
            ]
        ),
        "c.xlsx",
        db,
    )
    assert rel.criados == 2
    assert _por_telefone(db, "+5511987654321").consentimento is True


# --- AC-16: relatório mascara o telefone (sem PII completa) ---
def test_relatorio_mascara_telefone(db):
    rel = importar(_csv([{"nome": "A", "telefone": "11987654321"}]), "c.csv", db)
    assert rel.linhas[0].telefone == mascarar_telefone("+5511987654321")
    assert rel.linhas[0].telefone != "+5511987654321"
    assert "*" in (rel.linhas[0].telefone or "")


# --- Matriz linha 3: contato existente ativo ganha consentimento no reimport ---
def test_reimport_adiciona_consentimento(db):
    importar(_csv([{"nome": "A", "telefone": "11987654321"}]), "c.csv", db)
    importar(
        _csv([{"nome": "A", "telefone": "11987654321",
               "consentimento_origem": "ligação", "consentimento_data": "2026-10-01"}]),
        "c.csv", db,
    )
    contato = _por_telefone(db, "+5511987654321")
    assert contato.consentimento is True
    assert contato.consentimento_origem == "ligação"


# --- Borda: consentimento_data inválida/futura → sem opt-in + motivo (nunca auto-consente) ---
def test_consentimento_data_invalida(db):
    rel = importar(
        _csv([{"nome": "A", "telefone": "11987654321",
               "consentimento_origem": "site", "consentimento_data": "30/10/2026"}]),
        "c.csv", db,
    )
    assert _por_telefone(db, "+5511987654321").consentimento is False
    assert "inválida" in (rel.linhas[0].motivo or "")


def test_consentimento_data_futura(db):
    rel = importar(
        _csv([{"nome": "A", "telefone": "11987654321",
               "consentimento_origem": "site", "consentimento_data": "2099-01-01"}]),
        "c.csv", db,
    )
    assert _por_telefone(db, "+5511987654321").consentimento is False
    assert "futuro" in (rel.linhas[0].motivo or "")


# --- Borda: formato não suportado e arquivos ilegíveis → erro de arquivo inteiro ---
def test_formato_nao_suportado(db):
    with pytest.raises(ImportacaoError):
        importar(b"qualquer", "contatos.txt", db)


def test_csv_encoding_invalido(db):
    with pytest.raises(ImportacaoError):
        importar(b"\xff\xfe\x00nome,telefone", "c.csv", db)


def test_xlsx_corrompido(db):
    with pytest.raises(ImportacaoError):
        importar(b"isto nao e um xlsx", "c.xlsx", db)


def test_xlsx_vazio(db):
    wb = Workbook()
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(ImportacaoError):
        importar(buf.getvalue(), "c.xlsx", db)


def test_xlsx_pula_linha_em_branco(db):
    wb = Workbook()
    ws = wb.active
    ws.append(COLS)
    ws.append([None] * len(COLS))  # linha totalmente vazia → ignorada
    ws.append(["Z", "11987654321", "", "", "", "", ""])
    buf = io.BytesIO()
    wb.save(buf)
    rel = importar(buf.getvalue(), "c.xlsx", db)
    assert rel.criados == 1
