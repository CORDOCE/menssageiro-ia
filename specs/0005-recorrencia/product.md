---
name: product-recorrencia
description: Product brief da spec 0005 — recorrência de agendamentos. Cada ocorrência vira uma nova linha de agendamento; o worker cria a próxima no disparo, sem duplicar. Problema, métrica e fronteiras.
---

# Product: Recorrência de agendamentos (spec 0005)

## Problema
A Fase 4 (spec 0004) entrega o disparo de agendamentos **avulsos** (one-off), mas o BRIEFING §1/§3 exige
mensagens **recorrentes** (ex.: "todo dia 5", "toda segunda") — é parte do núcleo do produto. As colunas
`agendamento_pai_id` e `recorrencia` já existem no schema (criadas inertes na 0004, por decisão do ADR 0005),
mas **sem nenhuma lógica**. Falta: o operador define uma regra de recorrência num agendamento, e o worker, ao
disparar uma ocorrência, **cria automaticamente a próxima** — no horário certo, **sem duplicar** ocorrências
(inclusive após reinício).

Para quem: o operador (agenda uma vez uma série recorrente) e os contatos que recebem as mensagens nas datas certas.

## Métrica de sucesso
Observável por testes de integração (PostgreSQL real; Meta mockada — §5.7):
1. Um agendamento com regra de recorrência, ao ser disparado pelo worker, **gera a próxima ocorrência** como
   **nova linha de agendamento** (`status=aprovado`, `agendamento_pai_id` = série, `executar_em` = próxima data).
2. **Idempotência da recorrência:** rodar o ciclo de novo (ou reiniciar o worker) **não cria ocorrências
   duplicadas** — garantido por `UNIQUE(agendamento_pai_id, executar_em)` (ADR 0005).
3. A série **termina** quando a regra se esgota (data final / contagem) — não gera ocorrência além do previsto.

## Goals
- **Regra de recorrência no agendamento** (`recorrencia`): o operador cria um agendamento recorrente via API; o
  schema e a validação aceitam a regra (formato RRULE — BRIEFING §9).
- **Worker cria a próxima ocorrência no disparo** (BRIEFING §10.3 / ADR 0005 §2): ao processar uma ocorrência
  vencida, calcula a **próxima data** pela regra e insere a próxima linha de agendamento, dedupada por
  `UNIQUE(agendamento_pai_id, executar_em)` (migração adiciona esse índice).
- **Encadeamento de série:** `agendamento_pai_id` liga as ocorrências à série; a primeira é a "mãe".
- **Fim da série:** respeitar data final/contagem da regra; sem próxima ocorrência quando esgota.
- API para **criar recorrente** e **cancelar a série** (cancelar as ocorrências futuras pendentes).

## Non-goals (vinculante)
- **Envio real / número +55:** continua adiado (ver memória [[meta-numero-teste-nao-entrega-brasil]]); recorrência
  é testada com **mock** do envio, como a Fase 4.
- **Anexos (DOCUMENT)** e **texto livre/janela 24 h** → fora (specs próprias / Fase 8).
- **Telas do PWA** (criar recorrência pela UI) → Fase 5; aqui é só API + worker.
- **Edição de série** (mudar a regra no meio) e **exceções/"pular esta ocorrência"** → fora desta spec (revisitar).
- **Sugestões de recorrência pela IA** → Fase 6.

## Dependências / decisão em aberto (§4)
- **Cálculo da próxima ocorrência a partir de RRULE** exige uma **biblioteca** (candidata: `python-dateutil`) —
  **dependência nova, precisa de aprovação do responsável (§4)**. Alternativa: implementar um subconjunto
  (diária/semanal/mensal) à mão, sem dependência. **Decisão pendente antes do `design.md`.**

## Questões para /clarificar (gate da spec)
1. Quais frequências/opções de RRULE entram na v1 (diária/semanal/mensal? intervalo? dia da semana? fim por data/contagem?).
2. "Cancelar série" cancela só as ocorrências **futuras pendentes** (as já enviadas ficam)? (proposta: sim.)
3. Horizonte de criação: cria **só a próxima** ocorrência a cada disparo (lazy) — confirmando a abordagem do ADR 0005.
