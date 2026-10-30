# ADR 0001 — Autenticação de 1 usuário com 2FA (TOTP), herdada do projeto antigo

- **Status:** aceito
- **Data:** 2026-10-30
- **Contexto da feature:** `specs/0001-esqueleto-fase-1/`

## Contexto
A Fase 1 exige login funcionando (critério de pronto, BRIEFING §14). O BRIEFING §2 fixa "1 usuário (admin) com
verificação em duas etapas (TOTP)" e o §8 manda reaproveitar a autenticação do projeto antigo
`document-ai-system` (`app/api/auth.py`, `app/core/security.py`, `app/core/auth_deps.py`, modelo de usuário),
copiando e adaptando — **nunca alterando o projeto antigo**. Autenticação molda todo endpoint protegido, por isso
a decisão é difícil de reverter e vira ADR.

## Decisão
1. Herdar a estratégia de sessão/autenticação já usada no projeto antigo (será confirmada lendo o código herdado
   antes da implementação — CLAUDE.md §1, sem supor JWT vs cookie), mantendo-a como baseline.
2. Simplificar para **1 usuário admin** (sem cadastro aberto nem papéis).
3. Somar **2FA obrigatório via TOTP** (biblioteca `pyotp`), exigido em todo login.
4. **Rate limit** no endpoint de login (CLAUDE.md §6) e resposta genérica para usuário/senha inválidos.
5. Reset de senha por e-mail (Resend) fica fora da Fase 1 (reaproveitável depois).

## Consequências
- Menos código novo e caminho já validado em produção; custo de ler/entender o código herdado antes de adaptar.
- O 2FA entra desde o esqueleto, elevando o escopo da Fase 1 (aceito — é o critério de pronto).
- Qualquer mudança futura no mecanismo de sessão exige novo ADR.
