# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-03_

## Em andamento
- **Fase 2 (`specs/0002-contatos-importacao/`) CODE-COMPLETE na branch `feat/0002-contatos`.** Gate pré-PR passado (/revisar, /seguranca, /validar + CI backend). **PR ainda não aberta.**

## Próximo passo
1. **Abrir PR de `feat/0002-contatos` → `develop`** (objetivo/risco/plano de teste; linkar ADR 0006). Sem P0/P1 nem CRÍTICO/ALTO em aberto.
2. Após merge em `develop` → deploy staging → **validar em staging**: importar planilha CSV/XLSX com validação; conferir que nenhum envio ocorre (DoD da spec 0002).

## Fase 2 — entregue (branch `feat/0002-contatos`, 5 commits a partir da develop)
- `9aa990c` modelo/migração/`core/telefone.py`/deps · `3efc02c` CRUD+descadastro+consentimento · `402a9de` serviço de import · `f18d72d` endpoint multipart+limites · `80c8017` auditoria sem PII + cobertura.
- 12 tasks completas (TDD). **78 passed, cobertura 98.06%**, ruff+mypy 0, ciclo Alembic EXIT=0, pip-audit limpo.
- Deps novas aprovadas (§4): `phonenumbers`, `openpyxl` (ADR 0006) e **`python-multipart`** (adendo ao ADR 0006, 2026-11-03).
- Revisões pré-PR: `/revisar` → PRONTO PRA PR (3 notas P2); `/seguranca` → sem vulnerabilidade bloqueante (3 notas MEDIO de endurecimento). Detalhe no histórico da sessão.

## Notas P2/MEDIO registradas (não bloqueiam; revisitar quando fizer sentido)
- Dedup POST/import é SELECT-then-INSERT → corrida concorrente viraria 500 em vez de 409 (1 admin → desprezível; unicidade garantida pelo índice).
- Upload: cap `read(max+1)` limita memória, mas o ASGI já recebe o corpo (spool em disco) — endurecer com limite de corpo no proxy/Railway. openpyxl em `read_only`/`data_only` + limites de 5 MB/5000 linhas mitigam zip-bomb.
- Futuro: proteção contra CSV formula-injection quando houver **export** de contatos.
- Comentário em `api/contatos.py:95` sobre o cap de leitura pode ser suavizado (não impede o recebimento do corpo).

## Fase 1 — entregue (em develop, no ar em staging)
- Auth senha(scrypt)+2FA TOTP+sessão multi-dispositivo+rate limit; worker heartbeat; frontend Next.js PWA; CI backend+frontend. ADRs 0004/0005/0006.

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07`)
- **staging** 🟢 `api`/`worker`/`frontend`/`Postgres`. Deploy: push em `develop` → staging. (produção ainda segue `develop`; repoint → `main` é pendência manual da Fase 1.)
- Dev/testes locais: `docker compose up -d db` (container `mensageiro-ia-db-1`, Postgres 17, porta 5434).

## Estado do git
- Branch **`feat/0002-contatos`** (da `develop`=`8ee144b`), 5 commits à frente. **Sem PR aberta.**
- `docs/codebase-map`: 1 commit `6f03cdc` (CODEBASE_MAP + ponteiro no CLAUDE.md), sem PR.
- Branch remota obsoleta `origin/feat/0002-contatos-importacao` (sem PR) pode ser apagada quando quiser.
