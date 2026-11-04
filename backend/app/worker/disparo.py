"""Worker de disparo (spec 0004, tasks 8-10; ADR 0005/0008).

Um passo (`processar_ciclo`) por ciclo do worker:
1. Lê a configuração (pausa/janela/limite). Pausado → não dispara.
2. **`aguardando_decisao`**: gap de heartbeat + item >2 h atrasado → move pra lá (não dispara).
3. Seleciona vencidos (`aprovado`/`enviando`) com **`FOR UPDATE SKIP LOCKED`** (um por transação).
4. Por agendamento: fora da janela → **reagenda**; modelo não aprovado → **falhou**; limite → **adia**.
5. Expande o grupo e, **por contato** (descadastro/consentimento/limite), **reserva o envio antes de
   enviar** (`INSERT … ON CONFLICT DO NOTHING` em `(agendamento_id, contato_id)` = idempotência, §5.2).

O "claim" (marcar `enviando`) é **commitado e libera o `FOR UPDATE`** antes de inserir envios — necessário
porque `envios.agendamento_id` é FK (o INSERT pega um lock na linha do agendamento). O agendamento só vira
`enviado` no fim; crash o deixa `enviando` e o próximo ciclo recompleta (ON CONFLICT pula os já reservados).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

import app.db.database as _db
from app.core.audit import registrar_auditoria
from app.core.config import get_settings
from app.core.telefone import mascarar_telefone
from app.models.agendamento import Agendamento
from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo
from app.services.janela import (
    dentro_da_janela,
    inicio_dia_seguinte,
    obter_configuracao,
    proximo_inicio,
)
from app.services.recorrencia import proxima_ocorrencia
from app.services.whatsapp_client import WhatsappError, enviar_template

_LOTE = 100
# Status que contam para os limites (reservados ou entregues; não conta falhou/criado).
_CONTAM_LIMITE = ("enviando", "enviado", "entregue", "lido")
_ATIVOS = ("aprovado", "enviando")

Enviar = Callable[..., str]


def processar_ciclo(
    *,
    enviar: Enviar = enviar_template,
    agora: datetime | None = None,
    heartbeat_anterior: datetime | None = None,
    intervalo_s: int | None = None,
) -> None:
    agora = agora or datetime.now(UTC)
    intervalo = intervalo_s if intervalo_s is not None else get_settings().worker_intervalo_s

    ctrl = _db.SessionLocal()
    try:
        cfg = obter_configuracao(ctrl)
        janela = dict(cfg.janela_envio)
        pausado = cfg.envios_pausados
        limite_diario = cfg.limite_diario
        limite_contato = cfg.limite_por_contato_dia

        if heartbeat_anterior is not None and (agora - heartbeat_anterior).total_seconds() > 2 * intervalo:
            ctrl.execute(
                update(Agendamento)
                .where(
                    Agendamento.status.in_(_ATIVOS),
                    Agendamento.executar_em < agora - timedelta(hours=2),
                )
                .values(
                    status="aguardando_decisao",
                    motivo_ultima_transicao="indisponibilidade (gap de heartbeat) + atraso >2h",
                )
            )
            ctrl.commit()

        if pausado:
            return

        ids = (
            ctrl.execute(
                select(Agendamento.id)
                .where(Agendamento.status.in_(_ATIVOS), Agendamento.executar_em <= agora)
                .order_by(Agendamento.executar_em)
                .limit(_LOTE)
            )
            .scalars()
            .all()
        )
    finally:
        ctrl.close()

    for aid in ids:
        try:
            _processar_agendamento(aid, agora, janela, limite_diario, limite_contato, enviar)
        except Exception as exc:  # um agendamento ruim não derruba o ciclo
            registrar_auditoria(
                "agendamento.erro_ciclo",
                alvo_tipo="agendamento",
                alvo_id=aid,
                status="error",
                metadados={"erro": type(exc).__name__},
                correlation_id=aid,
            )


def _destinatarios(sess: Session, ag: Agendamento) -> list[Contato]:
    if ag.contato_id is not None:
        c = sess.get(Contato, ag.contato_id)
        return [c] if c is not None else []
    return list(sess.execute(select(Contato).where(Contato.grupo == ag.grupo)).scalars().all())


def _enviados_em_24h(sess: Session, agora: datetime, contato_id: str | None = None) -> int:
    filtros = [Envio.status.in_(_CONTAM_LIMITE), Envio.criado_em >= agora - timedelta(hours=24)]
    if contato_id is not None:
        filtros.append(Envio.contato_id == contato_id)
    return int(sess.execute(select(func.count()).select_from(Envio).where(*filtros)).scalar_one())


def _processar_agendamento(
    aid: str,
    agora: datetime,
    janela: dict[str, Any],
    limite_diario: int,
    limite_contato: int | None,
    enviar: Enviar,
) -> None:
    sess = _db.SessionLocal()
    try:
        # Claim: trava o agendamento (SKIP LOCKED); aplica as decisões de nível agendamento.
        ag = sess.execute(
            select(Agendamento)
            .where(
                Agendamento.id == aid,
                Agendamento.status.in_(_ATIVOS),
                Agendamento.executar_em <= agora,
            )
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if ag is None:  # já tratado, travado por outro worker, ou mudou de status
            return

        if not dentro_da_janela(agora, janela):
            ag.status = "aprovado"
            ag.executar_em = proximo_inicio(agora, janela)
            ag.reagendamentos += 1
            ag.motivo_ultima_transicao = "fora da janela de horário — reagendado"
            sess.commit()
            return

        modelo = sess.get(Modelo, ag.modelo_id)
        if modelo is None or modelo.status != "aprovado":
            ag.status = "falhou"
            ag.motivo_ultima_transicao = "modelo não aprovado"
            sess.commit()
            registrar_auditoria(
                "agendamento.falhou", alvo_tipo="agendamento", alvo_id=ag.id, status="error",
                metadados={"motivo": "modelo_nao_aprovado"}, correlation_id=ag.id,
            )
            return

        if _enviados_em_24h(sess, agora) >= limite_diario:
            ag.status = "aprovado"
            ag.executar_em = inicio_dia_seguinte(agora, janela)
            ag.motivo_ultima_transicao = "limite diário atingido — adiado"
            sess.commit()
            return

        nome, idioma, modelo_id, variaveis = modelo.nome, modelo.idioma, ag.modelo_id, list(ag.variaveis)
        # Campos para encadear a próxima ocorrência (capturados antes do commit que expira `ag`).
        recorrencia, pai_id, executar_em = ag.recorrencia, ag.agendamento_pai_id, ag.executar_em
        contato_id, grupo, origem = ag.contato_id, ag.grupo, ag.origem
        contatos = _destinatarios(sess, ag)
        ag.status = "enviando"
        sess.commit()  # libera o FOR UPDATE antes de inserir envios (FK envios→agendamentos)

        componentes: list[dict[str, Any]] = (
            [{"type": "body", "parameters": [{"type": "text", "text": v} for v in variaveis]}]
            if variaveis
            else []
        )
        for contato in contatos:
            _processar_contato(
                sess, aid, modelo_id, nome, idioma, componentes, contato, agora, limite_contato, enviar
            )

        # Recorrência (spec 0005, ADR 0005/0009): cria a próxima ocorrência (lazy) junto de marcar
        # `enviado`, no mesmo commit (atômico). ON CONFLICT torna o reprocesso idempotente (§5.2).
        if recorrencia is not None:
            _criar_proxima_ocorrencia(
                sess, aid=aid, pai_id=pai_id, executar_em=executar_em, recorrencia=recorrencia,
                contato_id=contato_id, grupo=grupo, modelo_id=modelo_id, variaveis=variaveis, origem=origem,
            )
        sess.execute(
            update(Agendamento)
            .where(Agendamento.id == aid)
            .values(status="enviado", motivo_ultima_transicao=None)
        )
        sess.commit()
    finally:
        sess.close()


def _criar_proxima_ocorrencia(
    sess: Session,
    *,
    aid: str,
    pai_id: str | None,
    executar_em: datetime,
    recorrencia: str,
    contato_id: str | None,
    grupo: str | None,
    modelo_id: str,
    variaveis: list[str],
    origem: str,
) -> None:
    """Insere a próxima ocorrência da série, ou nada se a regra esgotou. Idempotente (ON CONFLICT)."""
    raiz = pai_id or aid
    dtstart = (
        executar_em
        if pai_id is None
        else sess.execute(
            select(Agendamento.executar_em).where(Agendamento.id == raiz)
        ).scalar_one()
    )
    proxima = proxima_ocorrencia(recorrencia, dtstart, executar_em)
    if proxima is None:
        return
    novo_id = str(uuid.uuid4())
    criado = sess.execute(
        pg_insert(Agendamento)
        .values(
            id=novo_id, modelo_id=modelo_id, contato_id=contato_id, grupo=grupo,
            variaveis=variaveis, executar_em=proxima, status="aprovado", origem=origem,
            agendamento_pai_id=raiz, recorrencia=recorrencia,
        )
        .on_conflict_do_nothing(
            index_elements=["agendamento_pai_id", "executar_em"],
            index_where=text("agendamento_pai_id IS NOT NULL"),
        )
        .returning(Agendamento.id)
    ).scalar_one_or_none()
    # Audita só quando a linha foi de fato criada (ON CONFLICT → None → reprocesso não re-audita); §5.8.
    if criado is not None:
        registrar_auditoria(
            "agendamento.ocorrencia_criada", alvo_tipo="agendamento", alvo_id=novo_id,
            metadados={"serie": raiz, "executar_em": proxima.isoformat()}, correlation_id=raiz,
        )


def _processar_contato(
    sess: Session,
    aid: str,
    modelo_id: str,
    nome: str,
    idioma: str,
    componentes: list[dict[str, Any]],
    contato: Contato,
    agora: datetime,
    limite_contato: int | None,
    enviar: Enviar,
) -> None:
    motivo = _motivo_inelegivel(sess, contato, agora, limite_contato)
    if motivo is not None:
        registrar_auditoria(
            "envio.pulado", alvo_tipo="contato", alvo_id=contato.id, status="skipped",
            metadados={"motivo": motivo}, correlation_id=aid,
        )
        return

    # Reserva antes de enviar (idempotente/race-safe): ON CONFLICT no índice único parcial.
    reservado = sess.execute(
        pg_insert(Envio)
        .values(
            id=str(uuid.uuid4()), agendamento_id=aid, contato_id=contato.id,
            modelo_id=modelo_id, status="enviando",
        )
        .on_conflict_do_nothing(
            index_elements=["agendamento_id", "contato_id"],
            index_where=text("agendamento_id IS NOT NULL"),
        )
        .returning(Envio.id)
    ).scalar_one_or_none()
    sess.commit()
    if reservado is None:  # já reservado (reinício) → não reenvia (§5.2)
        return

    tel = mascarar_telefone(contato.telefone_e164)
    try:
        wamid = enviar(contato.telefone_e164, nome, idioma, componentes)
        sess.execute(update(Envio).where(Envio.id == reservado).values(status="enviado", wamid=wamid))
        sess.commit()
        registrar_auditoria(
            "envio.enviado", alvo_tipo="envio", alvo_id=reservado,
            metadados={"telefone": tel}, correlation_id=aid,
        )
    except WhatsappError as exc:
        sess.execute(
            update(Envio).where(Envio.id == reservado).values(
                status="falhou", erro_codigo=str(exc.codigo), erro_motivo=exc.motivo
            )
        )
        sess.commit()
        registrar_auditoria(
            "envio.falhou", alvo_tipo="envio", alvo_id=reservado, status="error",
            metadados={"telefone": tel, "codigo": str(exc.codigo)}, correlation_id=aid,
        )


def _motivo_inelegivel(
    sess: Session, contato: Contato, agora: datetime, limite_contato: int | None
) -> str | None:
    if contato.descadastrado_em is not None:
        return "descadastrado"
    if not contato.consentimento:
        return "sem_consentimento"
    if limite_contato is not None and _enviados_em_24h(sess, agora, contato.id) >= limite_contato:
        return "limite_por_contato"
    return None
