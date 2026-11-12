"""Web Push (spec 0023 / ADR 0015): chave pública VAPID + inscrição do dispositivo. Autenticado por sessão.

Só leitura/inscrição; o envio de notificações é interno (service `push.enviar_push`, disparado pelos
alertas §12). Protegido por sessão (dependência do router).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth_deps import usuario_atual
from app.db.database import get_db
from app.schemas.push import ChavePublica, InscricaoEntrada
from app.services.push import chave_publica, inscrever

router = APIRouter(prefix="/push", tags=["push"], dependencies=[Depends(usuario_atual)])


@router.get("/chave-publica", response_model=ChavePublica)
def obter_chave_publica() -> ChavePublica:
    """Chave pública VAPID para o browser inscrever (null se não configurada → UI degrada)."""
    return ChavePublica(chave=chave_publica())


@router.post("/inscrever", status_code=201)
def inscrever_dispositivo(
    dados: InscricaoEntrada, db: Session = Depends(get_db)
) -> dict[str, str]:
    """Registra (upsert por endpoint) a inscrição de Web Push do dispositivo atual."""
    inscrever(db, dados.endpoint, dados.keys.p256dh, dados.keys.auth)
    return {"status": "inscrito"}
