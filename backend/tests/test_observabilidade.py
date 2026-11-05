"""Inicialização do Sentry e mascaramento de PII (spec 0009 / S3)."""

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
