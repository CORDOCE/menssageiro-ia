---
name: spec-esqueleto-fase-1
description: Spec da feature 0001-esqueleto-fase-1. A fonte da verdade — os critérios de aceite são o contrato e o oráculo de teste.
---

# Spec: Esqueleto da Fase 1 do Mensageiro

## Contexto
Fundação do monorepo, CI e login (1 usuário + 2FA) para a Fase 1 do BRIEFING §14. Detalhes em `product.md` e `design.md`.
Pronto quando "login funciona em staging e CI verde". Nenhuma regra de negócio das fases 2–8 entra aqui.

## Criterios de aceite (o contrato)
Cada AC é testável e não-ambíguo (Definition of Ready). Um teste/gate por AC.

- **AC-1** — Dado o repositório clonado, Quando rodo `ruff check .` e `mypy app` em `backend/`, Então ambos terminam com código 0 (sem erros de lint/tipo).
- **AC-2** — Dado o `backend/` com dependências instaladas e um PostgreSQL de teste, Quando rodo `pytest`, Então a suíte passa com código 0 e cobertura das regras de auth ≥ 90% (CLAUDE.md §8).
- **AC-3** — Dado a API em execução, Quando faço `GET /health`, Então recebo HTTP 200 com corpo JSON indicando status "ok" (sem exigir dependências externas da Meta/OpenAI).
- **AC-4** — Dado um banco limpo, Quando rodo `alembic upgrade head` e depois `alembic downgrade base`, Então ambos terminam com código 0 e o esquema volta ao estado vazio (downgrade funcional — CLAUDE.md §4.5).
- **AC-5** — Dado um admin cadastrado com senha e segredo TOTP, Quando faço login enviando senha correta **e** código TOTP válido, Então recebo uma credencial de sessão válida (HTTP 200).
- **AC-6** — Dado o mesmo admin, Quando faço login com senha correta mas **código TOTP ausente ou inválido**, Então o acesso é negado (HTTP 401/403) e nenhuma credencial é emitida.
- **AC-7** — Dada uma rota protegida, Quando a acesso **sem** credencial válida, Então recebo HTTP 401; Quando a acesso **com** credencial válida, Então recebo HTTP 200.
- **AC-8** — Dado o endpoint de login, Quando excedo o limite de tentativas falhas configurado dentro da janela, Então as tentativas seguintes são bloqueadas (HTTP 429) por rate limit (CLAUDE.md §6).
- **AC-9** — Dado o processo worker, Quando executo `python -m app.worker` por mais de um ciclo, Então ele grava um heartbeat (`ultimo_ciclo_em`) a cada ~60 s e **não realiza nenhum envio**.
- **AC-10** — Dado o `frontend/`, Quando rodo `npm run lint`, `npx tsc --noEmit` e `npm run build`, Então os três terminam com código 0.
- **AC-11** — Dado o frontend buildado apontando para a API, Quando abro a tela de login e envio credenciais válidas (senha + TOTP), Então sou autenticado e vejo o shell protegido; credenciais inválidas mostram erro e não autenticam.
- **AC-12** — Dado um push/PR para `develop`, Quando o workflow de CI roda, Então executa os jobs de backend (ruff, mypy, pytest+Postgres, pip-audit) e frontend (eslint, tsc, build, npm audit) e fica verde.

## Casos de borda
- TOTP com janela de tempo: código do passo imediatamente anterior/seguinte (drift) — definir tolerância explícita no teste.
- Login com usuário inexistente vs senha errada: mesma resposta genérica (não revelar qual falhou) e mesmo custo de tempo.
- `alembic downgrade base` em banco já vazio não deve quebrar.
- `/health` deve responder mesmo sem variáveis da Meta/OpenAI configuradas (não depende delas).
- Worker reiniciado no meio de um ciclo: próximo ciclo grava heartbeat normalmente (sem estado em memória — BRIEFING §5).
- Rate limit: contador por identificador de origem; expira após a janela.

## Fora de escopo (vinculante)
- Contatos, templates, agendamentos, envios, webhook da Meta, IA/sugestões, comandos pelo WhatsApp (fases 2–8).
- Qualquer chamada real à Meta/OpenAI; worker não envia nada.
- Criação/alteração de serviços, variáveis ou ambientes na Railway, no GitHub remoto ou no painel da Meta (passos manuais do responsável — RAILWAY §3–§11).
- `/admin/health/deep`, métricas de saúde completas e telas além de login/shell.
- Reset de senha por e-mail (Resend) — reaproveitável depois; não é requisito do login da Fase 1.

## Matriz de decisao — autenticação no login (cada linha vira um teste)
| senha correta | TOTP válido | credencial de sessão? | resultado esperado |
|---|---|---|---|
| sim | sim | emite | 200 (AC-5) |
| sim | não/ausente | não emite | 401/403 (AC-6) |
| não | sim | não emite | 401/403 (resposta genérica) |
| não | não/ausente | não emite | 401/403 (resposta genérica) |
| (qualquer) | (qualquer), após exceder tentativas | não emite | 429 (AC-8) |
