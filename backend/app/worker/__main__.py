"""Worker do Mensageiro (task 8): loop de heartbeat.

Fase 1: a cada ciclo (~60 s) grava `saude.ultimo_ciclo_em` e **não envia nada** — envios são
das fases 3+ (non-goal). Nenhum estado em memória (BRIEFING §5): o heartbeat vai para o banco.
`python -m app.worker` roda `main()`.
"""

import time
from datetime import UTC, datetime

import app.db.database as _db
from app.core.config import get_settings
from app.models.saude import Saude

_ID_WORKER = "worker"


def gravar_heartbeat() -> datetime:
    """Grava/atualiza o heartbeat do worker (linha única); retorna o instante gravado."""
    agora = datetime.now(UTC)
    db = _db.SessionLocal()
    try:
        s = db.get(Saude, _ID_WORKER)
        if s is None:
            db.add(Saude(id=_ID_WORKER, ultimo_ciclo_em=agora))
        else:
            s.ultimo_ciclo_em = agora
        db.commit()
    finally:
        db.close()
    return agora


def executar(ciclos: int | None = None, intervalo_s: float | None = None) -> None:
    """Loop do worker. `ciclos=None` roda indefinidamente (produção); um número finito é usado
    nos testes. Só grava heartbeat — nenhum envio."""
    espera = intervalo_s if intervalo_s is not None else get_settings().worker_intervalo_s
    feitos = 0
    while ciclos is None or feitos < ciclos:
        gravar_heartbeat()
        feitos += 1
        if ciclos is not None and feitos >= ciclos:
            break
        time.sleep(espera)


def main() -> None:
    executar()


if __name__ == "__main__":  # pragma: no cover
    main()
