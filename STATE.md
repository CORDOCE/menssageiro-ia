# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-10-30_

## Em andamento
- **Spec ativa:** `specs/0001-esqueleto-fase-1/` (Esqueleto da Fase 1).
- **PR #2** (`docs/adr-0002-escopo-respostas-ia` → `develop`): ADR 0002 encerrado (resolvido — seguir o
  BRIEFING, respostas controladas na v1) + housekeeping (STATE.md e sync do `tasks.md`). Revisado, `MERGEABLE`.
- **PR #3** (`docs/regra-gates-ci-docker-pre-pr` → `develop`): regra de governança CLAUDE.md §4.4
  (gates + CI via Docker antes de PR de código). Separado do PR #2 a pedido do responsável.

## Próximo passo
1. **PRs #2 e #3** revisados (docs-only, sem achados). Aguardam **autorização explícita do Jefferson
   para mergear** em `develop` (CLAUDE.md §4.2 — merge só com pedido).
2. Depois do merge: seguir a spec 0001 pelo backend — **task 3** (`app/db/database.py` SQLAlchemy 2 +
   Alembic, migração base; usar `/migracao`) → task 5 (auth) → task 6 (2FA TOTP) → 7 (rate limit) →
   8 (worker loop) → 9 (cobertura ≥90%). Frontend (10→11) em paralelo. CI (12) por último.

## Decisões da sessão
- ADR 0002 resolvido: seguir o BRIEFING; nenhuma edição em CLAUDE.md/BRIEFING necessária. Ver
  `docs/decisoes/0002-inconsistencias-claude-md-escopo-respostas-ia.md`.
- `tasks.md` da spec 0001 sincronizado com a realidade: tasks **1, 2, 4** (backend esqueleto + /health,
  já em `develop` via PR #1, commit `b2f8616`) e **13** (ADRs 0001 e 0002) marcadas `done`.

## Bloqueios/pendências
- Merge dos PRs #2 e #3 depende de autorização do Jefferson.
- **Regra CLAUDE.md §4.4 (no PR #3):** só se torna plenamente executável quando existirem `docker-compose`
  (PostgreSQL local) e `.github/workflows/ci.yml` — previstos nas tasks 3 e 12 da spec 0001.
- claude-mem (memória de sessões) estava **indisponível** nesta sessão (`fetch failed`) — diagnóstico
  feito via git + arquivos.

## Estado do git
- PRs abertos: **#2** `docs(adr): encerrar ADR 0002` e **#3** `docs: regra §4.4 gates+CI Docker`, ambos → `develop`.
- `develop` já contém o esqueleto backend (PR #1 mergeado).
