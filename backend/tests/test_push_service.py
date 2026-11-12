"""Service de Web Push (spec 0023, AC-3..AC-6): inscrição + envio. `webpush` é mockado (sem rede, §5.7)."""

import uuid

from pywebpush import WebPushException

from app.core.config import get_settings
from app.models.push_subscription import PushSubscription
from app.services import push as push_mod
from app.services.push import enviar_push, inscrever


def _sub(db, endpoint):
    db.add(PushSubscription(id=str(uuid.uuid4()), endpoint=endpoint, p256dh="p", auth="a"))
    db.commit()


class _Resp:
    def __init__(self, status):
        self.status_code = status


def _com_vapid(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "vapid_public_key", "PUB")
    monkeypatch.setattr(s, "vapid_private_key", "PRIV")


def test_inscrever_upsert(db):  # AC-3
    s1 = inscrever(db, "https://push/1", "p1", "a1")
    s2 = inscrever(db, "https://push/1", "p2", "a2")  # mesmo endpoint
    assert s1.id == s2.id
    assert db.query(PushSubscription).count() == 1
    assert db.query(PushSubscription).one().p256dh == "p2"


def test_enviar_noop_sem_vapid(db, monkeypatch):  # AC-4
    _sub(db, "https://push/1")
    chamadas: list = []
    monkeypatch.setattr(push_mod, "webpush", lambda **k: chamadas.append(k))
    enviar_push("op", "corpo")
    assert chamadas == []  # no-op: webpush não é chamado sem VAPID


def test_enviar_com_vapid_limpa_410(db, monkeypatch):  # AC-5
    _com_vapid(monkeypatch)
    _sub(db, "https://push/ok")
    _sub(db, "https://push/gone")
    chamadas: list[str] = []

    def _fake(**k):
        ep = k["subscription_info"]["endpoint"]
        chamadas.append(ep)
        if ep.endswith("/gone"):
            raise WebPushException("gone", response=_Resp(410))

    monkeypatch.setattr(push_mod, "webpush", _fake)
    enviar_push("op", "corpo")
    assert len(chamadas) == 2  # tentou as duas
    db.expire_all()
    enderecos = {s.endpoint for s in db.query(PushSubscription).all()}
    assert "https://push/gone" not in enderecos  # inscrição expirada removida
    assert "https://push/ok" in enderecos


def test_enviar_nunca_derruba(db, monkeypatch):  # AC-6
    _com_vapid(monkeypatch)
    _sub(db, "https://push/boom")
    _sub(db, "https://push/ok")
    recebidos: list[str] = []

    def _fake(**k):
        ep = k["subscription_info"]["endpoint"]
        if ep.endswith("/boom"):
            raise RuntimeError("erro inesperado")
        recebidos.append(ep)

    monkeypatch.setattr(push_mod, "webpush", _fake)
    enviar_push("op", "corpo")  # não propaga
    assert "https://push/ok" in recebidos  # o outro ainda recebeu


def test_enviar_erro_nao_expirado_mantem(db, monkeypatch):  # AC-6 (borda: 500 não remove a inscrição)
    _com_vapid(monkeypatch)
    _sub(db, "https://push/err")

    def _fake(**k):
        raise WebPushException("erro servidor", response=_Resp(500))

    monkeypatch.setattr(push_mod, "webpush", _fake)
    enviar_push("op", "corpo")  # não propaga
    db.expire_all()
    assert db.query(PushSubscription).filter_by(endpoint="https://push/err").count() == 1
