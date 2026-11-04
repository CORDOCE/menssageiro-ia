"""Router de agendamentos (spec 0004, tasks 5-6): CRUD mínimo protegido por sessão.

**§5.1:** a API só **registra** o agendamento; quem envia é o worker. A regra `contato_id` xor
`grupo` vive no schema (422). `cancelar`/`reenviar` são transições de status (409 em estado inválido).
Toda ação que muda estado gera auditoria (§5.8).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.core.auth_deps import usuario_atual
from app.db.database import get_db
from app.models.agendamento import Agendamento
from app.models.modelo import Modelo
from app.models.usuario import Usuario
from app.schemas.agendamento import AgendamentoCriar, AgendamentoRead
from app.services.recorrencia import validar_regra

router = APIRouter(
    prefix="/agendamentos", tags=["agendamentos"], dependencies=[Depends(usuario_atual)]
)

_STATUS_TERMINAIS = {"enviado", "cancelado"}


@router.post("", status_code=201, response_model=AgendamentoRead)
def criar(
    payload: AgendamentoCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> Agendamento:
    if db.get(Modelo, payload.modelo_id) is None:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    if payload.recorrencia is not None:
        try:
            validar_regra(payload.recorrencia)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail="recorrencia (RRULE) inválida") from exc
    ag = Agendamento(
        id=str(uuid.uuid4()),
        contato_id=payload.contato_id,
        grupo=payload.grupo,
        modelo_id=payload.modelo_id,
        variaveis=payload.variaveis,
        executar_em=payload.executar_em,
        origem=payload.origem,
        recorrencia=payload.recorrencia,
        criado_por=usuario.id,
    )
    db.add(ag)
    db.commit()
    db.refresh(ag)
    registrar_auditoria(
        "agendamento.criar", ator_email=usuario.email, alvo_tipo="agendamento", alvo_id=ag.id
    )
    return ag


@router.get("", response_model=list[AgendamentoRead])
def listar(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Agendamento]:
    filtros = []
    if status is not None:
        filtros.append(Agendamento.status == status)
    rows = db.execute(
        select(Agendamento).where(*filtros).order_by(Agendamento.executar_em).limit(limit).offset(offset)
    ).scalars().all()
    return list(rows)


def _buscar(db: Session, agendamento_id: str) -> Agendamento:
    ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return ag


@router.post("/{agendamento_id}/cancelar", response_model=AgendamentoRead)
def cancelar(
    agendamento_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> Agendamento:
    ag = _buscar(db, agendamento_id)
    if ag.status in _STATUS_TERMINAIS:
        raise HTTPException(status_code=409, detail=f"Agendamento em estado terminal ({ag.status})")
    ag.status = "cancelado"
    ag.motivo_ultima_transicao = "cancelado pelo operador"
    db.commit()
    db.refresh(ag)
    registrar_auditoria(
        "agendamento.cancelar", ator_email=usuario.email, alvo_tipo="agendamento", alvo_id=ag.id
    )
    return ag


@router.post("/{agendamento_id}/reenviar", response_model=AgendamentoRead)
def reenviar(
    agendamento_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> Agendamento:
    ag = _buscar(db, agendamento_id)
    if ag.status != "aguardando_decisao":
        raise HTTPException(
            status_code=409, detail="Só agendamentos em aguardando_decisao podem ser reenviados"
        )
    ag.status = "aprovado"
    ag.executar_em = datetime.now(UTC)
    ag.motivo_ultima_transicao = "reenviado pelo operador"
    db.commit()
    db.refresh(ag)
    registrar_auditoria(
        "agendamento.reenviar", ator_email=usuario.email, alvo_tipo="agendamento", alvo_id=ag.id
    )
    return ag


@router.post("/{agendamento_id}/cancelar-serie")
def cancelar_serie(
    agendamento_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> dict[str, int]:
    """Cancela as ocorrências **futuras pendentes** da série (spec 0005, AC-13).

    Aceita o id da raiz **ou** de qualquer ocorrência-filha. Só afeta `status='aprovado'` com
    `executar_em > agora`; as já enviadas ficam. Cancelar uma ocorrência isolada = `/cancelar` (0004).
    """
    ag = _buscar(db, agendamento_id)
    raiz = ag.agendamento_pai_id or ag.id
    agora = datetime.now(UTC)
    cancelados = len(
        db.execute(
            update(Agendamento)
            .where(
                or_(Agendamento.id == raiz, Agendamento.agendamento_pai_id == raiz),
                Agendamento.status == "aprovado",
                Agendamento.executar_em > agora,
            )
            .values(status="cancelado", motivo_ultima_transicao="série cancelada pelo operador")
            .returning(Agendamento.id)
        ).all()
    )
    db.commit()
    registrar_auditoria(
        "agendamento.cancelar_serie", ator_email=usuario.email, alvo_tipo="agendamento",
        alvo_id=raiz, metadados={"cancelados": cancelados},
    )
    return {"cancelados": cancelados}
