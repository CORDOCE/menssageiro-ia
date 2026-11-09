"""Auditoria não-bloqueante (CLAUDE.md §5.8, §7).

Falha ao auditar NUNCA propaga para o chamador — é logada e descartada, para que a instrumentação
não derrube a operação. Cada escrita abre sua própria sessão (não interfere na transação do chamador).
`SessionLocal` é importado de forma preguiçosa para que testes possam repontá-lo antes.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def registrar_auditoria(
    operacao: str,
    ator_email: str | None = None,
    alvo_tipo: str | None = None,
    alvo_id: str | None = None,
    status: str = "success",
    metadados: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    alertar: bool = False,
) -> None:
    """Grava uma entrada de auditoria. Nunca levanta exceção.

    `alertar=True` em eventos de fluxo crítico (`status` error/warning) também emite ao Sentry
    para o §12 poder alertar (spec 0017 / O1). Sem PII; no-op sem Sentry inicializado.
    """
    try:
        import app.db.database as _db
        from app.models.auditoria import Auditoria

        if alertar:
            from app.core.observabilidade import alertar_evento

            alertar_evento(operacao, status, correlation_id, metadados)

        entrada = Auditoria(
            id=str(uuid.uuid4()),
            criado_em=datetime.now(UTC),
            ator_email=ator_email,
            operacao=operacao,
            alvo_tipo=alvo_tipo,
            alvo_id=alvo_id,
            status=status,
            metadados=json.dumps(metadados, default=str) if metadados else None,
            correlation_id=correlation_id,
        )
        db = _db.SessionLocal()
        try:
            db.add(entrada)
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("falha_ao_gravar_auditoria: operacao=%s alvo_id=%s", operacao, alvo_id)
