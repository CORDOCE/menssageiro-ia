"""Testes do worker (task 8, AC-9): heartbeat por ciclo, sem envio."""

import inspect
import time
from datetime import datetime

import app.db.database as db_mod
import app.worker.__main__ as worker
from app.models.saude import Saude


def _ler_heartbeat() -> datetime | None:
    sessao = db_mod.SessionLocal()
    try:
        s = sessao.get(Saude, "worker")
        return s.ultimo_ciclo_em if s else None
    finally:
        sessao.close()


def test_gravar_heartbeat_cria_e_atualiza(db):
    # AC-9: grava o heartbeat; a 2ª gravação atualiza (avança).
    assert _ler_heartbeat() is None
    t1 = worker.gravar_heartbeat()
    assert _ler_heartbeat() is not None
    time.sleep(0.01)
    t2 = worker.gravar_heartbeat()
    assert t2 >= t1


def test_executar_n_ciclos_grava_heartbeat(db):
    # AC-9: rodar mais de um ciclo grava o heartbeat (intervalo_s=0 para não dormir no teste).
    worker.executar(ciclos=2, intervalo_s=0)
    assert _ler_heartbeat() is not None


def test_main_chama_executar(monkeypatch):
    chamado = {}
    monkeypatch.setattr(worker, "executar", lambda: chamado.setdefault("ok", True))
    worker.main()
    assert chamado.get("ok") is True


def test_worker_fase1_nao_envia_nada():
    # AC-9 / non-goal: na Fase 1 o worker não integra nada de envio (sem cliente WhatsApp/Meta).
    fonte = inspect.getsource(worker).lower()
    assert "whatsapp" not in fonte
    assert "whatsapp_client" not in fonte
    assert "graph.facebook" not in fonte
