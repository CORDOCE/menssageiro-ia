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

# Reenvio automático (spec 0020 / ADR 0014): até 3 reenvios com backoff crescente curto.
_MAX_RETRY = 3
_BACKOFF_RETRY = {1: timedelta(minutes=5), 2: timedelta(minutes=15), 3: timedelta(hours=1)}

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
        limite_agendamento = cfg.limite_por_agendamento_dia

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
            _processar_agendamento(
                aid, agora, janela, limite_diario, limite_contato, limite_agendamento, enviar
            )
        except Exception as exc:  # um agendamento ruim não derruba o ciclo
            registrar_auditoria(
                "agendamento.erro_ciclo",
                alvo_tipo="agendamento",
                alvo_id=aid,
                status="error",
                metadados={"erro": type(exc).__name__},
                correlation_id=aid,
                alertar=True,
            )

    processar_reenvios(agora, limite_contato, enviar)  # spec 0020: retenta os aguardando_retry vencidos


def _destinatarios(sess: Session, ag: Agendamento) -> list[Contato]:
    if ag.contato_id is not None:
        c = sess.get(Contato, ag.contato_id)
        return [c] if c is not None else []
    # Ordem estável (Contato.id) para o corte do teto por-agendamento ser determinístico (ADR 0013).
    return list(
        sess.execute(
            select(Contato).where(Contato.grupo == ag.grupo).order_by(Contato.id)
        ).scalars().all()
    )


def _enviados_do_agendamento(sess: Session, aid: str) -> int:
    """Envios já reservados/entregues deste agendamento (teto por-agendamento, ADR 0013)."""
    return int(
        sess.execute(
            select(func.count())
            .select_from(Envio)
            .where(Envio.agendamento_id == aid, Envio.status.in_(_CONTAM_LIMITE))
        ).scalar_one()
    )


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
    limite_agendamento: int | None,
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
                metadados={"motivo": "modelo_nao_aprovado"}, correlation_id=ag.id, alertar=True,
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
        # Teto por-agendamento (ADR 0013): corta o excedente e marca `parcial` no fim.
        total_destinatarios = len(contatos)
        cortou = False
        if limite_agendamento is not None:
            restante = max(0, limite_agendamento - _enviados_do_agendamento(sess, aid))
            if total_destinatarios > restante:
                contatos = contatos[:restante]
                cortou = True
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

        if cortou:
            # Teto atingido (ADR 0013): para, marca `parcial` (terminal) e alerta — não espalha, não
            # cria próxima ocorrência (o operador investiga o corte antes de a série seguir).
            enviados = _enviados_do_agendamento(sess, aid)
            sess.execute(
                update(Agendamento)
                .where(Agendamento.id == aid)
                .values(
                    status="parcial",
                    motivo_ultima_transicao=(
                        f"teto por-agendamento atingido — {enviados} de {total_destinatarios}"
                    ),
                )
            )
            sess.commit()
            registrar_auditoria(
                "agendamento.limite_por_agendamento", alvo_tipo="agendamento", alvo_id=aid,
                status="warning",
                metadados={"enviados": enviados, "total": total_destinatarios, "teto": limite_agendamento},
                correlation_id=aid, alertar=True,
            )
            return

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


def _despachar_e_aplicar(
    sess: Session,
    envio_id: str,
    telefone: str,
    nome: str,
    idioma: str,
    componentes: list[dict[str, Any]],
    agora: datetime,
    tel: str,
    correlation_id: str,
    tentativas_atuais: int,
    enviar: Enviar,
) -> None:
    """Envia e aplica o desfecho na linha `envio_id`: sucesso → `enviado`+`wamid`; falha → roteia pela
    classe (`_aplicar_falha_envio`). Usado no 1º envio e no reenvio (spec 0020)."""
    try:
        wamid = enviar(telefone, nome, idioma, componentes)
        sess.execute(update(Envio).where(Envio.id == envio_id).values(status="enviado", wamid=wamid))
        sess.commit()
        registrar_auditoria(
            "envio.enviado", alvo_tipo="envio", alvo_id=envio_id,
            metadados={"telefone": tel}, correlation_id=correlation_id,
        )
    except WhatsappError as exc:
        _aplicar_falha_envio(sess, envio_id, exc, tentativas_atuais, agora, tel, correlation_id)


def _aplicar_falha_envio(
    sess: Session,
    envio_id: str,
    exc: WhatsappError,
    tentativas_atuais: int,
    agora: datetime,
    tel: str,
    correlation_id: str,
) -> None:
    """Roteia a falha de um envio pela **classe** e tentativas (ADR 0014): retentável<3 agenda reenvio;
    retentável esgotado e ambíguo → decisão humana; definitivo → falhou. Grava status + auditoria."""
    if exc.classe == "retentavel" and tentativas_atuais < _MAX_RETRY:
        nova = tentativas_atuais + 1
        sess.execute(
            update(Envio)
            .where(Envio.id == envio_id)
            .values(
                status="aguardando_retry",
                tentativas=nova,
                proxima_tentativa_em=agora + _BACKOFF_RETRY[nova],
                erro_codigo=str(exc.codigo),
                erro_motivo=exc.motivo,
            )
        )
        sess.commit()
        registrar_auditoria(
            "envio.retry_agendado", alvo_tipo="envio", alvo_id=envio_id, status="warning",
            metadados={"telefone": tel, "codigo": str(exc.codigo), "tentativa": nova},
            correlation_id=correlation_id,
        )
        return

    if exc.classe == "definitivo":
        status, operacao, nivel = "falhou", "envio.falhou", "error"
    elif exc.classe == "retentavel":  # tentativas == _MAX_RETRY → esgotou
        status, operacao, nivel = "aguardando_decisao", "envio.retry_esgotado", "warning"
    else:  # ambiguo
        status, operacao, nivel = "aguardando_decisao", "envio.falha_ambigua", "warning"
    sess.execute(
        update(Envio)
        .where(Envio.id == envio_id)
        .values(status=status, erro_codigo=str(exc.codigo), erro_motivo=exc.motivo)
    )
    sess.commit()
    registrar_auditoria(
        operacao, alvo_tipo="envio", alvo_id=envio_id, status=nivel,
        metadados={"telefone": tel, "codigo": str(exc.codigo)}, correlation_id=correlation_id, alertar=True,
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
    _despachar_e_aplicar(
        sess, reservado, contato.telefone_e164, nome, idioma, componentes,
        agora, tel, aid, tentativas_atuais=0, enviar=enviar,
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


def processar_reenvios(agora: datetime, limite_contato: int | None, enviar: Enviar) -> None:
    """Passo de reenvio (spec 0020 / ADR 0014): retenta os envios `aguardando_retry` vencidos. Cada envio é
    travado com `FOR UPDATE SKIP LOCKED`; a elegibilidade do contato é reavaliada antes de cada tentativa."""
    ctrl = _db.SessionLocal()
    try:
        ids = list(
            ctrl.execute(
                select(Envio.id)
                .where(Envio.status == "aguardando_retry", Envio.proxima_tentativa_em <= agora)
                .order_by(Envio.proxima_tentativa_em)
                .limit(_LOTE)
            ).scalars().all()
        )
    finally:
        ctrl.close()
    for envio_id in ids:
        try:
            _reenviar_um(envio_id, agora, limite_contato, enviar)
        except Exception:  # um reenvio ruim não derruba o passo
            registrar_auditoria(
                "envio.erro_reenvio", alvo_tipo="envio", alvo_id=envio_id, status="error", alertar=True
            )


def _reenviar_um(envio_id: str, agora: datetime, limite_contato: int | None, enviar: Enviar) -> None:
    sess = _db.SessionLocal()
    try:
        envio = sess.execute(
            select(Envio)
            .where(
                Envio.id == envio_id,
                Envio.status == "aguardando_retry",
                Envio.proxima_tentativa_em <= agora,
            )
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if envio is None:  # outro worker já pegou, ou o status mudou
            return
        contato = sess.get(Contato, envio.contato_id)
        ag = sess.get(Agendamento, envio.agendamento_id) if envio.agendamento_id else None
        modelo = sess.get(Modelo, envio.modelo_id) if envio.modelo_id else None
        if contato is None or ag is None or modelo is None:
            return  # dados insuficientes (envio avulso) — não reenvia
        aid = ag.id
        tel = mascarar_telefone(contato.telefone_e164)
        motivo = _motivo_inelegivel(sess, contato, agora, limite_contato)
        if motivo is not None:  # descadastro/consentimento/limite mudou desde a 1ª tentativa (§5.4)
            sess.execute(
                update(Envio)
                .where(Envio.id == envio_id)
                .values(status="falhou", erro_motivo=f"inelegível no reenvio: {motivo}")
            )
            sess.commit()
            registrar_auditoria(
                "envio.reenvio_inelegivel", alvo_tipo="envio", alvo_id=envio_id, status="warning",
                metadados={"telefone": tel, "motivo": motivo}, correlation_id=aid, alertar=True,
            )
            return
        variaveis = list(ag.variaveis)
        componentes: list[dict[str, Any]] = (
            [{"type": "body", "parameters": [{"type": "text", "text": v} for v in variaveis]}]
            if variaveis
            else []
        )
        _despachar_e_aplicar(
            sess, envio_id, contato.telefone_e164, modelo.nome, modelo.idioma, componentes,
            agora, tel, aid, tentativas_atuais=envio.tentativas, enviar=enviar,
        )
    finally:
        sess.close()
