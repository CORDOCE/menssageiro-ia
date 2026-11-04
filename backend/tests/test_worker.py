"""Testes do heartbeat do worker. O disparo (spec 0004) é coberto em `test_worker_disparo.py`.

Nota (§1.7): o antigo `test_worker_fase1_nao_envia_nada` (que proibia o worker de enviar) foi removido —
a Fase 4 (spec 0004) reverte esse non-goal da Fase 1: o worker agora dispara agendamentos.
"""

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
