"""Semente do limite diário (spec 0004 / ADR 0008): a env `LIMITE_DIARIO` só semeia o default."""

from app.core.config import Settings


def test_limite_diario_default_padrao():
    assert Settings(_env_file=None).limite_diario_default == 200


def test_limite_diario_default_le_env(monkeypatch):
    monkeypatch.setenv("LIMITE_DIARIO", "500")
    assert Settings(_env_file=None).limite_diario_default == 500
