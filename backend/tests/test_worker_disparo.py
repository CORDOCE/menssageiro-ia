"""Worker de disparo (spec 0004, AC-8..AC-22): núcleo do envio com PostgreSQL real e mock da Meta.

`AGORA` = terça 2026-11-03 10:00 em America/Sao_Paulo (= 13:00 UTC), dentro da janela padrão.
`AGORA_FORA` = domingo 2026-11-08 12:00 SP, fora da janela.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.agendamento import Agendamento
from app.models.auditoria import Auditoria
from app.models.configuracao import ID_CONFIG, Configuracao
from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo
from app.services.whatsapp_client import WhatsappError
from app.worker.disparo import processar_ciclo

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
                 status="aprovado", variaveis=None) -> str:
    aid = str(uuid.uuid4())
    db.add(
        Agendamento(
            id=aid, modelo_id=modelo_id, contato_id=contato_id, grupo=grupo,
            executar_em=executar_em or (AGORA - timedelta(minutes=1)),
            status=status, variaveis=variaveis or [],
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
