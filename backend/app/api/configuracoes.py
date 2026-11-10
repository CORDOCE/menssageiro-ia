"""Router de configuração de envio (spec 0018): GET/PATCH da linha única.

Expõe os controles que o worker lê **a cada ciclo** (ADR 0008): janela, limites e pausa.
`PATCH` é parcial (só os campos presentes mudam) e toda alteração gera auditoria (§5.8).
A validação de domínio vive no schema (vira 422); aqui nada é enviado (§5.7).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.audit import registrar_auditoria
from app.core.auth_deps import usuario_atual
from app.db.database import get_db
from app.models.configuracao import ID_CONFIG, Configuracao
from app.models.usuario import Usuario
from app.schemas.configuracao import ConfiguracaoPatch, ConfiguracaoRead
from app.services.janela import obter_configuracao

router = APIRouter(
    prefix="/configuracoes", tags=["configuracoes"], dependencies=[Depends(usuario_atual)]
)


@router.get("", response_model=ConfiguracaoRead)
def obter(db: Session = Depends(get_db)) -> Configuracao:
    return obter_configuracao(db)


@router.patch("", response_model=ConfiguracaoRead)
def atualizar(
    patch: ConfiguracaoPatch,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
) -> Configuracao:
    config = obter_configuracao(db)
    # exclude_unset: só os campos presentes no corpo entram; `null` nos opcionais remove o limite.
    dados = patch.model_dump(exclude_unset=True)
    # Diff real: aplica e audita apenas o que de fato muda (AC-8). No-op não gera auditoria.
    alteracoes = {campo: valor for campo, valor in dados.items() if getattr(config, campo) != valor}
    if not alteracoes:
        return config
    for campo, valor in alteracoes.items():
        setattr(config, campo, valor)
    db.commit()
    db.refresh(config)
    # Auditoria da mudança de estado (§5.8/§7). Config não tem PII; registra campos e novos valores.
    registrar_auditoria(
        "configuracao.atualizada",
        ator_email=usuario.email,
        alvo_tipo="configuracao",
        alvo_id=ID_CONFIG,
        metadados={"alteracoes": alteracoes},
    )
    return config
