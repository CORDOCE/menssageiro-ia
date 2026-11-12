# Tasks — 0023 Notificações push (Web Push/VAPID)

| # | Task | AC | Gate (teste) | Status |
|---|---|---|---|---|
| 1 | `pyproject.toml`: dep `pywebpush` (fixada) + `uv lock` | — | `uv sync` ok | todo |
| 2 | `models/push_subscription.py` + migração `push_subscriptions` (endpoint único, p256dh, auth) | AC-2,3 | `alembic upgrade head && downgrade` ok | todo |
| 3 | `services/push.py`: `chave_publica()`, `inscrever(db, sub)` (upsert), `enviar_push(titulo, corpo, url=None)` (no-op sem VAPID; pywebpush; remove 404/410; nunca levanta) | AC-4,5,6 | `test_push_service.py` | todo |
| 4 | `schemas/push.py` + `api/push.py` (`GET /push/chave-publica`, `POST /push/inscrever`) + registro `main.py` | AC-1,2,3 | `test_push_api.py`: 401; chave; upsert | todo |
| 5 | `core/observabilidade.py`: em `alertar_evento`, após o Sentry, `enviar_push(op, resumo)` (sem PII) | AC-7,8 | `test_observabilidade.py` (+AC-7): error/warning chama, ok não | todo |
| 6 | Frontend `public/sw.js`: handlers `push` + `notificationclick` | AC-9 | smoke/manual | todo |
| 7 | Frontend `lib/push.ts` + `lib/api.ts` (`obterChavePush`/`inscreverPush`) | AC-9 | tsc | todo |
| 8 | Frontend card "Notificações" em `configuracoes/page.tsx` (ativar, sem suporte, sucesso) | AC-9 | `page.test.tsx` (Vitest) | todo |

## Gates finais (antes do PR)
- Backend: `ruff` + `mypy` + `pytest` (cobertura 90%+ em `services/push.py` e `api/push.py`) + migração up/down + `pip-audit`.
- Frontend: `eslint` + `tsc` + `vitest` + `build` + `npm audit`.
- `/revisar` → `/seguranca` (superfície: endpoint de inscrição = input externo; SSRF do envio a endpoint de push arbitrário — mitigar) → `/validar` (AC-1..AC-9) → CI Docker. PR `feat/0023` → `develop`.

## Notas de segurança (p/ o /seguranca)
- `enviar_push` manda HTTP ao `endpoint` da inscrição (vem do browser). É Web Push padrão (endpoints dos push
  services dos browsers), mas o endpoint é **input externo** → considerar validar o host (allowlist de push services
  conhecidos) ou aceitar o risco (o endpoint só é usado se autenticado inscreveu). Decidir no /seguranca.
- Chaves VAPID só em env; corpo do push sem PII (AC-8).
- Eu gero o par VAPID (via `py-vapid`); Jefferson seta `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` na Railway.
