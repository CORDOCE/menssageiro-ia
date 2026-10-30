# ADR 0002 — Escopo de respostas controladas da IA e referência §10.7

- **Status:** resolvido (seguir o BRIEFING; confirmado por Jefferson em 2026-10-30)
- **Data:** 2026-10-30
- **Contexto da feature:** `specs/0001-esqueleto-fase-1/` (não bloqueia a Fase 1)

## Contexto
No início da sessão (2026-10-30), lendo uma versão **anterior** do `BRIEFING.md`, apontei duas inconsistências:
1. `CLAUDE.md §5.5` referenciava `BRIEFING §10.7`, que **não existia** naquela versão (§10 ia até §10.6).
2. `CLAUDE.md` (§5.5–5.6, §8) tratava "respostas controladas" como parte do sistema, enquanto aquele BRIEFING
   listava "respostas automáticas da IA" **fora da v1**.

## Resolução
As inconsistências **já estavam resolvidas pelo próprio BRIEFING**, que foi atualizado (nota "Mudança de escopo
(30/10/2026)" na §1) para **incluir respostas controladas na v1**. Verificado no BRIEFING atual [arquivo:linha]:
- §1 (l.23–25): o assistente também responde mensagens recebidas, de forma controlada e monitorada; ref. §10.7.
- §3 "Fora da v1" (l.62–67): reescrita — não exclui mais respostas automáticas; exclui só assuntos fora da lista
  e negociação de valores pela IA.
- §10.7 (l.240+): fluxo completo de respostas controladas (`services/respostas/`): interruptor geral, classificação,
  guardrails em código, modo Aprovação/Automático.
- §14 fase 8 (l.321): "Respostas controladas (seção 10.7)".

Decisão: **seguir o BRIEFING** — respostas controladas são escopo da v1. O `CLAUDE.md` (§5.5 ref. §10.7, §5.6
interruptor geral, §8 módulo `respostas/`) **já está consistente** com isso; **nenhuma edição aplicada**.

## Consequências
- Nenhuma mudança no CLAUDE.md nem no BRIEFING decorrente deste ADR.
- Respostas controladas permanecem na fase 8 (BRIEFING §14); a skill `/avaliar-ia` governa prompts/regras/guardrails.
- Lição: reler a versão vigente do documento-fonte antes de afirmar inconsistência (CLAUDE.md §1.5: "não encontrei" ≠ "não existe").
