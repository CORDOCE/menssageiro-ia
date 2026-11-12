"""Inicialização do Sentry e mascaramento de PII (spec 0009 / S3)."""

import re

import sentry_sdk

from app.core import observabilidade as obs
from app.core.config import get_settings
from app.worker import __main__ as worker


def test_nao_inicializa_sem_dsn(monkeypatch):
    """AC-2: sem SENTRY_DSN, não chama init e retorna False."""
    chamadas: list[dict] = []
    monkeypatch.setattr(obs.sentry_sdk, "init", lambda **kw: chamadas.append(kw))
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    get_settings.cache_clear()
    try:
        assert obs.configurar_sentry() is False
        assert chamadas == []
    finally:
        get_settings.cache_clear()


def test_inicializa_com_dsn(monkeypatch):
    """AC-1: com SENTRY_DSN, chama init uma vez com before_send e sem PII default."""
    chamadas: list[dict] = []
    monkeypatch.setattr(obs.sentry_sdk, "init", lambda **kw: chamadas.append(kw))
    monkeypatch.setenv("SENTRY_DSN", "https://abc@o1.ingest.sentry.io/1")
    get_settings.cache_clear()
    try:
        assert obs.configurar_sentry() is True
        assert len(chamadas) == 1
        assert chamadas[0]["before_send"] is obs._mascarar_pii
        assert chamadas[0]["send_default_pii"] is False
    finally:
        get_settings.cache_clear()


def test_mascarar_telefone_em_mensagem_e_excecao():
    """AC-3: telefones (dígitos) são mascarados em message e exception.value."""
    ev = {
        "message": "falha ao enviar para 5531999887766 agora",
        "exception": {"values": [{"value": "numero 5531912345678 invalido"}]},
    }
    out = obs._mascarar_pii(ev)
    assert out is not None
    assert "5531999887766" not in out["message"]
    assert "5531912345678" not in out["exception"]["values"][0]["value"]


def test_mascarar_telefone_em_contexts():
    """AC-7 (spec 0017): PII em contexts (metadados de alertar_evento) é mascarada."""
    ev = {"contexts": {"evento": {"telefone": "5531999887766", "codigo": "190"}}}
    out = obs._mascarar_pii(ev)
    assert out is not None
    assert "999887766" not in out["contexts"]["evento"]["telefone"]  # dígitos mascarados
    assert out["contexts"]["evento"]["telefone"].endswith("66")  # 2 últimos preservados
    assert out["contexts"]["evento"]["codigo"] == "190"  # <8 dígitos, não mascarado


def test_remove_corpo_e_cookies_da_requisicao():
    """AC-3: corpo e cookies da requisição são removidos do evento."""
    ev = {"request": {"data": {"senha": "x"}, "cookies": "sessao=abc", "url": "/x"}}
    out = obs._mascarar_pii(ev)
    assert out is not None
    assert "data" not in out["request"]
    assert "cookies" not in out["request"]
    assert out["request"]["url"] == "/x"


def test_worker_ciclo_erro_vai_ao_sentry(db, monkeypatch):
    """AC-4: exceção no ciclo do worker → capture_exception (além da auditoria)."""
    capturas: list[bool] = []

    def _raise(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(worker, "processar_ciclo", _raise)
    monkeypatch.setattr(sentry_sdk, "capture_exception", lambda *a, **k: capturas.append(True))
    worker.executar(ciclos=1, intervalo_s=0)
    assert capturas == [True]


# --- alerta de fluxo crítico ao Sentry (spec 0017 / dívida O1) ---
from app.core.audit import registrar_auditoria  # noqa: E402


def _mock_capture(monkeypatch):
    chamadas: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        obs.sentry_sdk, "capture_message", lambda msg, **kw: chamadas.append((msg, kw))
    )
    return chamadas


def test_alertar_error_emite_level_error(db, monkeypatch):  # AC-1
    chamadas = _mock_capture(monkeypatch)
    registrar_auditoria(
        "agendamento.falhou", status="error", correlation_id="c1",
        metadados={"motivo": "modelo_nao_aprovado"}, alertar=True,
    )
    assert len(chamadas) == 1
    msg, kw = chamadas[0]
    assert msg == "agendamento.falhou"
    assert kw.get("level") == "error"


def test_alertar_warning_emite_level_warning(db, monkeypatch):  # AC-2
    chamadas = _mock_capture(monkeypatch)
    registrar_auditoria("agendamento.limite_por_agendamento", status="warning", alertar=True)
    assert chamadas and chamadas[0][1].get("level") == "warning"


def test_sem_alertar_nao_emite(db, monkeypatch):  # AC-3
    chamadas = _mock_capture(monkeypatch)
    registrar_auditoria("agendamento.falhou", status="error")  # alertar=False (default)
    assert chamadas == []


def test_alertar_so_error_warning(db, monkeypatch):  # AC-4
    chamadas = _mock_capture(monkeypatch)
    registrar_auditoria("envio.enviado", status="success", alertar=True)
    registrar_auditoria("envio.pulado", status="skipped", alertar=True)
    assert chamadas == []


def test_alertar_sem_dsn_noop(db):  # AC-6 — Sentry não inicializado: no-op, não levanta
    registrar_auditoria("agendamento.falhou", status="error", correlation_id="c", alertar=True)
    # chegou aqui sem exceção; auditoria gravada


def test_alertar_sem_pii_na_mensagem(db, monkeypatch):  # AC-7
    chamadas = _mock_capture(monkeypatch)
    registrar_auditoria("envio.falhou", status="error", metadados={"codigo": "190"}, alertar=True)
    msg, _ = chamadas[0]
    assert not re.search(r"\d{8,}", msg)  # sem telefone na mensagem


# --- push nos eventos §12 (spec 0023, AC-7/AC-8) ---


def test_alertar_dispara_push_em_error(monkeypatch):  # AC-7 (0023)
    pushes: list[dict] = []
    monkeypatch.setattr("app.services.push.enviar_push", lambda **k: pushes.append(k))
    obs.alertar_evento("evt.critico", "error")
    assert len(pushes) == 1
    assert pushes[0]["titulo"] == "evt.critico"  # título = operação (sem PII)
    assert not re.search(r"\d{8,}", pushes[0]["corpo"])  # corpo sem telefone (AC-8)


def test_alertar_nao_dispara_push_em_ok(monkeypatch):  # AC-7 (0023)
    pushes: list[dict] = []
    monkeypatch.setattr("app.services.push.enviar_push", lambda **k: pushes.append(k))
    obs.alertar_evento("evt.ok", "ok")
    assert pushes == []  # ok/info não geram alerta nem push
