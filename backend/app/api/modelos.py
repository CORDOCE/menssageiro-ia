"""Router de modelos (spec 0003, task 11).

Expõe o envio de **teste** (`POST /modelos/{id}/enviar-teste`), protegido por sessão e **restrito ao
número de teste** (§4: nunca número real). Cria um `envio` avulso (sem agendamento) e chama o cliente
WhatsApp. O caminho de produção (disparo em escala) é do worker, na Fase 4.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.core.auth_deps import usuario_atual
from app.core.config import get_settings
from app.core.telefone import mascarar_telefone, normalizar_e164
from app.db.database import get_db
from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo
from app.models.usuario import Usuario
from app.services.whatsapp_client import enviar_template, listar_templates

router = APIRouter(prefix="/modelos", tags=["modelos"])

# Status possíveis do template (espelham a Meta; ver models/modelo.py).
StatusModelo = Literal["rascunho", "pendente", "aprovado", "rejeitado", "pausado"]

# Mapa status da Meta → nosso status. Fonte: enum oficial de message_templates (consultada 2026-11-05).
# Tudo que não for claramente APPROVED fica != "aprovado" (invariante §5.3: só aprovado inicia conversa).
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


def _extrair_componentes(components: list[dict[str, Any]] | None) -> tuple[str, str | None, list[str]]:
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


class SincronizarResultado(BaseModel):
    total: int
    criados: int
    atualizados: int


@router.post("/sincronizar", response_model=SincronizarResultado)
def sincronizar(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> SincronizarResultado:
    """Lê os templates da Meta (Cloud API, só leitura) e faz upsert em `modelos` por (nome, idioma).
    A Meta é a fonte da verdade do status/categoria (§5.3). Protegido por sessão (spec 0010)."""
    templates = listar_templates()
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
        ator_email=usuario.email,
        metadados={"total": len(templates), "criados": criados, "atualizados": atualizados},
    )
    return SincronizarResultado(total=len(templates), criados=criados, atualizados=atualizados)


class ModeloRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    idioma: str
    categoria: str
    status: str
    corpo: str
    cabecalho_tipo: str | None
    variaveis: list[str]


@router.get("", response_model=list[ModeloRead])
def listar_modelos(
    status: StatusModelo | None = Query(default=None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> list[Modelo]:
    """Lista os modelos (templates), opcionalmente filtrando por `status` (ex.: `aprovado` para a
    tela Nova mensagem). Ordena por nome. Protegido por sessão (spec 0010)."""
    stmt = select(Modelo).order_by(Modelo.nome)
    if status is not None:
        stmt = stmt.where(Modelo.status == status)
    return list(db.execute(stmt).scalars().all())


class EnviarTeste(BaseModel):
    telefone: str
    componentes: list[dict[str, Any]] = Field(default_factory=list)


class EnvioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contato_id: str
    modelo_id: str | None
    wamid: str | None
    status: str


@router.post("/{modelo_id}/enviar-teste", status_code=201, response_model=EnvioRead)
def enviar_teste(
    modelo_id: str,
    payload: EnviarTeste,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> Envio:
    modelo = db.get(Modelo, modelo_id)
    if modelo is None:
        raise HTTPException(status_code=404, detail="modelo não encontrado")
    try:
        telefone = normalizar_e164(payload.telefone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="telefone inválido") from exc

    cfg = get_settings()
    teste = normalizar_e164(cfg.whatsapp_test_number) if cfg.whatsapp_test_number else None
    if teste is None or telefone != teste:
        raise HTTPException(
            status_code=403, detail="envio de teste permitido apenas para o número de teste"
        )

    contato = db.execute(select(Contato).where(Contato.telefone_e164 == telefone)).scalar_one_or_none()
    if contato is None:
        contato = Contato(id=str(uuid.uuid4()), nome="Número de teste", telefone_e164=telefone)
        db.add(contato)
        db.flush()

    envio = Envio(id=str(uuid.uuid4()), contato_id=contato.id, modelo_id=modelo_id, status="enviando")
    db.add(envio)
    db.commit()
    db.refresh(envio)

    # Telefone mascarado em log/auditoria (AC-16); nunca o número cheio.
    wamid = enviar_template(telefone, modelo.nome, modelo.idioma, payload.componentes)
    envio.wamid = wamid
    envio.status = "enviado"
    db.commit()
    db.refresh(envio)

    # Auditoria sem PII (§5.8 / AC-16-17): telefone mascarado, nunca o número cheio.
    registrar_auditoria(
        operacao="envio_teste",
        ator_email=usuario.email,
        alvo_tipo="envio",
        alvo_id=envio.id,
        metadados={"telefone": mascarar_telefone(telefone), "modelo": modelo.nome, "wamid": wamid},
    )
    return envio
