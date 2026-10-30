# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-10-30_

## Em andamento
- **Spec ativa:** `specs/0001-esqueleto-fase-1/` (Esqueleto da Fase 1).
- **Task 5 (modelo `usuario` + auth)** **commitada** (`b58151f`) no branch `feat/0001-task5-usuario-auth`
  (a partir de `develop`). **Só senha** (TOTP é task 6; rate limit é task 7). Ainda **sem push/PR**.

## Próximo passo
1. **Push + abrir PR** `feat/0001-task5-usuario-auth` → `develop` (aguarda autorização do Jefferson).
   Commit pronto; gates e review já feitos.
2. **Task 6**: 2FA TOTP (`pyotp` — dep nova, precisa aprovação §4) no fluxo de login; usa `usuarios.totp_secret`.
3. Depois: task 7 (rate limit no login) → 8 (worker) → 9 (cobertura) → 10–11 (frontend) → 12 (CI).

## Como a auth foi feita (ADR 0001, herdada de `document-ai-system`, adaptada)
- Sessão = **token opaco Bearer no banco** (tabela `sessoes_usuario`), não JWT/cookie. 1 sessão ativa por usuário.
- Tabelas pt-BR: `usuarios`, `sessoes_usuario`, `auditoria`. Sem papéis (1 admin). Datas `timestamptz`.
- Endurecimentos vs. herdado: token via `secrets.token_urlsafe`, senha com scrypt + `hmac.compare_digest`,
  resposta genérica anti-enumeração, auditoria não-bloqueante de login/logout (invariante §5.8).
- Rotas: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`. Admin criado por `python -m app.criar_admin`.
- `pyproject`: ruff `flake8-bugbear.extend-immutable-calls` p/ o padrão `Depends/Header` do FastAPI.

## Validação da task 5 (§4.4, Postgres via Docker) — concluída
- Gates verdes: ruff, mypy (17 arquivos), **16 testes** (1 health + 15 auth), ciclo `alembic base→head`,
  `pip-audit` sem vulnerabilidades. **Cobertura das regras de auth = 100%** (auth.py, auth_deps.py, security.py, audit.py).
- `/revisar` + `/seguranca`: 1 achado corrigido — **timing enumeration** no login (scrypt roda contra hash
  fictício quando o e-mail não existe → "mesmo custo de tempo" da spec). Sem P0/P1 nem CRÍTICO/ALTO em aberto.
- Migração `ab30d72b78e4` (cria as 3 tabelas); revisada linha a linha; downgrade funcional.

## Bloqueios/pendências
- Push/PR da task 5 aguarda autorização do Jefferson.
- Testes usam um banco dedicado `<db>_test` (criado pela fixture). Container `mensageiro-ia-db-1` de pé.

## Estado do git
- Branch: `feat/0001-task5-usuario-auth`, commit `b58151f`, **árvore limpa** (exceto este STATE.md ao salvar).
- `develop` = topo `d7bee54` (PRs #1–#4 mergeados).
