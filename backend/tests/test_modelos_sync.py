"""Service de sincronização de modelos (spec 0022, AC-6): upsert reusado pelo endpoint e pelo job.

Testa a lógica pura de upsert a partir de uma lista de templates (sem tocar a Meta).
"""

from app.models.modelo import Modelo
from app.services.modelos_sync import sincronizar_modelos


def _tpl(nome, *, status="APPROVED", body="Oi {{1}} {{2}}", header="TEXT"):
    comps: list[dict] = [{"type": "BODY", "text": body}]
    if header:
        comps.insert(0, {"type": "HEADER", "format": header})
    return {
        "name": nome,
        "language": "pt_BR",
        "category": "UTILITY",
        "status": status,
        "components": comps,
    }


def test_cria_e_mapeia_status(db):  # AC-6
    r = sincronizar_modelos(db, [_tpl("cobranca")], ator_email="a@b.com")
    assert (r.total, r.criados, r.atualizados) == (1, 1, 0)
    m = db.query(Modelo).filter_by(nome="cobranca").one()
    assert m.status == "aprovado"
    assert m.variaveis == ["1", "2"]
    assert m.cabecalho_tipo == "TEXT"


def test_atualiza_existente(db):  # AC-6
    sincronizar_modelos(db, [_tpl("cobranca")], ator_email=None)
    r = sincronizar_modelos(
        db, [_tpl("cobranca", status="REJECTED", body="x", header=None)], ator_email=None
    )
    assert (r.criados, r.atualizados) == (0, 1)
    assert db.query(Modelo).filter_by(nome="cobranca").one().status == "rejeitado"


def test_ignora_sem_nome_ou_idioma(db):  # AC-6 (borda)
    r = sincronizar_modelos(db, [{"language": "pt_BR"}, {"name": "x"}], ator_email=None)
    assert (r.total, r.criados, r.atualizados) == (2, 0, 0)
