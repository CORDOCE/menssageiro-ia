---
name: design-recorrencia
description: Design doc da spec 0005 — recorrência (tier arquitetural). RRULE via python-dateutil; o worker cria a próxima ocorrência (nova linha de agendamento) no disparo, dedupada por UNIQUE(agendamento_pai_id, executar_em). Implementa ADR 0005. Alternativas, trade-offs, riscos e ADR 0009.
---

# Design: Recorrência de agendamentos (spec 0005)

> **Contrato já aprovado:** ADR 0005 (cada ocorrência = nova linha de agendamento; dedup por
> `UNIQUE(agendamento_pai_id, executar_em)`), BRIEFING §9 (`recorrencia (RRULE)`), §10.3 (worker cria a próxima
> ocorrência no disparo). **Dependência `python-dateutil` aprovada (§4, 2026-11-04).**

## Solução proposta
Respeitar a arquitetura existente (SQLAlchemy 2, Alembic, worker em `worker/disparo.py`, serviços em `services/`).
A recorrência é **lazy**: o worker cria **só a próxima** ocorrência quando dispara a atual (ADR 0005) — nunca
materializa a série toda (séries sem fim seriam infinitas).

### Dependência (§4)
- **`python-dateutil`** adicionado ao `pyproject.toml` (`uv sync`). Licença Apache-2.0/BSD; maduro; `dateutil.rrule`
  parseia e itera RRULE (iCalendar). Justificativa no PR (necessidade: RRULE do BRIEFING §9; alternativa à mão
  reinventa matemática de data). → **ADR 0009**.

### Dados (migração aditiva)
- `agendamentos.recorrencia` (Text, **já existe** inerte desde a 0004): guarda a **string RRULE** (ex.:
  `FREQ=MONTHLY;BYMONTHDAY=5`, `FREQ=WEEKLY;BYDAY=MO;UNTIL=20270101T000000Z`). `NULL` = one-off.
- `agendamentos.agendamento_pai_id` (String(36), **já existe** inerte): aponta para a **raiz da série** (a 1ª
  ocorrência, "mãe"). A mãe tem `agendamento_pai_id = NULL`; cada ocorrência-filha aponta para o id da raiz.
- **Migração 0005:** adiciona **índice único parcial** `UNIQUE(agendamento_pai_id, executar_em) WHERE
  agendamento_pai_id IS NOT NULL` — dedup das ocorrências de uma série (nulos dos one-offs/mães não conflitam).

### Serviço `services/recorrencia.py`
- `proxima_ocorrencia(regra: str, dtstart: datetime, apos: datetime) -> datetime | None`:
  `dateutil.rrule.rrulestr(regra, dtstart=dtstart).after(apos, inc=False)`; devolve a próxima data **estritamente
  após `apos`** ou `None` se a série esgotou (`UNTIL`/`COUNT`). Tudo tz-aware em `America/Sao_Paulo`, gravado
  `timestamptz` (§8; reusa o padrão de `services/janela.py`).
- `validar_regra(regra: str) -> None`: parseia a RRULE; inválida → exceção → 422 na API.

### Worker (`worker/disparo.py`)
Ao terminar o disparo de um agendamento **com `recorrencia`** (depois do loop de contatos, antes/junto de marcar
`enviado`): calcula `proxima = proxima_ocorrencia(recorrencia, dtstart=<executar_em da raiz>, apos=executar_em)`.
Se `proxima` não for `None`, insere a **próxima ocorrência** (nova linha `Agendamento`, `status=aprovado`,
mesmos `contato_id`/`grupo`/`modelo_id`/`variaveis`/`recorrencia`, `agendamento_pai_id = raiz`, `executar_em =
proxima`) com `INSERT … ON CONFLICT DO NOTHING` no índice `(agendamento_pai_id, executar_em)` — **idempotente**:
reinício/reprocesso não duplica. `raiz = ag.agendamento_pai_id or ag.id`. `dtstart` da série = `executar_em` da
raiz (buscado quando `ag` é filha).

### API (`api/agendamentos.py`)
- `POST /agendamentos`: `AgendamentoCriar` ganha `recorrencia: str | None`. Se setada, `validar_regra` (422 se
  inválida); o agendamento criado é a **raiz** (`agendamento_pai_id = NULL`).
- `POST /agendamentos/{id}/cancelar-serie`: cancela as ocorrências **futuras pendentes** da série (status
  `aprovado` e `executar_em > agora`, mesma raiz) → `cancelado`. As já enviadas ficam. (Cancelar uma ocorrência
  isolada = o `cancelar` da 0004.)

## Alternativas consideradas
| Opção | Prós | Contras | Veredito |
|---|---|---|---|
| **`python-dateutil` (RRULE)** | padrão iCalendar; casa com BRIEFING §9; robusto | 1 dep nova | **Escolhida (§4 ok → ADR 0009)** |
| Implementar freq à mão | zero dep | reinventa data/bordas; limitado | Descartada |
| `croniter` (cron) | leve | sintaxe cron ≠ RRULE do BRIEFING | Descartada |
| **Lazy: cria só a próxima** | séries infinitas ok; barato | 1 ocorrência "viva" por vez | **Escolhida (ADR 0005)** |
| Materializar série toda | simples de listar | infinito sem `UNTIL`; explode | Descartada |
| **Índice único parcial p/ dedup** | reinício não duplica (ADR 0005) | — | **Escolhida** |
| `recorrencia` como RRULE string | padrão; dateutil parseia | menos "tipado" que JSON | **Escolhida** (BRIEFING §9) |

## Trade-offs e riscos
- **Fuso/DST:** calcular em `America/Sao_Paulo` (zoneinfo), gravar `timestamptz`. Brasil sem DST hoje; cobrir borda.
- **Séries sem fim** (`FREQ` sem `UNTIL`/`COUNT`): lazy → seguem indefinidamente (intencional). `cancelar-serie` as encerra.
- **Idempotência:** `ON CONFLICT (agendamento_pai_id, executar_em)` evita ocorrência duplicada após reinício no meio.
- **Entrada da RRULE** (operador): `validar_regra` com dateutil antes de aceitar; rejeitar RRULE pathológica
  (ex.: `COUNT` enorme é inofensivo no lazy, mas validar formato). Reusa a disciplina de input do repo (Pydantic/422).
- **Interação com a 0004:** a criação da próxima ocorrência entra no fim de `_processar_agendamento`; não muda a
  idempotência do envio (índice `(agendamento_id, contato_id)` continua valendo por ocorrência).
- **Sem Meta real** (§5.7): testado com mock; envio real segue adiado (número +55).

## Decisões irreversíveis (→ ADR 0009 proposto)
- **ADR 0009 — Recorrência: RRULE via python-dateutil, criação lazy da próxima ocorrência.**
  (a) dependência `python-dateutil`; (b) `recorrencia` = string RRULE; (c) worker cria **só a próxima**
  ocorrência no disparo, dedup por índice parcial `UNIQUE(agendamento_pai_id, executar_em) WHERE
  agendamento_pai_id IS NOT NULL`. Difícil de reverter: define formato gravado e semântica da série.

## Questões para /clarificar (gate da spec)
1. Opções de RRULE na v1 (diária/semanal/mensal, intervalo, BYDAY, UNTIL/COUNT) — quais garantir por teste.
2. `cancelar-serie` = só ocorrências futuras pendentes (proposta: sim; as enviadas ficam).
3. Confirmar criação **lazy** (só a próxima) — alinhado ao ADR 0005.
