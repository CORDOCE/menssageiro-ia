# Tasks — 0022 Job diário de sincronização de modelos

| # | Task | AC | Gate (teste) | Status |
|---|---|---|---|---|
| 1 | `services/modelos_sync.py`: extrair `sincronizar_modelos(db, templates, *, ator_email)` + `_extrair_componentes` + `_STATUS_META` + `SincronizarResultado` | AC-6 | `test_modelos_sync.py`: upsert cria+atualiza, mapa de status, auditoria | todo |
| 2 | `api/modelos.py`: `sincronizar` passa a `listar_templates()` + delegar ao service | AC-5 | `test_modelos_api.py` (existente) segue verde | todo |
| 3 | `core/config.py`: `sync_modelos_hora: int = 6` | AC-1,2 | referência nos testes | todo |
| 4 | `worker/jobs_diarios.py`: `ciclo_jobs_diarios(agora)` + guarda `_ja_rodou_hoje` (auditoria `job.sincronizar_modelos` no dia SP); degrada exceção | AC-1..AC-4 | `test_jobs_diarios.py`: roda ≥06h; cedo não roda; idempotência; falha audita error sem propagar | todo |
| 5 | `worker/__main__.py`: chama `ciclo_jobs_diarios()` no loop (após `ciclo_alertas`) | AC-1 | smoke do loop | todo |

## Gates finais (antes do PR)
- Backend: `ruff` + `mypy` + `pytest` (cobertura 90%+ no service e no job) + `pip-audit`. Sem migração.
- `/revisar` → `/seguranca` → `/validar` (AC-1..AC-6) → CI Docker completo. PR `feat/0022` → `develop`.

## Notas
- O endpoint segue importando `listar_templates` (os testes mockam `app.api.modelos.listar_templates`) e
  **passa os templates** ao service — refactor sem mudar o ponto de mock (AC-5 sem editar os testes existentes).
- Guarda de idempotência e fronteira de dia SP: molde de `worker/alertas.py` (`_ja_alertou_hoje`).
- `job.sincronizar_modelos` com `status="error"` em falha **não** usa `alertar=True` (não é evento §12 de
  modelo pausado/rejeitado; vai ao Sentry pela captura de exceção, não por alerta de e-mail).
