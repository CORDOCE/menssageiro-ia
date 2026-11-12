"""Router de modelos (spec 0003, task 11).

Expõe o envio de **teste** (`POST /modelos/{id}/enviar-teste`), protegido por sessão e **restrito ao
número de teste** (§4: nunca número real). Cria um `envio` avulso (sem agendamento) e chama o cliente
WhatsApp. O caminho de produção (disparo em escala) é do worker, na Fase 4.
"""

from __future__ import annotations

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
from app.services.modelos_sync import SincronizarResultado, sincronizar_modelos
from app.services.whatsapp_client import enviar_template, listar_templates

router = APIRouter(prefix="/modelos", tags=["modelos"])

# Status possíveis do template (espelham a Meta; ver models/modelo.py).
StatusModelo = Literal["rascunho", "pendente", "aprovado", "rejeitado", "pausado"]

@router.post("/sincronizar", response_model=SincronizarResultado)
def sincronizar(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> SincronizarResultado:
    """Lê os templates da Meta (Cloud API, só leitura) e delega o upsert ao service compartilhado
    (spec 0022). A Meta é a fonte da verdade do status/categoria (§5.3). Protegido por sessão (spec 0010)."""
    templates = listar_templates()
    return sincronizar_modelos(db, templates, ator_email=usuario.email)


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
