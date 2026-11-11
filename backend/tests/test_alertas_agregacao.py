"""Alertas de agregação (spec 0019): check-in de liveness do worker + taxa de falha diária.

`AGORA` = terça 2026-11-03 13:00 UTC (= 10:00 America/Sao_Paulo). Sem Sentry inicializado nos testes
(sem `SENTRY_DSN`): `capture_checkin`/`capture_message` são no-op — mockados quando se observa a chamada.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.auditoria import Auditoria
from app.models.contato import Contato
from app.models.envio import Envio
from app.worker import alertas
from app.worker.alertas import verificar_taxa_falha

AGORA = datetime(2026, 11, 3, 13, 0, tzinfo=UTC)
_OP = "envios.taxa_falha_alta"


@pytest.fixture
def contato(db):
    cid = str(uuid.uuid4())
    db.add(
        Contato(id=cid, nome="C", telefone_e164=f"+5531{uuid.uuid4().int % 10**8:08d}", consentimento=True)
    )
    db.commit()
    return cid


def _envio(db, contato_id, status, criado_em):
    db.add(Envio(id=str(uuid.uuid4()), contato_id=contato_id, status=status, criado_em=criado_em))
    db.commit()


def _semear(db, contato_id, *, enviados, falhas, quando=None):
    """Semeia `enviados` (status 'enviado') + `falhas` (status 'falhou') — tentativas = soma."""
    quando = quando or (AGORA - timedelta(hours=1))
    for _ in range(enviados):
        _envio(db, contato_id, "enviado", quando)
    for _ in range(falhas):
        _envio(db, contato_id, "falhou", quando)


def _spy_capture_message(monkeypatch):
    chamadas: list = []
    monkeypatch.setattr("sentry_sdk.capture_message", lambda *a, **k: chamadas.append((a, k)))
    return chamadas


def _audits_taxa(db):
    db.expire_all()
    return db.query(Auditoria).filter(Auditoria.operacao == _OP).all()


# --- Alerta B: taxa de falha (AC-2..AC-5, AC-7 + bordas) ---


def test_ac2_taxa_alta_emite_alerta_uma_vez(db, contato, monkeypatch):
    chamadas = _spy_capture_message(monkeypatch)
    _semear(db, contato, enviados=18, falhas=2)  # 20 tentativas, 10% > 5%
    verificar_taxa_falha(AGORA)
    assert len(_audits_taxa(db)) == 1
    assert len(chamadas) == 1  # registrar_auditoria(alertar=True) → alertar_evento → capture_message


def test_ac3_abaixo_do_piso_nao_alerta(db, contato, monkeypatch):
    chamadas = _spy_capture_message(monkeypatch)
    _semear(db, contato, enviados=4, falhas=6)  # 10 tentativas (< 20), 60%
    verificar_taxa_falha(AGORA)
    assert len(_audits_taxa(db)) == 0
    assert chamadas == []


def test_ac4_taxa_no_limite_nao_alerta(db, contato, monkeypatch):
    chamadas = _spy_capture_message(monkeypatch)
    _semear(db, contato, enviados=20, falhas=1)  # 21 tentativas, ~4.76% <= 5%
    verificar_taxa_falha(AGORA)
    assert len(_audits_taxa(db)) == 0
    assert chamadas == []


def test_ac5_idempotencia_diaria_nao_emite_segundo(db, contato, monkeypatch):
    db.add(Auditoria(id=str(uuid.uuid4()), operacao=_OP, status="warning", criado_em=AGORA))
    db.commit()
    chamadas = _spy_capture_message(monkeypatch)
    _semear(db, contato, enviados=18, falhas=2)
    verificar_taxa_falha(AGORA)
    assert len(_audits_taxa(db)) == 1  # não criou um segundo alerta no mesmo dia
    assert chamadas == []


def test_ac5_alerta_de_ontem_nao_bloqueia_hoje(db, contato, monkeypatch):
    db.add(
        Auditoria(id=str(uuid.uuid4()), operacao=_OP, status="warning", criado_em=AGORA - timedelta(days=1))
    )
    db.commit()
    chamadas = _spy_capture_message(monkeypatch)
    _semear(db, contato, enviados=18, falhas=2)
    verificar_taxa_falha(AGORA)
    assert len(_audits_taxa(db)) == 2  # o de ontem + o de hoje
    assert len(chamadas) == 1


def test_ac7_metadados_sem_pii(db, contato, monkeypatch):
    _spy_capture_message(monkeypatch)
    _semear(db, contato, enviados=18, falhas=2)
    verificar_taxa_falha(AGORA)
    aud = _audits_taxa(db)[0]
    meta = json.loads(aud.metadados)
    assert set(meta) <= {"tentativas", "falhas", "pct"}
    assert all(isinstance(v, (int, float)) for v in meta.values())


def test_tentativas_zero_nao_quebra_nem_alerta(db, monkeypatch):
    chamadas = _spy_capture_message(monkeypatch)
    verificar_taxa_falha(AGORA)  # sem envios
    assert len(_audits_taxa(db)) == 0
    assert chamadas == []


def test_envios_fora_da_janela_24h_nao_contam(db, contato, monkeypatch):
    chamadas = _spy_capture_message(monkeypatch)
    _semear(db, contato, enviados=18, falhas=2, quando=AGORA - timedelta(hours=25))  # fora das 24h
    verificar_taxa_falha(AGORA)
    assert len(_audits_taxa(db)) == 0
    assert chamadas == []


# --- Alerta A: check-in de liveness (AC-1, AC-6) ---


def test_ac1_checkin_ok_por_ciclo(db, monkeypatch):
    chamadas: list = []
    monkeypatch.setattr("sentry_sdk.crons.capture_checkin", lambda **k: chamadas.append(k))
    from app.worker.__main__ import executar

    executar(ciclos=1, intervalo_s=0)
    assert len(chamadas) == 1
    k = chamadas[0]
    assert k["monitor_slug"] == alertas._MONITOR_SLUG
    assert k["status"] == "ok"
    assert "schedule" in k["monitor_config"]


def test_ac6_sem_dsn_no_op_ciclo_nao_quebra(db):
    from app.worker.__main__ import executar, ler_heartbeat

    executar(ciclos=1, intervalo_s=0)  # Sentry não inicializado → capture_* são no-op
    assert ler_heartbeat() is not None  # ciclo completou (heartbeat gravado)
