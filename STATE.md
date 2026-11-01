# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-01_

## Em andamento
- **Fase 1 (esqueleto) COMPLETA e no ar no staging.** Nada em implementação no momento.
- Próxima feature: `specs/0002-contatos-importacao/` (Fase 2) — spec aprovada, ainda não iniciada.

## Próximo passo
1. **Iniciar a Fase 2 (contatos + importação)**: spec 0002 já aprovada (via `/nova-feature`). Implementar tasks 1→10 (modelo `Contato`, migration aditiva, `core/telefone.py` com `phonenumbers`, CRUD protegido, importação CSV/XLSX com `openpyxl`). Libs aprovadas no **ADR 0006**. Respeitar a invariante de **consentimento** (CLAUDE §5.9) e o modelo do **ADR 0005**.
2. OU acertar produção (ver bloqueios).

## Fase 1 — entregue (tudo em develop, no ar no staging; login validado pela tela)
- Auth: senha (scrypt, anti-enumeração) + **2FA TOTP** + **sessão multi-dispositivo** (deslizante + teto) + **rate limit** por e-mail. Worker (heartbeat na tabela `saude`). **Frontend Next.js 16 PWA** (login senha+TOTP, shell `/painel`). **CI formal** (backend + frontend) verde em todo PR.
- Polish do login: **CORS** (#15), **mostrar senha** (#16), **lembrar e-mail/senha opt-in** (#17).
- ADRs: 0004 (sessão), 0005 (regras de envio), 0006 (E.164 `phonenumbers` / XLSX `openpyxl`).

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07` "intuitive-emotion")
- **staging** 🟢 todos online: `api`, `worker`, `frontend`, `Postgres`.
  - api `menssageiro-ia-backend-staging.up.railway.app` (Root `/backend`, Procfile; vars: ADMIN_EMAIL, DATABASE_URL, OPENAI_MODEL, TZ, FRONTEND_URL).
  - frontend `menssageiro-ia-frontend-staging.up.railway.app` (Root `/frontend`, start `npm run start`, NEXT_PUBLIC_API_URL→api).
  - worker (Root `/backend`, startCommand `python -m app.worker`, só DATABASE_URL, sem domínio).
  - Admin (1 usuário) criado com TOTP; `ADMIN_PASSWORD` removido após o setup.
- Fluxo deploy: push em `develop` → **staging**. (produção ainda segue `develop` — deveria ser `main`.)

## Bloqueios/pendências
- **Repoint `production → main`**: MANUAL no painel da Railway (o classificador do modo automático bloqueia armar deploys de produção). Nada vai para produção sem passar por staging e promover `develop`→`main`.
- Endurecimentos anotados (futuro, não bloqueiam): cifrar `totp_secret` em repouso; alerta em `login_bloqueado` (BRIEFING §12); cookie HttpOnly no lugar de token/senha em localStorage; contraste WCAG no CI (fase de UI).

## Estado do git
- `develop` = `9e59a95` (após PRs #5–#17). **Sem PRs abertos.** Nada não-commitado.
- Branches de feature da Fase 1 já mergeadas — podem ser apagadas no remote quando quiser.
