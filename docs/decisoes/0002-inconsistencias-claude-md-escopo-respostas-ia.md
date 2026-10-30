# ADR 0002 — Inconsistências entre CLAUDE.md e BRIEFING (referência §10.7 e escopo de respostas da IA)

- **Status:** proposto (aguarda decisão do responsável, Jefferson)
- **Data:** 2026-10-30
- **Contexto da feature:** `specs/0001-esqueleto-fase-1/` (não bloqueia a Fase 1)

## Contexto
Durante a leitura dos documentos (sessão de 2026-10-30) foram encontradas duas inconsistências:

1. **Referência a seção inexistente.** `CLAUDE.md §5.5` diz: "A IA não envia nada sem passar pelas verificações
   em código (**BRIEFING §10.7**)". O `BRIEFING.md §10` vai só até **§10.6** (10.1 Cliente WhatsApp, 10.2 Webhook,
   10.3 Worker, 10.4 IA, 10.5 Comandos, 10.6 Frontend). Não existe §10.7. [verificado: BRIEFING §10 lido por inteiro]

2. **Escopo de "respostas da IA".** `CLAUDE.md` trata respostas controladas como parte do sistema: §5.5–5.6
   (a IA responde dentro de verificações; "interruptor geral de respostas... checado a cada ciclo"), §8 (módulo
   `respostas/` com mypy estrito), e a skill `/avaliar-ia`. Já o `BRIEFING.md §3` lista **"Respostas automáticas
   da IA para os contatos"** explicitamente **fora da v1**. O pedido de abertura do projeto também chamou o sistema
   de "respostas controladas", reforçando a tensão.

## Decisão (pendente)
Opções a decidir com o responsável:
- **(a)** Respostas controladas da IA **entram na v1** → atualizar o BRIEFING §3 (tirar de "fora da v1"), criar a
  seção BRIEFING §10.7 descrevendo as verificações, e manter CLAUDE.md como está.
- **(b)** Respostas **ficam fora da v1** (como no BRIEFING) → ajustar CLAUDE.md §5.5–5.6 e §8 para não pressupor o
  módulo de respostas na v1, e corrigir/remover a referência à §10.7.

## Consequências
- Não afeta a Fase 1 (esqueleto/CI/login) — registrado para resolver **antes das fases de IA (3/6)**.
- A escolha muda o escopo das fases de IA, o módulo `respostas/` e a aplicação da skill `/avaliar-ia`.
- Enquanto pendente, nenhum código de respostas da IA é escrito.
