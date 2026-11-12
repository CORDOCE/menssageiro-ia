"""Sincronização de modelos (spec 0022 — extraído de `api/modelos.py`, spec 0010).

Upsert dos templates da Meta em `modelos`, reusado pelo endpoint manual (`POST /modelos/sincronizar`,
spec 0013) e pelo job diário do worker (06:00, spec 0022). Recebe os `templates` já lidos — quem chama
faz `listar_templates()` —, faz upsert por `(nome, idioma)` e registra auditoria. A Meta é a fonte da
verdade do status/categoria (§5.3: só `aprovado` inicia conversa).
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.models.modelo import Modelo

# Mapa status da Meta → nosso. Tudo que não for claramente APPROVED fica != "aprovado" (invariante §5.3).
_STATUS_META: dict[str, str] = {
    "APPROVED": "aprovado",
    "REJECTED": "rejeitado",
    "PENDING": "pendente",
    "IN_APPEAL": "pendente",
    "PENDING_DELETION": "pausado",
    "DELETED": "pausado",
    "DISABLED": "pausado",
    "PAUSED": "pausado",
    "LIMIT_EXCEEDED": "pausado",
    "ARCHIVED": "pausado",
}
_PLACEHOLDER = re.compile(r"\{\{(\d+)\}\}")


class SincronizarResultado(BaseModel):
    total: int
    criados: int
    atualizados: int


def _extrair_componentes(
    components: list[dict[str, Any]] | None,
) -> tuple[str, str | None, list[str]]:
    """De `components` da Meta extrai (corpo BODY, formato do HEADER, variáveis {{n}} do corpo)."""
    corpo = ""
    cabecalho_tipo: str | None = None
    for comp in components or []:
        tipo = str(comp.get("type") or "").upper()
        if tipo == "BODY":
            corpo = str(comp.get("text") or "")
        elif tipo == "HEADER":
            cabecalho_tipo = comp.get("format")
    variaveis = sorted({m for m in _PLACEHOLDER.findall(corpo)}, key=int)
    return corpo, cabecalho_tipo, variaveis


def sincronizar_modelos(
    db: Session, templates: list[dict[str, Any]], *, ator_email: str | None = None
) -> SincronizarResultado:
    """Upsert dos `templates` em `modelos` por `(nome, idioma)`; audita `modelos_sincronizados`.
    `ator_email=None` = ator sistema (job diário); o email do operador no caminho manual."""
    criados = 0
    atualizados = 0
    for t in templates:
        nome = t.get("name")
        idioma = t.get("language")
        if not nome or not idioma:
            continue
        corpo, cabecalho_tipo, variaveis = _extrair_componentes(t.get("components"))
        status = _STATUS_META.get(str(t.get("status") or "").upper(), "pendente")
        categoria = str(t.get("category") or "UTILITY")
        existente = db.execute(
            select(Modelo).where(Modelo.nome == nome, Modelo.idioma == idioma)
        ).scalar_one_or_none()
        if existente is None:
            db.add(
                Modelo(
                    id=str(uuid.uuid4()), nome=nome, idioma=idioma, categoria=categoria,
                    status=status, corpo=corpo, cabecalho_tipo=cabecalho_tipo, variaveis=variaveis,
                )
            )
            criados += 1
        else:
            existente.categoria = categoria
            existente.status = status
            existente.corpo = corpo
            existente.cabecalho_tipo = cabecalho_tipo
            existente.variaveis = variaveis
            atualizados += 1
    db.commit()
    registrar_auditoria(
        operacao="modelos_sincronizados",
        ator_email=ator_email,
        metadados={"total": len(templates), "criados": criados, "atualizados": atualizados},
    )
    return SincronizarResultado(total=len(templates), criados=criados, atualizados=atualizados)
