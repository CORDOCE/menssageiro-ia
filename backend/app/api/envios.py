"""Router de envios (spec 0014): histórico read-only protegido por sessão.

Lista os envios realizados para auditoria (§5.8), com join de contato (nome/telefone) e modelo
(nome; outer join — envios avulsos têm `modelo_id` nulo), filtros de status/período e paginação.
Só leitura: nenhum caminho aqui envia nada.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.core.auth_deps import usuario_atual
from app.db.database import get_db
from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo
from app.models.usuario import Usuario
from app.schemas.envio import EnvioRead, StatusEnvio

router = APIRouter(prefix="/envios", tags=["envios"], dependencies=[Depends(usuario_atual)])


@router.get("", response_model=list[EnvioRead])
def listar(
    db: Session = Depends(get_db),
    status: StatusEnvio | None = Query(default=None),
    desde: datetime | None = Query(default=None),
    ate: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[EnvioRead]:
    stmt = (
        select(Envio, Contato.nome, Contato.telefone_e164, Modelo.nome)
        .join(Contato, Envio.contato_id == Contato.id)
        .outerjoin(Modelo, Envio.modelo_id == Modelo.id)
    )
    if status is not None:
        stmt = stmt.where(Envio.status == status.value)
    if desde is not None:
        stmt = stmt.where(Envio.criado_em >= desde)
    if ate is not None:
        stmt = stmt.where(Envio.criado_em <= ate)
    stmt = stmt.order_by(Envio.criado_em.desc()).limit(limit).offset(offset)
    rows = db.execute(stmt).all()
    return [
        EnvioRead(
            id=e.id,
            contato_id=e.contato_id,
            contato_nome=contato_nome,
            contato_telefone=contato_telefone,
            modelo_id=e.modelo_id,
            modelo_nome=modelo_nome,
            status=e.status,
            erro_codigo=e.erro_codigo,
            erro_motivo=e.erro_motivo,
            criado_em=e.criado_em,
        )
        for e, contato_nome, contato_telefone, modelo_nome in rows
    ]


@router.post("/{envio_id}/reenviar", response_model=EnvioRead)
def reenviar(
    envio_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> EnvioRead:
    """Reenvio manual (spec 0020 / ADR 0014): reabre um envio em `aguardando_decisao` para nova tentativa
    automática (zera o contador). 409 em qualquer outro estado; 401 sem sessão (dependência do router)."""
    envio = db.get(Envio, envio_id)
    if envio is None:
        raise HTTPException(status_code=404, detail="Envio não encontrado")
    if envio.status != "aguardando_decisao":
        raise HTTPException(
            status_code=409, detail="Só envios em aguardando_decisao podem ser reenviados"
        )
    envio.status = "aguardando_retry"
    envio.tentativas = 0
    envio.proxima_tentativa_em = datetime.now(UTC)
    db.commit()
    db.refresh(envio)
    registrar_auditoria(
        "envio.reenvio_manual", ator_email=usuario.email, alvo_tipo="envio", alvo_id=envio_id
    )
    contato = db.get(Contato, envio.contato_id)
    modelo = db.get(Modelo, envio.modelo_id) if envio.modelo_id else None
    return EnvioRead(
        id=envio.id,
        contato_id=envio.contato_id,
        contato_nome=contato.nome if contato else "",
        contato_telefone=contato.telefone_e164 if contato else "",
        modelo_id=envio.modelo_id,
        modelo_nome=modelo.nome if modelo else None,
        status=envio.status,
        erro_codigo=envio.erro_codigo,
        erro_motivo=envio.erro_motivo,
        criado_em=envio.criado_em,
    )
