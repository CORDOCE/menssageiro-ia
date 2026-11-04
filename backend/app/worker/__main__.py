"""Worker do Mensageiro: loop de disparo + heartbeat.

A cada ciclo (~60 s): lê o heartbeat anterior, roda o passo de **disparo** (`processar_ciclo`, spec 0004)
e grava `saude.ultimo_ciclo_em`. Nenhum estado em memória (BRIEFING §5): tudo vai para o banco.
`python -m app.worker` roda `main()`.
"""

import time
from datetime import UTC, datetime

import app.db.database as _db
from app.core.audit import registrar_auditoria
from app.core.config import get_settings
from app.models.saude import Saude
from app.worker.disparo import processar_ciclo

_ID_WORKER = "worker"


def ler_heartbeat() -> datetime | None:
    """Último `ultimo_ciclo_em` do worker (ou None) — usado para detectar gap de indisponibilidade."""
    db = _db.SessionLocal()
    try:
        s = db.get(Saude, _ID_WORKER)
        return s.ultimo_ciclo_em if s else None
    finally:
        db.close()


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
    nos testes. A cada ciclo dispara os agendamentos vencidos e grava o heartbeat."""
    espera = intervalo_s if intervalo_s is not None else get_settings().worker_intervalo_s
    feitos = 0
    while ciclos is None or feitos < ciclos:
        anterior = ler_heartbeat()
        try:
            processar_ciclo(heartbeat_anterior=anterior, intervalo_s=int(espera))
        except Exception:  # pragma: no cover — um ciclo ruim não pode derrubar o worker
            registrar_auditoria("worker.ciclo_erro", status="error")
        gravar_heartbeat()
        feitos += 1
        if ciclos is not None and feitos >= ciclos:
            break
        time.sleep(espera)


def main() -> None:
    executar()


if __name__ == "__main__":  # pragma: no cover
    main()
