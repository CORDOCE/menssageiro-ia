"""Router de contatos (spec 0002, task 4): CRUD protegido por sessão (`usuario_atual`).

Dedup pelo `telefone_e164` canônico: criar telefone já existente → 409; PATCH que colide com
outro contato → 409. Normalização e validação de telefone ficam nos schemas.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth_deps import usuario_atual
from app.core.config import get_settings
from app.db.database import get_db
from app.models.contato import Contato
from app.models.usuario import Usuario
from app.schemas.contato import (
    ContatoCreate,
    ContatoLista,
    ContatoRead,
    ContatoUpdate,
    RegistrarConsentimento,
    RelatorioImportacao,
)
from app.services.contatos_import import ImportacaoError, importar

router = APIRouter(prefix="/contatos", tags=["contatos"], dependencies=[Depends(usuario_atual)])


@router.post("", status_code=201, response_model=ContatoRead)
def criar(payload: ContatoCreate, db: Session = Depends(get_db)) -> Contato:
    existe = db.execute(
        select(Contato).where(Contato.telefone_e164 == payload.telefone)
    ).scalar_one_or_none()
    if existe is not None:
        raise HTTPException(status_code=409, detail="Telefone já cadastrado")
    contato = Contato(
        id=str(uuid.uuid4()),
        nome=payload.nome,
        telefone_e164=payload.telefone,
        grupo=payload.grupo,
        tags=payload.tags,
        observacoes=payload.observacoes,
    )
    db.add(contato)
    db.commit()
    db.refresh(contato)
    return contato


@router.get("", response_model=ContatoLista)
def listar(
    db: Session = Depends(get_db),
    grupo: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ContatoLista:
    filtros = []
    if grupo is not None:
        filtros.append(Contato.grupo == grupo)
    if tag is not None:
        filtros.append(Contato.tags.contains([tag]))  # JSONB @> (contém a tag)
    if status == "ativo":
        filtros.append(Contato.descadastrado_em.is_(None))
    elif status == "descadastrado":
        filtros.append(Contato.descadastrado_em.is_not(None))

    total = db.execute(select(func.count()).select_from(Contato).where(*filtros)).scalar_one()
    rows = (
        db.execute(
            select(Contato).where(*filtros).order_by(Contato.criado_em).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    items = [ContatoRead.model_validate(c) for c in rows]
    return ContatoLista(items=items, total=total, limit=limit, offset=offset)


@router.post("/importar", response_model=RelatorioImportacao)
async def importar_contatos(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> RelatorioImportacao:
    """Importa contatos de CSV/XLSX (multipart). Limites configuráveis (AC-17):
    acima do tamanho → 413; acima do nº de linhas ou arquivo inválido → 422. Nada persiste."""
    cfg = get_settings()
    # Lê no máximo o limite + 1 byte: evita carregar um upload gigante inteiro na memória.
    conteudo = await arquivo.read(cfg.import_max_bytes + 1)
    if len(conteudo) > cfg.import_max_bytes:
        raise HTTPException(status_code=413, detail="arquivo acima do limite de tamanho")
    try:
        return importar(
            conteudo, arquivo.filename or "", db,
            max_linhas=cfg.import_max_linhas, ator_email=usuario.email,
        )
    except ImportacaoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{contato_id}", response_model=ContatoRead)
def obter(contato_id: str, db: Session = Depends(get_db)) -> Contato:
    contato = db.get(Contato, contato_id)
    if contato is None:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    return contato


@router.patch("/{contato_id}", response_model=ContatoRead)
def atualizar(contato_id: str, payload: ContatoUpdate, db: Session = Depends(get_db)) -> Contato:
    contato = db.get(Contato, contato_id)
    if contato is None:
        raise HTTPException(status_code=404, detail="Contato não encontrado")

    dados = payload.model_dump(exclude_unset=True)
    novo_telefone = dados.pop("telefone", None)
    if novo_telefone is not None and novo_telefone != contato.telefone_e164:
        colisao = db.execute(
            select(Contato).where(Contato.telefone_e164 == novo_telefone, Contato.id != contato_id)
        ).scalar_one_or_none()
        if colisao is not None:
            raise HTTPException(status_code=409, detail="Telefone já cadastrado")
        contato.telefone_e164 = novo_telefone

    for campo, valor in dados.items():
        setattr(contato, campo, valor)
    db.commit()
    db.refresh(contato)
    return contato


@router.post("/{contato_id}/descadastrar", response_model=ContatoRead)
def descadastrar(contato_id: str, db: Session = Depends(get_db)) -> Contato:
    """Descadastro soft e imediato (§5.4): marca `descadastrado_em`; o contato permanece.

    Idempotente — não sobrescreve a data de um descadastro anterior.
    """
    contato = db.get(Contato, contato_id)
    if contato is None:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    if contato.descadastrado_em is None:
        contato.descadastrado_em = datetime.now(UTC)
        db.commit()
        db.refresh(contato)
    return contato


@router.post("/{contato_id}/consentimento", response_model=ContatoRead)
def registrar_consentimento(
    contato_id: str, payload: RegistrarConsentimento, db: Session = Depends(get_db)
) -> Contato:
    """Registra opt-in deliberado (§5.9): consentimento=true com origem e data."""
    contato = db.get(Contato, contato_id)
    if contato is None:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    contato.consentimento = True
    contato.consentimento_origem = payload.origem
    contato.consentimento_data = datetime(
        payload.data.year, payload.data.month, payload.data.day, tzinfo=UTC
    )
    db.commit()
    db.refresh(contato)
    return contato
