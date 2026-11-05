# Tasks — 0009 Inicializar Sentry (S3)

Gate: `ruff` + `mypy` 0; `pytest` (afetados) verde; cobertura ≥90%. Suíte completa + `pip-audit` antes do PR.

| # | Task | AC | Gate (prova) | Status |
|---|------|----|--------------|--------|
| 1 | Dep `sentry-sdk` (versão fixada) em `backend/pyproject.toml`; `uv sync` | — | `pip-audit` 0; import ok | done |
| 2 | `core/observabilidade.py`: `configurar_sentry()` (no-op sem DSN; init idempotente e à prova de DSN ruim) + `_mascarar_pii` (before_send: mascara telefone, remove `request.data`; nunca levanta) | AC-1,2,3 | testes: init só com DSN (mock); mask telefone; remove body; DSN ruim não derruba | done |
| 3 | `app/main.py`: chamar `configurar_sentry()` no import (antes do `FastAPI(...)`) | AC-1,2 | app sobe; smoke/import ok | done |
| 4 | `app/worker/__main__.py`: `configurar_sentry()` no `main()`; `capture_exception()` no `except` do ciclo (junto da auditoria) | AC-1,4 | teste: exceção no ciclo → `capture_exception` chamado | done |
| 5 | Suíte completa + cobertura ≥90%; `ruff`/`mypy` 0 | AC-1..4 | `pytest --cov` verde | done |

## Pós-implementação (fora do código)
- [ ] Setar `SENTRY_DSN` na Railway (staging e produção) — infra, aprovação §4. Sem DSN o Sentry fica inerte (seguro).
- [ ] `/revisar` + `/seguranca` + `/validar` + CI antes do PR.
