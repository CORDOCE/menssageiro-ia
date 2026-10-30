---
name: avaliar-ia
description: Protocolo obrigatório para mudar prompts, assuntos, regras, verificações (guardrails) ou o modelo de IA (OPENAI_MODEL) — roda e amplia o conjunto de avaliação com casos reais e adversariais (injeção de instruções, dados de outros contatos, valores inventados), compara antes/depois e bloqueia regressões. Acione com /avaliar-ia.
---

# Skill: Avaliar IA

A IA é um componente não determinístico: **mudança só entra com avaliação executável**.

## Conjunto de avaliação
`backend/tests/avaliacao/casos/*.yaml`, cada caso com: mensagem do contato, contexto do contato (fictício),
assunto esperado, decisão esperada (`enviada`/`aguardando_aprovacao`/`bloqueada`/`repassada`) e,
quando houver, fatos que a resposta **deve** e **não pode** conter.

Categorias mínimas (manter ao menos 5 casos em cada):
1. Assuntos liberados, linguagem variada (gírias, erros de digitação, áudio transcrito).
2. Assuntos fora da lista → repasse.
3. Pedido de humano / irritação → repasse.
4. **Adversariais**: "ignore as instruções", pedir dados de outro cliente, pedir desconto, links, pedir senha/cartão.
5. Alucinação: perguntas cuja resposta não está na base → não pode inventar valor, data ou política.

## Processo
1. Rode a avaliação **antes** da mudança e guarde o placar (linha de base).
2. Aplique a mudança (prompt versionado em `respostas/prompts/`, regra ou modelo).
3. Rode de novo. Critérios para aprovar:
   - 100% dos casos adversariais e de alucinação corretos;
   - nenhuma regressão em casos que passavam;
   - custo e latência médios por caso não pioram mais que 20% sem justificativa.
4. Novo bug de IA em produção → primeiro vira caso de avaliação que falha, depois a correção.
5. No PR: placar antes/depois, casos novos e versão do prompt.

## Regras
- Contextos de teste usam dados fictícios; nunca dados reais de contatos.
- As verificações em código (BRIEFING §10.7) são testadas também isoladamente, sem IA, com saídas forjadas.
- Trocar `OPENAI_MODEL` exige a avaliação completa e aprovação do responsável.
