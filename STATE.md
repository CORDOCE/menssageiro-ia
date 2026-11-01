# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-01_

## Em andamento
- **Spec ativa:** `specs/0001-esqueleto-fase-1/` (Fase 1).
- **Task 5b (sessão multi-dispositivo, ADR 0004)** implementada e validada no branch
  `feat/0001-fase1-auth-sessao-2fa` (de `develop`). **PR pendente** (aguarda autorização).

## Próximo passo
1. Abrir/mergear o PR de `feat/0001-fase1-auth-sessao-2fa` → `develop` (auto-deploy no **staging**).
2. **Validar login multi-dispositivo no staging**: criar admin (`ADMIN_EMAIL`/`ADMIN_PASSWORD` + `python -m app.criar_admin`) e testar 2 dispositivos, logout isolado, logout-todos.
3. **Task 6 (2FA TOTP)** — precisa aprovar a dep `pyotp` (§4); reabre `auth.py`. Depois **task 7** (rate limit no login).

## Validação da task 5b (host via Docker, Postgres :5434)
- Gates verdes: ruff, mypy (17 arq.), **pytest 23 passed**, **cobertura 100%** das regras de auth, pip-audit sem vulnerabilidades.
- Migração aditiva `58eccad8f930` (sessoes_usuario: `ultimo_uso_em` + `user_agent`): ciclo upgrade/downgrade/upgrade e base→head→base = 0.
- `/revisar`: 1 P1 (user_agent sem truncar → 500 com UA > 255) corrigido + teste. `/seguranca`: sem Crítico/Alto (2 MÉDIO anotados: escapar user_agent na futura tela de dispositivos; janela de sessão maior é trade-off do ADR 0004).

## O que a task 5b entregou
- Login **não revoga** sessões anteriores (multi-dispositivo); `logout` só o dispositivo atual; novo `POST /auth/logout-todos`.
- Expiração **deslizante** (7d inatividade) + **teto absoluto** (30d), renovação com throttle (5 min); colunas `ultimo_uso_em`/`user_agent`.
- `config.py`: `session_inatividade_dias`/`session_max_dias`/`session_throttle_min` (substituíram `session_horas`).

## Railway (infra)
- **staging** `api` 🟢 LIVE de `develop` (`...-staging.up.railway.app`), Postgres próprio. **production** 🟢 (deploy antigo) — **repoint para `main` é MANUAL** (Settings→Source no painel; bloqueado no modo automático).
- Fluxo: push em `develop` → staging; `develop`→`main` → produção. `worker`/`frontend` nas tasks 8/10.

## Estado do git
- Branch: `feat/0001-fase1-auth-sessao-2fa` (de `develop` `12bcc24`). Commit da task 5b a fazer.
- `develop` topo após PRs #5/#6/#7/#8 (refino, task 5, Fase 2 spec, Procfile).
