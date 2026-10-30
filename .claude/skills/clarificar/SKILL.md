---
name: clarificar
description: SABATINA — entrevista implacavel que transforma intencao difusa em entendimento compartilhado ANTES de construir. Caminha a arvore de decisao UMA pergunta por vez, resolvendo dependencias entre escolhas, sempre com uma resposta recomendada; explora o codebase/docs em vez de perguntar quando a resposta ja existe. Ideal nos gates de spec (AC testaveis) e design (decisao dificil de reverter). Acione com /clarificar.
---

# Skill: Clarificar (sabatina)

Fecha a ambiguidade antes de gastar token em codigo. Use quando a duvida e **profunda e
ramificada** (uma escolha depende da outra) — nesses casos uma pergunta-por-vez vale mais que um
lote, porque cada resposta abre/fecha ramos.

## Como conduzir
1. **Explore primeiro.** Se a resposta esta no codebase/docs/spec, **ache em vez de perguntar**.
   So pergunte o que voce genuinamente nao consegue inferir.
2. **Uma pergunta por vez.** Caminhe a arvore: a proxima pergunta depende da resposta anterior.
3. **Sempre ofereca uma resposta recomendada** ("(Recomendado)") com o porque — reduz carga e
   ancora a decisao. Use `AskUserQuestion` pra ofertar opcoes.
4. **Marque o que e suposicao** vs fato confirmado. Não avance sobre suposicao silenciosa.
5. **Pare quando o entendimento fecha** — nao alongue por completude.

## Saida
Um **resumo de entendimento** curto (decisoes tomadas, suposicoes, fora de escopo) que alimenta
`product.md` / `design.md` / `spec.md`. Se uma decisao for dificil de reverter, sinalize que vira
ADR. Devolva ao fluxo que chamou (`/nova-feature`, `/validar`, ou direto).
