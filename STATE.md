# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-10-30_

## Em andamento
- **Spec ativa:** `specs/0001-esqueleto-fase-1/` (Esqueleto da Fase 1).
- **Task 3 (DB/Alembic)** implementada e **validada** no branch `feat/0001-task3-db-alembic`
  (commit `96d9c9f`), ainda **sem push/PR**. Gates da §4.4 rodados (ver abaixo).

## Próximo passo
1. **Push + abrir PR** de `feat/0001-task3-db-alembic` → `develop` (aguarda autorização do Jefferson).
2. Depois: seguir a spec 0001 — task 5 (modelo `usuario` + auth) → 6 (2FA TOTP) → 7 (rate limit) →
   8 (worker loop) → 9 (cobertura ≥90%). Frontend (10→11) em paralelo. CI (12) por último.

## Validação da task 3 (§4.4, equivalente de CI no host via Docker)
- `/revisar`: PRONTO PRA PR (1 P2 corrigido — interpolação `%` da URL no `env.py`).
- `/seguranca`: sem CRÍTICO/ALTO (1 MÉDIO corrigido — bind do Postgres restrito a `127.0.0.1`).
- Gates verdes com Postgres dockerizado: ruff, mypy, pytest, ciclo `alembic upgrade/downgrade/upgrade`
  (AC-4), `pip-audit` (sem vulnerabilidades). `ci.yml` formal fica para a task 12.

## Decisões da sessão
- PRs **#2** (ADR 0002 + housekeeping) e **#3** (regra CLAUDE.md §4.4: gates + CI via Docker) já
  **mergeados** em `develop`. Branches mergeadas apagadas (local + origin).
- Task 3: migração base **vazia** (não há modelos ainda; `usuario` é a task 5) — só estabelece a cadeia
  Alembic e torna o AC-4 testável. URL do banco lida do `Settings` no `env.py` (não no `alembic.ini`).
- `docker-compose` usa Postgres na porta **5434** do host (5432/5433 ocupadas por outros projetos nesta máquina).
- `migrations/versions/` excluído do ruff (arquivos gerados; revisão manual via `/migracao`).

## Bloqueios/pendências
- A regra §4.4 ainda carece de `.github/workflows/ci.yml` (task 12) para o job de CI formal; o
  `docker-compose` já existe (criado na task 3).
- claude-mem (memória de sessões) estava **indisponível** nesta sessão (`fetch failed`).

## Estado do git
- Branch atual: `feat/0001-task3-db-alembic` (sem commit ainda; mudanças no working tree).
- `develop` = topo `e3d07b8` (PRs #1, #2, #3 mergeados).
- Arquivos da task 3: `docker-compose.yml`, `backend/app/db/{__init__,database}.py`, `backend/alembic.ini`,
  `backend/migrations/**`, e ajustes em `backend/pyproject.toml`, `backend/app/core/config.py`, `.env.example`, `tasks.md`.
