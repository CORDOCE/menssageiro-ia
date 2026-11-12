"""Upload de anexos PDF (spec 0024 / ADR 0016): `POST /anexos`, autenticado por sessão.

Guarda o PDF (bytea) até o disparo; o worker o sobe à Meta no envio. §6: valida mime + magic bytes +
tamanho e **nunca executa/parseia** o conteúdo — só o repassa. Lê no máximo `anexo_max_bytes + 1` do
corpo (não carrega arquivos gigantes).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth_deps import usuario_atual
from app.core.config import get_settings
from app.db.database import get_db
from app.models.anexo import Anexo
from app.schemas.anexo import AnexoRead

router = APIRouter(prefix="/anexos", tags=["anexos"], dependencies=[Depends(usuario_atual)])

_MAGIC_PDF = b"%PDF-"


@router.post("", status_code=201, response_model=AnexoRead)
async def enviar_anexo(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AnexoRead:
    """Recebe um PDF (boleto), valida e guarda. 401 sem sessão (dependência do router)."""
    cfg = get_settings()
    conteudo = await arquivo.read(cfg.anexo_max_bytes + 1)
    if len(conteudo) > cfg.anexo_max_bytes:
        raise HTTPException(status_code=422, detail="Arquivo acima do limite permitido")
    if arquivo.content_type != "application/pdf" or not conteudo.startswith(_MAGIC_PDF):
        raise HTTPException(status_code=422, detail="Apenas PDF é aceito")
    anexo = Anexo(
        id=str(uuid.uuid4()),
        nome_arquivo=(arquivo.filename or "boleto.pdf")[:255],
        mime="application/pdf",
        tamanho=len(conteudo),
        conteudo=conteudo,
    )
    db.add(anexo)
    db.commit()
    return AnexoRead(id=anexo.id, nome_arquivo=anexo.nome_arquivo, tamanho=anexo.tamanho)
