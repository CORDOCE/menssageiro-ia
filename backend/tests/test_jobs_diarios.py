"""Jobs diários do worker (spec 0022, AC-1..AC-4): 06:00 sincronizar modelos.

`listar_templates` é mockado (nunca toca a Meta, §5.7). `_NO_HORARIO` = 09:00 UTC = 06:00 SP (UTC-3);
`_CEDO` = 05:00 SP. Auditoria é emitida por `registrar_auditoria` em sessão própria → `db.expire_all()`
antes de consultar (molde de `test_alertas_agregacao.py`).
"""

from datetime import UTC, datetime

import pytest

import app.worker.jobs_diarios as jobs
from app.core.config import get_settings
from app.models.auditoria import Auditoria
from app.models.modelo import Modelo


@pytest.fixture(autouse=True)
def _credenciais_meta(monkeypatch):
    """Credenciais Meta presentes (staging-like) para o job passar da guarda; `listar_templates` é mockado."""
    s = get_settings()
    monkeypatch.setattr(s, "waba_id", "WABA1")
    monkeypatch.setattr(s, "whatsapp_token", "TOKEN1")

_T = [
    {
        "name": "c",
        "language": "pt_BR",
        "category": "UTILITY",
        "status": "APPROVED",
        "components": [{"type": "BODY", "text": "oi"}],
    }
]
_NO_HORARIO = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)  # 06:00 SP
_CEDO = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)  # 05:00 SP
_OP = "job.sincronizar_modelos"


def _audits(db):
    db.expire_all()
    return db.query(Auditoria).filter(Auditoria.operacao == _OP).all()


def test_roda_no_horario(db, monkeypatch):  # AC-1
    monkeypatch.setattr("app.worker.jobs_diarios.listar_templates", lambda: _T)
    jobs.sincronizar_modelos_job(_NO_HORARIO)
    db.expire_all()
    assert db.query(Modelo).filter_by(nome="c").one().status == "aprovado"
    aud = _audits(db)
    assert len(aud) == 1
    assert aud[0].status == "ok"


def test_cedo_nao_roda(db, monkeypatch):  # AC-2
    monkeypatch.setattr("app.worker.jobs_diarios.listar_templates", lambda: _T)
    jobs.sincronizar_modelos_job(_CEDO)
    db.expire_all()
    assert db.query(Modelo).count() == 0
    assert len(_audits(db)) == 0


def test_idempotente_no_dia(db, monkeypatch):  # AC-3
    calls: list[int] = []
    monkeypatch.setattr(
        "app.worker.jobs_diarios.listar_templates", lambda: (calls.append(1) or _T)
    )
    jobs.sincronizar_modelos_job(_NO_HORARIO)
    jobs.sincronizar_modelos_job(_NO_HORARIO)  # 2ª no mesmo dia
    assert len(calls) == 1  # só sincronizou uma vez
    assert len(_audits(db)) == 1


def test_falha_degrada_sem_propagar(db, monkeypatch):  # AC-4
    def _boom():
        raise RuntimeError("meta fora")

    monkeypatch.setattr("app.worker.jobs_diarios.listar_templates", _boom)
    jobs.sincronizar_modelos_job(_NO_HORARIO)  # não propaga
    db.expire_all()
    assert db.query(Modelo).count() == 0
    aud = _audits(db)
    assert len(aud) == 1
    assert aud[0].status == "error"


def test_sem_credenciais_meta_noop(db, monkeypatch):  # AC-7
    monkeypatch.setattr(get_settings(), "waba_id", None)  # sobrescreve a fixture

    def _nao_chamar():
        raise AssertionError("não deve tocar a Meta sem credenciais")

    monkeypatch.setattr("app.worker.jobs_diarios.listar_templates", _nao_chamar)
    jobs.sincronizar_modelos_job(_NO_HORARIO)
    db.expire_all()
    assert db.query(Modelo).count() == 0
    assert len(_audits(db)) == 0
