---
name: tasks-esqueleto-fase-1
description: Quebra de tasks da feature 0001-esqueleto-fase-1. Cada task mapeia 1+ AC e aponta o comando de teste (gate) que a prova.
---

# Tasks: Esqueleto da Fase 1 do Mensageiro

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 0 | Infra git: `git init`, branches `main`/`develop`, `.gitignore`, `.env.example` | — | — | `git rev-parse --abbrev-ref HEAD` = feature off `develop`; `git check-ignore .env` | done |
| 1 | `backend/pyproject.toml` com stack e configs de ruff/mypy/pytest; estrutura `app/` | AC-1 | 0 | `ruff check .` e `mypy app` → código 0 | done |
| 2 | `app/core/config.py` (pydantic-settings) lendo `.env` | AC-1 | 1 | incluído no gate de AC-1; teste de carga de settings | done |
| 3 | `app/db/database.py` (SQLAlchemy 2) + Alembic (`alembic.ini`, `migrations/env.py`, migração base) | AC-4 | 1,2 | `alembic upgrade head` && `alembic downgrade base` → código 0 | done |
| 4 | `app/main.py` FastAPI + `GET /health` | AC-3 | 1,2 | teste: `GET /health` → 200 JSON "ok" | done |
| 5 | Modelo `usuario` + auth herdada (adaptar BRIEFING §8) simplificada p/ 1 admin | AC-7 | 3,4 | teste: rota protegida 401 sem token / 200 com token | todo |
| 6 | 2FA TOTP (pyotp) no fluxo de login | AC-5, AC-6 | 5 | teste matriz de decisão (senha×TOTP) | todo |
| 7 | Rate limit no login | AC-8 | 5 | teste: N falhas → 429 | todo |
| 8 | `app/worker/__main__.py` loop 60 s + heartbeat, sem envio | AC-9 | 3 | teste: 1 ciclo grava `ultimo_ciclo_em`; asserção de "nenhum envio" | todo |
| 9 | Suíte de testes backend com cobertura ≥90% das regras de auth | AC-2 | 4–8 | `pytest --cov` → 0 e cobertura ≥90% | todo |
| 10 | `frontend/` Next.js TS estrito + PWA (manifest/SW) + tokens de tema | AC-10 | — | `npm run lint && npx tsc --noEmit && npm run build` → 0 | todo |
| 11 | Tela de login + shell protegido consumindo a API | AC-11 | 6,10 | teste e2e/manual: login válido → shell; inválido → erro | todo |
| 12 | `.github/workflows/ci.yml` (backend + frontend + contraste WCAG) | AC-12 | 1–11 | mesmos comandos verdes localmente; CI verde no 1º PR | todo |
| 13 | ADR 0001 (auth/2FA) e ADR 0002 (inconsistências doc) em `docs/decisoes/` | — | — | arquivos presentes e linkados no design.md | done |

> `[P]` na frente de uma task = pode rodar em paralelo. Tasks 10 (frontend) e 1–9 (backend) são largamente paralelas;
> 11 e 12 dependem de ambas.

## Ordem de execução sugerida
Backend 1→9, frontend 10→11 em paralelo, CI 12 por último. Migração (task 3) e qualquer mudança de esquema passam
por `/migracao`. Antes do PR: `/revisar` → `/seguranca` → `/validar`.

## Definition of Done (resumo — detalhe no CLAUDE.md §9)
- [ ] Todo AC verde pelo **gate executável** (não por inspeção)
- [ ] Cobertura ≥ 90% nas regras de auth, relatório anexado ao PR
- [ ] `/revisar` sem P0/P1 e `/seguranca` sem Crítico/Alto, zero segredo
- [ ] Sem `SPEC_DEVIATION` aberto
- [ ] Commit limpo (zero co-autoria, zero segredo); PR com objetivo/risco/plano de teste
- [ ] Validado em staging (login + `/health` + heartbeat do worker)
- [ ] `STATE.md` atualizado
