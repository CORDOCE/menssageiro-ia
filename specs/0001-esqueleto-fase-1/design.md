---
name: design-esqueleto-fase-1
description: Design doc da feature 0001-esqueleto-fase-1 (tier arquitetural). Estrutura do monorepo, stack, autenticação 2FA e CI, reaproveitando o projeto antigo.
---

# Design: Esqueleto da Fase 1 do Mensageiro

## Solucao proposta
Respeitar a arquitetura já fixada no `BRIEFING.md` (§5 arquitetura, §6 layout, §7 stack) — não inventar padrão novo.

**Estrutura (BRIEFING §6):**
- `backend/` — um único código Python 3.12 servindo dois processos: `app.main:app` (API FastAPI) e
  `python -m app.worker` (loop). Camadas conforme §6: `app/api`, `app/core`, `app/models`, `app/schemas`,
  `app/services`, `app/worker`; `migrations/` (Alembic); `tests/`; `pyproject.toml`.
- `frontend/` — Next.js + TypeScript estrito, PWA (manifest + service worker), tokens de tema (DESIGN §2/§10).
- `.github/workflows/ci.yml` — CI.

**Nesta fase, cada camada entra só com o mínimo para o login funcionar e os gates passarem:**
- `app/main.py`: FastAPI com `/health` (shallow; o `/admin/health/deep` do BRIEFING §12 fica para fases posteriores)
  e o router de auth.
- `app/core/config.py`: `pydantic-settings` lendo as variáveis do `.env.example`.
- `app/db/database.py`: engine/sessão SQLAlchemy 2 (reúso adaptado do projeto antigo — BRIEFING §8).
- `app/models/usuario.py` + auth: **adaptados** de `document-ai-system` (`app/api/auth.py`, `app/core/security.py`,
  `app/core/auth_deps.py`, modelo de usuário — BRIEFING §8), simplificados para 1 admin e com TOTP somado.
- `app/worker/__main__.py`: loop de 60 s que só grava heartbeat (`configuracoes.ultimo_ciclo_em` ou tabela de
  saúde) — **nenhum envio** (non-goal).

**Reaproveitamento (BRIEFING §8):** copiar e adaptar do projeto antigo; **nunca alterar o projeto antigo**.
A abordagem exata de sessão (JWT vs cookie de sessão) será **confirmada lendo o código herdado** antes de codar
(CLAUDE.md §1) e mantida como baseline — esta fase apenas acrescenta o 2FA e a simplificação para 1 usuário.

## Alternativas consideradas
| opcao | pros | contras | veredito |
|---|---|---|---|
| A (escolhida) — herdar a auth do projeto antigo + somar TOTP (pyotp) | Menos código novo; BRIEFING §8 manda reusar; já rodou em produção | Precisa ler/entender o código herdado antes | **Escolhida** |
| B — auth nova do zero | "Limpa" | Reinventa o que já existe; viola BRIEFING §8; mais risco | Descartada |
| Monorepo backend único p/ api+worker (vs dois pacotes) | BRIEFING §2/§6 já decidiu; 1 base, 2 start commands (RAILWAY §4/§5) | — | Já decidido no BRIEFING (sem ADR) |

## Trade-offs e riscos
- **Login é o critério de pronto da fase**, então a fase carrega auth+2FA de verdade (não é só "hello world"). Aceito.
- **GRAPH_API_VERSION** e versões de libs: não inventar; fixar versões lendo o que o ambiente resolver e confirmar
  na doc oficial quando tocar a Meta (fase 3). Nesta fase a Meta não é usada.
- Reúso do frontend (`cordoce-frontend`): aproveitar casca (login/layout/tema); risco de arrastar código morto —
  mitigado trazendo só o necessário para login + shell.
- Testes de integração exigem PostgreSQL real (CLAUDE.md §8) — usar container (serviço do GitHub Actions no CI; Docker local).

## Decisoes irreversiveis (-> ADR)
- **ADR 0001** — Estratégia de autenticação e 2FA (TOTP) herdada e simplificada para 1 usuário. Molda todo endpoint protegido.
- **ADR 0002** (status: proposto, aguarda decisão do responsável) — Inconsistências doc encontradas: (a) `CLAUDE.md §5.5`
  referencia `BRIEFING §10.7` inexistente; (b) escopo de "respostas da IA" (`CLAUDE.md §5.5–5.6, §8`) vs `BRIEFING §3`
  que as põe fora da v1. Não bloqueia a Fase 1; decidir antes das fases de IA (3/6).
