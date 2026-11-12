"""Worker de disparo (spec 0004, AC-8..AC-22): núcleo do envio com PostgreSQL real e mock da Meta.

`AGORA` = terça 2026-11-03 10:00 em America/Sao_Paulo (= 13:00 UTC), dentro da janela padrão.
`AGORA_FORA` = domingo 2026-11-08 12:00 SP, fora da janela.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.agendamento import Agendamento
from app.models.auditoria import Auditoria
from app.models.configuracao import ID_CONFIG, Configuracao
from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo
from app.services.whatsapp_client import WhatsappError
from app.worker.disparo import processar_ciclo, processar_reenvios, varrer_orfaos

AGORA = datetime(2026, 11, 3, 13, 0, tzinfo=UTC)
AGORA_FORA = datetime(2026, 11, 8, 15, 0, tzinfo=UTC)


class FakeEnviar:
    def __init__(self, erro: Exception | None = None) -> None:
        self.chamadas: list[str] = []
        self.erro = erro

    def __call__(self, telefone: str, nome: str, idioma: str, componentes: list) -> str:
        self.chamadas.append(telefone)
        if self.erro is not None:
            raise self.erro
        return f"wamid.{uuid.uuid4().hex[:8]}"


def _config(db, **kw) -> None:
    cfg = db.get(Configuracao, ID_CONFIG) or Configuracao(id=ID_CONFIG)
    for k, v in kw.items():
        setattr(cfg, k, v)
    db.add(cfg)
    db.commit()


def _modelo(db, status: str = "aprovado") -> str:
    mid = str(uuid.uuid4())
    db.add(Modelo(id=mid, nome=f"t_{mid[:8]}", corpo="oi", status=status))
    db.commit()
    return mid


def _contato(db, *, consentimento=True, descadastrado=False, grupo=None) -> str:
    cid = str(uuid.uuid4())
    db.add(
        Contato(
            id=cid, nome="C", telefone_e164=f"+5531{uuid.uuid4().int % 100000000:08d}",
            consentimento=consentimento, grupo=grupo,
            descadastrado_em=datetime.now(UTC) if descadastrado else None,
        )
    )
    db.commit()
    return cid


def _agendamento(db, modelo_id, *, contato_id=None, grupo=None, executar_em=None,
                 status="aprovado", variaveis=None, recorrencia=None,
                 agendamento_pai_id=None) -> str:
    aid = str(uuid.uuid4())
    db.add(
        Agendamento(
            id=aid, modelo_id=modelo_id, contato_id=contato_id, grupo=grupo,
            executar_em=executar_em or (AGORA - timedelta(minutes=1)),
            status=status, variaveis=variaveis or [],
            recorrencia=recorrencia, agendamento_pai_id=agendamento_pai_id,
        )
    )
    db.commit()
    return aid


def _envio_feito(db, contato_id, *, agendamento_id=None) -> None:
    db.add(
        Envio(id=str(uuid.uuid4()), contato_id=contato_id, agendamento_id=agendamento_id,
              status="enviado", wamid=f"w.{uuid.uuid4().hex[:6]}")
    )
    db.commit()


def test_ac8_envio_unico_para_contato(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid, variaveis=["x"])
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    envios = db.query(Envio).filter(Envio.agendamento_id == aid).all()
    assert len(fake.chamadas) == 1
    assert len(envios) == 1 and envios[0].status == "enviado" and envios[0].wamid
    assert db.get(Agendamento, aid).status == "enviado"


def test_ac9_grupo_expande_em_n_envios(db):
    mid = _modelo(db)
    for _ in range(3):
        _contato(db, grupo="clientes")
    aid = _agendamento(db, mid, grupo="clientes")
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    assert db.query(Envio).filter(Envio.agendamento_id == aid).count() == 3
    assert len(fake.chamadas) == 3


def test_ac10_idempotencia_apos_reinicio(db):
    mid = _modelo(db)
    cids = [_contato(db, grupo="g") for _ in range(3)]
    aid = _agendamento(db, mid, grupo="g")
    _envio_feito(db, cids[0], agendamento_id=aid)  # lote interrompido: 1 já enviado
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    assert len(fake.chamadas) == 2  # só os 2 restantes
    assert db.query(Envio).filter(Envio.agendamento_id == aid).count() == 3


def test_ac11_pausa_nao_dispara(db):
    _config(db, envios_pausados=True)
    mid, cid = _modelo(db), _contato(db)
    _agendamento(db, mid, contato_id=cid)
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    assert len(fake.chamadas) == 0 and db.query(Envio).count() == 0


def test_ac12_fora_da_janela_reagenda(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid, executar_em=AGORA_FORA - timedelta(minutes=1))
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA_FORA)
    db.expire_all()
    ag = db.get(Agendamento, aid)
    assert ag.status == "aprovado" and ag.reagendamentos == 1 and ag.executar_em > AGORA_FORA
    assert len(fake.chamadas) == 0


def test_ac13_limite_diario_adia(db):
    _config(db, limite_diario=1)
    mid = _modelo(db)
    _envio_feito(db, _contato(db))  # 1 envio já conta p/ o limite
    aid = _agendamento(db, mid, contato_id=_contato(db))
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    ag = db.get(Agendamento, aid)
    assert ag.status == "aprovado" and ag.executar_em > AGORA and len(fake.chamadas) == 0


def test_ac14_modelo_nao_aprovado_falha(db):
    mid = _modelo(db, status="pendente")
    aid = _agendamento(db, mid, contato_id=_contato(db))
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    assert db.get(Agendamento, aid).status == "falhou" and len(fake.chamadas) == 0


def test_ac15_16_inelegiveis_nao_recebem(db):
    mid = _modelo(db)
    ok = _contato(db, grupo="g")
    _contato(db, grupo="g", descadastrado=True)
    _contato(db, grupo="g", consentimento=False)
    aid = _agendamento(db, mid, grupo="g")
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    envios = db.query(Envio).filter(Envio.agendamento_id == aid).all()
    assert len(envios) == 1 and envios[0].contato_id == ok and len(fake.chamadas) == 1


def test_ac17_limite_por_contato_pula(db):
    _config(db, limite_por_contato_dia=1)
    mid, cid = _modelo(db), _contato(db)
    _envio_feito(db, cid)  # contato já atingiu 1 hoje
    aid = _agendamento(db, mid, contato_id=cid)
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    assert db.query(Envio).filter(Envio.agendamento_id == aid).count() == 0
    assert len(fake.chamadas) == 0


def test_ac18_aguardando_decisao_com_gap(db):
    mid = _modelo(db)
    aid = _agendamento(db, mid, contato_id=_contato(db), executar_em=AGORA - timedelta(hours=3))
    fake = FakeEnviar()
    processar_ciclo(
        enviar=fake, agora=AGORA, heartbeat_anterior=AGORA - timedelta(hours=1), intervalo_s=60
    )
    db.expire_all()
    assert db.get(Agendamento, aid).status == "aguardando_decisao" and len(fake.chamadas) == 0


def test_ac19_atraso_sem_gap_dispara(db):
    mid = _modelo(db)
    aid = _agendamento(db, mid, contato_id=_contato(db), executar_em=AGORA - timedelta(hours=3))
    fake = FakeEnviar()
    processar_ciclo(
        enviar=fake, agora=AGORA, heartbeat_anterior=AGORA - timedelta(seconds=60), intervalo_s=60
    )
    db.expire_all()
    assert db.get(Agendamento, aid).status == "enviado" and len(fake.chamadas) == 1


def test_ac20_erro_definitivo_marca_falhou(db):
    mid = _modelo(db)
    aid = _agendamento(db, mid, contato_id=_contato(db))
    fake = FakeEnviar(erro=WhatsappError(131000, "falha definitiva"))
    processar_ciclo(enviar=fake, agora=AGORA)
    db.expire_all()
    envio = db.query(Envio).filter(Envio.agendamento_id == aid).one()
    assert envio.status == "falhou" and envio.erro_codigo == "131000"


# --- 0020 T3: roteamento da falha por classe (AC-5, AC-7, AC-8) ---
def _um_envio(db, aid):
    db.expire_all()
    return db.query(Envio).filter(Envio.agendamento_id == aid).one()


def test_t3_retentavel_agenda_retry(db):
    mid = _modelo(db)
    aid = _agendamento(db, mid, contato_id=_contato(db))
    fake = FakeEnviar(erro=WhatsappError(131056, "rate limit", classe="retentavel"))
    processar_ciclo(enviar=fake, agora=AGORA)
    e = _um_envio(db, aid)
    assert e.status == "aguardando_retry"
    assert e.tentativas == 1
    assert e.proxima_tentativa_em == AGORA + timedelta(minutes=5)


def test_t3_ambiguo_vai_para_decisao(db):
    mid = _modelo(db)
    aid = _agendamento(db, mid, contato_id=_contato(db))
    fake = FakeEnviar(erro=WhatsappError(500, "server error", classe="ambiguo"))
    processar_ciclo(enviar=fake, agora=AGORA)
    e = _um_envio(db, aid)
    assert e.status == "aguardando_decisao"
    assert e.tentativas == 0  # ambíguo não conta como tentativa de retry


def test_t3_definitivo_marca_falhou(db):
    mid = _modelo(db)
    aid = _agendamento(db, mid, contato_id=_contato(db))
    fake = FakeEnviar(erro=WhatsappError(131026, "número inválido", classe="definitivo"))
    processar_ciclo(enviar=fake, agora=AGORA)
    e = _um_envio(db, aid)
    assert e.status == "falhou"


# --- 0020 T4: passo de reenvio (AC-6, AC-9, AC-10, AC-11) ---
def _envio_retry(db, *, aid, cid, mid, tentativas=1, proxima=None):
    eid = str(uuid.uuid4())
    db.add(
        Envio(
            id=eid, agendamento_id=aid, contato_id=cid, modelo_id=mid,
            status="aguardando_retry", tentativas=tentativas,
            proxima_tentativa_em=proxima or (AGORA - timedelta(minutes=1)),
        )
    )
    db.commit()
    return eid


def test_t4_reenvio_no_horario_sucesso(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid)
    eid = _envio_retry(db, aid=aid, cid=cid, mid=mid, tentativas=1)
    fake = FakeEnviar()
    processar_reenvios(AGORA, None, fake)
    db.expire_all()
    e = db.get(Envio, eid)
    assert e.status == "enviado" and e.wamid and len(fake.chamadas) == 1


def test_t4_reenvio_futuro_nao_dispara(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid)
    eid = _envio_retry(db, aid=aid, cid=cid, mid=mid, proxima=AGORA + timedelta(minutes=10))
    fake = FakeEnviar()
    processar_reenvios(AGORA, None, fake)
    db.expire_all()
    assert db.get(Envio, eid).status == "aguardando_retry" and len(fake.chamadas) == 0


def test_t4_reenvio_contato_descadastrado_falhou(db):
    mid, cid = _modelo(db), _contato(db, descadastrado=True)
    aid = _agendamento(db, mid, contato_id=cid)
    eid = _envio_retry(db, aid=aid, cid=cid, mid=mid)
    fake = FakeEnviar()
    processar_reenvios(AGORA, None, fake)
    db.expire_all()
    assert db.get(Envio, eid).status == "falhou" and len(fake.chamadas) == 0


def test_t4_esgotou_terceira_tentativa_vai_para_decisao(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid)
    eid = _envio_retry(db, aid=aid, cid=cid, mid=mid, tentativas=3)
    fake = FakeEnviar(erro=WhatsappError(131056, "rate", classe="retentavel"))
    processar_reenvios(AGORA, None, fake)
    db.expire_all()
    assert db.get(Envio, eid).status == "aguardando_decisao"


# --- 0020 T5: sweep de órfãos (AC-12, AC-13) ---
def _envio_enviando(db, cid, *, criado_em):
    eid = str(uuid.uuid4())
    db.add(Envio(id=eid, contato_id=cid, status="enviando", criado_em=criado_em))
    db.commit()
    return eid


def test_t5_orfao_antigo_vai_para_decisao(db):
    eid = _envio_enviando(db, _contato(db), criado_em=AGORA - timedelta(minutes=20))
    varrer_orfaos(AGORA)
    db.expire_all()
    assert db.get(Envio, eid).status == "aguardando_decisao"


def test_t5_envio_em_voo_nao_e_recolhido(db):
    eid = _envio_enviando(db, _contato(db), criado_em=AGORA - timedelta(minutes=2))
    varrer_orfaos(AGORA)
    db.expire_all()
    assert db.get(Envio, eid).status == "enviando"


# --- 0020 double-check: ciclo completo de retry (cadeia t=1→2→3→decisão) ---
def test_dc_ciclo_completo_de_retry_esgota_e_vai_para_decisao(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid)
    err = WhatsappError(131056, "rate", classe="retentavel")

    processar_ciclo(enviar=FakeEnviar(erro=err), agora=AGORA)  # 1º envio falha
    e = _um_envio(db, aid)
    assert e.status == "aguardando_retry" and e.tentativas == 1
    assert e.proxima_tentativa_em == AGORA + timedelta(minutes=5)

    processar_reenvios(e.proxima_tentativa_em, None, FakeEnviar(erro=err))  # retry 1 falha
    e = _um_envio(db, aid)
    assert e.status == "aguardando_retry" and e.tentativas == 2

    processar_reenvios(e.proxima_tentativa_em, None, FakeEnviar(erro=err))  # retry 2 falha
    e = _um_envio(db, aid)
    assert e.status == "aguardando_retry" and e.tentativas == 3

    processar_reenvios(e.proxima_tentativa_em, None, FakeEnviar(erro=err))  # retry 3 falha → esgotou
    e = _um_envio(db, aid)
    assert e.status == "aguardando_decisao"
    assert db.query(Envio).filter(Envio.agendamento_id == aid).count() == 1  # at-most-once: 1 linha


def test_dc_retry_bem_sucedido_marca_enviado(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid)
    processar_ciclo(enviar=FakeEnviar(erro=WhatsappError(131056, "x", classe="retentavel")), agora=AGORA)
    e = _um_envio(db, aid)
    processar_reenvios(e.proxima_tentativa_em, None, FakeEnviar())  # retry 1 sucesso
    e = _um_envio(db, aid)
    assert e.status == "enviado" and e.wamid


# --- 0020 T8: invariantes (AC-17 at-most-once, AC-19 teto) ---
def test_t8_retry_reusa_a_mesma_linha(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid)
    _envio_retry(db, aid=aid, cid=cid, mid=mid)
    processar_reenvios(AGORA, None, FakeEnviar())
    db.expire_all()
    assert db.query(Envio).filter(Envio.agendamento_id == aid).count() == 1  # nunca 2ª linha (§5.2)


def test_t8_aguardando_decisao_nao_e_auto_retentado(db):
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid)
    eid = str(uuid.uuid4())
    db.add(
        Envio(
            id=eid, agendamento_id=aid, contato_id=cid, modelo_id=mid,
            status="aguardando_decisao", proxima_tentativa_em=AGORA - timedelta(hours=1),
        )
    )
    db.commit()
    fake = FakeEnviar()
    processar_reenvios(AGORA, None, fake)
    db.expire_all()
    assert db.get(Envio, eid).status == "aguardando_decisao" and len(fake.chamadas) == 0


def test_t8_aguardando_retry_conta_no_limite_por_contato(db):
    mid, cid = _modelo(db), _contato(db)
    _config(db, limite_por_contato_dia=1)
    db.add(
        Envio(
            id=str(uuid.uuid4()), contato_id=cid, status="aguardando_retry",
            criado_em=AGORA - timedelta(hours=1),
        )
    )
    db.commit()
    _agendamento(db, mid, contato_id=cid)
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    assert len(fake.chamadas) == 0  # o retry pendente já atingiu o limite → novo envio pulado


def test_ac21_auditoria_sem_pii(db):
    from app.core.telefone import mascarar_telefone

    mid, cid = _modelo(db), _contato(db)
    tel = db.get(Contato, cid).telefone_e164
    aid = _agendamento(db, mid, contato_id=cid)
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    db.expire_all()
    aud = db.query(Auditoria).filter(Auditoria.operacao == "envio.enviado").one()
    meta = json.loads(aud.metadados)
    assert meta["telefone"] == mascarar_telefone(tel) and meta["telefone"] != tel
    assert aud.correlation_id == aid


def _filhas(db, raiz_id):
    return db.query(Agendamento).filter(Agendamento.agendamento_pai_id == raiz_id).all()


def test_ac1_indice_parcial_dedup_ocorrencia(db):
    # 2ª ocorrência na mesma (raiz, executar_em) viola o índice único parcial.
    mid, cid = _modelo(db), _contato(db)
    raiz = _agendamento(db, mid, contato_id=cid, recorrencia="FREQ=DAILY", status="enviado")
    quando = AGORA + timedelta(days=1)
    _agendamento(db, mid, contato_id=cid, agendamento_pai_id=raiz, executar_em=quando)
    with pytest.raises(IntegrityError):
        _agendamento(db, mid, contato_id=cid, agendamento_pai_id=raiz, executar_em=quando)
    db.rollback()


def test_ac1_avulsos_null_pai_nao_conflitam(db):
    # Índice é PARCIAL (WHERE pai_id IS NOT NULL): dois avulsos com mesmo executar_em coexistem.
    mid, c1, c2 = _modelo(db), _contato(db), _contato(db)
    quando = AGORA + timedelta(days=2)
    _agendamento(db, mid, contato_id=c1, executar_em=quando)
    _agendamento(db, mid, contato_id=c2, executar_em=quando)  # pai_id NULL → não conflita
    assert db.query(Agendamento).filter(Agendamento.executar_em == quando).count() == 2


def test_ac6_recorrencia_cria_proxima_ocorrencia(db):
    # Mãe diária (agendamento_pai_id NULL) dispara e cria 1 ocorrência-filha.
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid, recorrencia="FREQ=DAILY")
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    db.expire_all()
    filhas = _filhas(db, aid)
    assert db.get(Agendamento, aid).status == "enviado"
    assert len(filhas) == 1
    f = filhas[0]
    assert f.status == "aprovado" and f.agendamento_pai_id == aid
    assert f.contato_id == cid and f.recorrencia == "FREQ=DAILY"
    assert f.executar_em > db.get(Agendamento, aid).executar_em
    # §5.8: a criação da ocorrência gera auditoria.
    assert db.query(Auditoria).filter(Auditoria.operacao == "agendamento.ocorrencia_criada").count() == 1


def test_ac7_recorrencia_idempotente_no_reprocesso(db):
    # Reprocessar a mãe (simula crash: volta a 'enviando' <= agora) não duplica a ocorrência.
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid, recorrencia="FREQ=DAILY")
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    db.expire_all()
    mae = db.get(Agendamento, aid)
    mae.status = "enviando"  # finge o lote interrompido antes de criar a próxima
    db.commit()
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    db.expire_all()
    assert len(_filhas(db, aid)) == 1  # ON CONFLICT DO NOTHING no índice parcial
    # auditoria também idempotente: reprocesso não re-audita (ON CONFLICT → None).
    assert db.query(Auditoria).filter(Auditoria.operacao == "agendamento.ocorrencia_criada").count() == 1


def test_ac8_filha_encadeia_na_raiz_nao_nela_mesma(db):
    # Uma filha vencida cria a próxima apontando para a MESMA raiz (não para a filha).
    mid, cid = _modelo(db), _contato(db)
    raiz = _agendamento(db, mid, contato_id=cid, recorrencia="FREQ=DAILY",
                        executar_em=AGORA - timedelta(days=1), status="enviado")
    filha = _agendamento(db, mid, contato_id=cid, recorrencia="FREQ=DAILY",
                         agendamento_pai_id=raiz, executar_em=AGORA - timedelta(minutes=1))
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    db.expire_all()
    netas = [f for f in _filhas(db, raiz) if f.id != filha]
    assert len(netas) == 1 and netas[0].agendamento_pai_id == raiz


def test_ac9_serie_esgotada_nao_cria(db):
    # COUNT=1: só a mãe; depois dela a série esgota → nenhuma filha.
    mid, cid = _modelo(db), _contato(db)
    aid = _agendamento(db, mid, contato_id=cid, recorrencia="FREQ=DAILY;COUNT=1")
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    db.expire_all()
    assert db.get(Agendamento, aid).status == "enviado" and _filhas(db, aid) == []


def test_ac10_avulso_nao_cria_ocorrencia(db):
    # Sem recorrência: nenhum agendamento novo é criado.
    mid, cid = _modelo(db), _contato(db)
    antes = db.query(Agendamento).count()
    _agendamento(db, mid, contato_id=cid)
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    db.expire_all()
    assert db.query(Agendamento).count() == antes + 1  # só o avulso criado no teste


def test_ac22_skip_locked_nao_processa_travado(db):
    import app.db.database as _dbmod

    mid = _modelo(db)
    aid = _agendamento(db, mid, contato_id=_contato(db))
    outra = _dbmod.SessionLocal()
    try:
        outra.execute(
            select(Agendamento).where(Agendamento.id == aid).with_for_update()
        ).scalar_one()  # trava numa transação paralela
        fake = FakeEnviar()
        processar_ciclo(enviar=fake, agora=AGORA)
        assert len(fake.chamadas) == 0  # travado → pulado
    finally:
        outra.rollback()
        outra.close()
    fake2 = FakeEnviar()
    processar_ciclo(enviar=fake2, agora=AGORA)  # liberado → dispara
    db.expire_all()
    assert len(fake2.chamadas) == 1 and db.get(Agendamento, aid).status == "enviado"


# --- teto de segurança por agendamento (spec 0016 / ADR 0013) ---
def _grupo(db, n: int, nome: str = "g") -> None:
    for _ in range(n):
        _contato(db, grupo=nome)


def test_teto_nulo_nao_corta(db):  # AC-1
    mid = _modelo(db)
    _grupo(db, 3)
    aid = _agendamento(db, mid, grupo="g")
    _config(db, limite_por_agendamento_dia=None)
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    assert len(fake.chamadas) == 3
    assert db.get(Agendamento, aid).status == "enviado"


def test_grupo_dentro_do_teto_enviado(db):  # AC-2
    mid = _modelo(db)
    _grupo(db, 2)
    aid = _agendamento(db, mid, grupo="g")
    _config(db, limite_por_agendamento_dia=5)
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    assert len(fake.chamadas) == 2
    assert db.get(Agendamento, aid).status == "enviado"
    assert (
        db.query(Auditoria).filter(Auditoria.operacao == "agendamento.limite_por_agendamento").count()
        == 0
    )


def test_grupo_excede_teto_parcial(db):  # AC-3
    mid = _modelo(db)
    _grupo(db, 5)
    aid = _agendamento(db, mid, grupo="g")
    _config(db, limite_por_agendamento_dia=3)
    fake = FakeEnviar()
    processar_ciclo(enviar=fake, agora=AGORA)
    assert len(fake.chamadas) == 3
    assert db.query(Envio).filter(Envio.agendamento_id == aid).count() == 3  # excedente não enviado
    assert db.get(Agendamento, aid).status == "parcial"


def test_corte_emite_auditoria_sem_pii(db):  # AC-4
    mid = _modelo(db)
    _grupo(db, 5)
    _agendamento(db, mid, grupo="g")
    _config(db, limite_por_agendamento_dia=3)
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    aud = (
        db.query(Auditoria)
        .filter(Auditoria.operacao == "agendamento.limite_por_agendamento")
        .one()
    )
    assert aud.status == "warning"
    assert json.loads(aud.metadados) == {"enviados": 3, "total": 5, "teto": 3}


def test_parcial_terminal_nao_reprocessa(db):  # AC-5
    mid = _modelo(db)
    _grupo(db, 5)
    aid = _agendamento(db, mid, grupo="g")
    _config(db, limite_por_agendamento_dia=3)
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    db.expire_all()
    fake2 = FakeEnviar()
    processar_ciclo(enviar=fake2, agora=AGORA + timedelta(minutes=1))
    assert len(fake2.chamadas) == 0  # parcial é terminal
    assert db.get(Agendamento, aid).status == "parcial"


def test_borda_n_igual_teto_enviado(db):  # borda: N == teto não corta
    mid = _modelo(db)
    _grupo(db, 3)
    aid = _agendamento(db, mid, grupo="g")
    _config(db, limite_por_agendamento_dia=3)
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    assert db.get(Agendamento, aid).status == "enviado"


def test_modelo_nao_aprovado_alerta_sentry(db, monkeypatch):  # spec 0017 AC-5
    import sentry_sdk

    alertas: list[tuple[str, dict]] = []
    monkeypatch.setattr(sentry_sdk, "capture_message", lambda msg, **kw: alertas.append((msg, kw)))
    mid = _modelo(db, status="pendente")  # modelo não aprovado → agendamento.falhou
    cid = _contato(db)
    _agendamento(db, mid, contato_id=cid)
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    assert any(op == "agendamento.falhou" and kw.get("level") == "error" for op, kw in alertas)


def test_teto_atingido_alerta_sentry(db, monkeypatch):  # spec 0017 AC-5
    import sentry_sdk

    alertas: list[tuple[str, dict]] = []
    monkeypatch.setattr(sentry_sdk, "capture_message", lambda msg, **kw: alertas.append((msg, kw)))
    mid = _modelo(db)
    _grupo(db, 5)
    _agendamento(db, mid, grupo="g")
    _config(db, limite_por_agendamento_dia=3)
    processar_ciclo(enviar=FakeEnviar(), agora=AGORA)
    assert any(
        op == "agendamento.limite_por_agendamento" and kw.get("level") == "warning"
        for op, kw in alertas
    )


# --- anexos no disparo (spec 0024, AC-9..AC-11) ---


class _FakeEnviarComp:
    """Captura os componentes passados a cada envio (para checar o cabeçalho DOCUMENT)."""

    def __init__(self) -> None:
        self.componentes: list[list] = []

    def __call__(self, telefone: str, nome: str, idioma: str, componentes: list) -> str:
        self.componentes.append(componentes)
        return f"wamid.{uuid.uuid4().hex[:8]}"


def _modelo_doc(db) -> str:
    mid = str(uuid.uuid4())
    db.add(
        Modelo(id=mid, nome=f"doc_{mid[:8]}", corpo="oi", status="aprovado", cabecalho_tipo="DOCUMENT")
    )
    db.commit()
    return mid


def _anexo(db) -> str:
    from app.models.anexo import Anexo

    aid = str(uuid.uuid4())
    db.add(Anexo(id=aid, nome_arquivo="b.pdf", mime="application/pdf", tamanho=5, conteudo=b"%PDF-"))
    db.commit()
    return aid


def _agendamento_anexo(db, modelo_id, anexo_id, *, contato_id=None, grupo=None) -> str:
    aid = str(uuid.uuid4())
    db.add(
        Agendamento(
            id=aid, modelo_id=modelo_id, anexo_id=anexo_id, contato_id=contato_id, grupo=grupo,
            executar_em=AGORA - timedelta(minutes=1), status="aprovado", variaveis=[],
        )
    )
    db.commit()
    return aid


def _headers(componentes: list) -> list:
    return [c for c in componentes if c.get("type") == "header"]


def test_anexo_inclui_document_no_envio(db, monkeypatch):  # AC-9
    chamadas: list[str] = []
    monkeypatch.setattr(
        "app.worker.disparo.upload_midia",
        lambda conteudo, mime, nome: (chamadas.append(mime), "MEDIA123")[1],
    )
    mid, cid, anexo = _modelo_doc(db), _contato(db), _anexo(db)
    aid = _agendamento_anexo(db, mid, anexo, contato_id=cid)
    fake = _FakeEnviarComp()
    processar_ciclo(enviar=fake, agora=AGORA)
    assert chamadas == ["application/pdf"]  # upload 1×
    headers = _headers(fake.componentes[0])
    assert len(headers) == 1
    assert headers[0]["parameters"][0]["document"]["id"] == "MEDIA123"
    db.expire_all()
    assert db.get(Agendamento, aid).status == "enviado"


def test_grupo_anexo_reusa_media_id(db, monkeypatch):  # AC-10
    calls: list[int] = []
    monkeypatch.setattr(
        "app.worker.disparo.upload_midia",
        lambda conteudo, mime, nome: (calls.append(1), "MEDIAXYZ")[1],
    )
    mid, anexo = _modelo_doc(db), _anexo(db)
    for _ in range(3):
        _contato(db, grupo="g")
    _agendamento_anexo(db, mid, anexo, grupo="g")
    fake = _FakeEnviarComp()
    processar_ciclo(enviar=fake, agora=AGORA)
    assert len(calls) == 1  # upload 1× para o lote inteiro
    assert len(fake.componentes) == 3  # 3 contatos
    for comps in fake.componentes:
        assert _headers(comps)[0]["parameters"][0]["document"]["id"] == "MEDIAXYZ"


def test_anexo_upload_falha_marca_falhou(db, monkeypatch):  # AC-11
    def _boom(conteudo, mime, nome):
        raise WhatsappError("erro", "falha no upload")

    monkeypatch.setattr("app.worker.disparo.upload_midia", _boom)
    mid, cid, anexo = _modelo_doc(db), _contato(db), _anexo(db)
    aid = _agendamento_anexo(db, mid, anexo, contato_id=cid)
    fake = _FakeEnviarComp()
    processar_ciclo(enviar=fake, agora=AGORA)  # não derruba o ciclo
    db.expire_all()
    assert db.get(Agendamento, aid).status == "falhou"
    assert fake.componentes == []  # nenhum envio
