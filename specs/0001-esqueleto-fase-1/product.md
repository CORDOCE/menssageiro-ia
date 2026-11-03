---
name: product-esqueleto-fase-1
description: Product brief da feature 0001-esqueleto-fase-1 (tier arquitetural). Esqueleto do monorepo, CI e base de autenticação para a Fase 1 do BRIEFING §14.
---

# Product: Esqueleto da Fase 1 do Mensageiro

> Produto, arquitetura e regras completas estão no `BRIEFING.md`. Este brief cobre só o recorte da Fase 1
> (BRIEFING §14) e não redefine o produto.

## Problema
Não há código nem pipeline: é impossível implementar qualquer regra de negócio (contatos, templates, envio,
IA) sem um monorepo que builde, teste e rode, com o operador conseguindo **entrar no sistema com segurança**.
A Fase 1 entrega essa fundação para o responsável (Jefferson) e o operador único (cliente).

## Metrica de sucesso
Critério de pronto do BRIEFING §14: **login (1 usuário + 2FA TOTP) funciona em staging e o CI está verde**.
Observável: pipeline de CI verde no PR para `develop`; em staging, `/health` responde no domínio público, o
worker loga ≥1 ciclo/min, e o operador loga no frontend com senha + código TOTP.

## Goals
- Monorepo `backend/` (FastAPI + worker) + `frontend/` (Next.js PWA) que builda, linta, tipa e testa localmente e no CI.
- Autenticação de 1 usuário com 2FA (TOTP) e rate limit no login; rota protegida real.
- Migrações Alembic com `upgrade`/`downgrade` funcionais.
- Worker com loop de 60 s gravando heartbeat (`ultimo_ciclo_em`).
- CI GitHub Actions: backend (ruff, mypy, pytest + Postgres, pip-audit) e frontend (eslint, tsc, build, npm audit).
- Repositório pronto para o deploy manual na Railway (estrutura, start commands e `/health` compatíveis com `RAILWAY.md`).

## Non-goals (vinculante)
- Nenhuma regra de negócio das fases 2–8: contatos, templates, agendamentos, envio real, webhook da Meta,
  IA/sugestões, comandos pelo WhatsApp. (Worker só com heartbeat; nenhum envio.)
- Nenhuma chamada real à Meta ou OpenAI (CLAUDE.md §5.7).
- Nenhuma ação na Railway, no GitHub remoto ou no painel da Meta — são passos **manuais** do responsável (RAILWAY §3–§11).
- Multiusuário, papéis/permissões avançadas.
