# ADR 0009 — Recorrência: RRULE via python-dateutil, criação lazy da próxima ocorrência

- **Status:** aceito
- **Data:** 2026-11-04
- **Contexto da feature:** spec `0005-recorrencia`; decisões fechadas na sabatina `/clarificar` de 2026-11-04.
- **Aprovação:** recorrência é **regra de envio** (CLAUDE.md §4) — as decisões abaixo, inclusive a **dependência
  nova** `python-dateutil`, foram aprovadas por Jefferson (2026-11-04). O contrato de domínio (ocorrência = nova
  linha; dedup por `UNIQUE(agendamento_pai_id, executar_em)`) já vinha do **ADR 0005**; este ADR fixa o **como**.

## Contexto
O BRIEFING §9 define `recorrencia (RRULE)` e §10.3 manda o worker criar a próxima ocorrência no disparo. O
ADR 0005 decidiu que cada ocorrência é uma **nova linha** de agendamento e que a criação é dedupada por
`UNIQUE(agendamento_pai_id, executar_em)`. Faltava fechar, por serem caros de reverter:
1. **Como calcular a próxima data** a partir da regra — biblioteca vs implementação à mão.
2. **Em que formato** a regra é gravada.
3. **Qual o horizonte de materialização** — criar a série toda vs só a próxima.

## Decisão
1. **`python-dateutil` (RRULE iCalendar) para calcular datas.** `dateutil.rrule.rrulestr` parseia e itera a
   regra; `proxima_ocorrencia` usa `.after(apos, inc=False)`. Licença BSD/Apache-2.0, biblioteca madura.
   Implementar à mão reinventaria matemática de calendário (meses, dias da semana, `UNTIL`/`COUNT`, bordas de
   fuso) — descartado. `croniter` (cron) foi descartado por não ser o padrão RRULE do BRIEFING.
2. **`recorrencia` é a string RRULE** (ex.: `FREQ=MONTHLY;BYMONTHDAY=5`), gravada na coluna `agendamentos.recorrencia`
   (Text, já existente). `NULL` = agendamento avulso (one-off). Menos "tipado" que um JSON próprio, mas é o padrão
   que a biblioteca entende e o BRIEFING §9 adota.
3. **Validação permissiva (aceitar qualquer RRULE válida).** `validar_regra` só confirma que o `dateutil`
   parseia a string (inválida → 422 na API). Não há whitelist de frequências: restringir exigiria mais código
   para **rejeitar** casos legítimos (ex.: `INTERVAL`, `BYDAY`). Regra "patológica" (ex.: `COUNT` enorme) é
   inofensiva porque a criação é **lazy** (uma ocorrência por vez). O núcleo (`DAILY`/`WEEKLY`/`MONTHLY` +
   `INTERVAL` + `BYDAY` + `BYMONTHDAY` + `UNTIL` + `COUNT`) é garantido por teste.
4. **Criação lazy: o worker cria só a próxima ocorrência no disparo.** Ao disparar uma ocorrência com
   `recorrencia`, calcula a próxima data e insere **uma** nova linha (`agendamento_pai_id` = raiz da série,
   `executar_em` = próxima data), com `INSERT … ON CONFLICT DO NOTHING` no índice único parcial
   `UNIQUE(agendamento_pai_id, executar_em) WHERE agendamento_pai_id IS NOT NULL`. Materializar a série toda é
   impossível para séries sem fim (`FREQ` sem `UNTIL`/`COUNT`) — descartado. A raiz é `ag.agendamento_pai_id or
   ag.id`; o `dtstart` da série é o `executar_em` da raiz.
5. **`cancelar-serie` encerra só as ocorrências futuras pendentes** (`status='aprovado'` e `executar_em > agora`
   da mesma série); as já enviadas ficam. Cancelar uma ocorrência isolada continua sendo o `/cancelar` da 0004.

## Consequências
- **Dependência:** `python-dateutil` fixada em `backend/pyproject.toml`.
- **Schema (migração 0005):** adiciona o índice único parcial em `agendamentos` (as colunas já existiam, ADR 0008).
- **Fuso/DST:** cálculo em `America/Sao_Paulo` (`zoneinfo`), gravando `timestamptz` (§8); normalizar datas
  aware/naive antes de iterar (o `dateutil` lança `TypeError` ao misturar `dtstart` aware com `UNTIL` naive).
- **Idempotência:** reprocesso/reinício no meio não duplica ocorrência — o `ON CONFLICT DO NOTHING` no índice
  parcial garante no máximo uma filha por `(agendamento_pai_id, executar_em)`. Não altera a idempotência de
  envio da 0004 (`UNIQUE(agendamento_id, contato_id)`, por ocorrência).
- **Séries sem fim:** seguem indefinidamente por desenho; `cancelar-serie` as encerra.
- **Fora deste ADR:** edição de série (mudar a regra no meio), exceções ("pular esta ocorrência"), sugestão de
  recorrência pela IA e telas do PWA → specs/fases seguintes.
