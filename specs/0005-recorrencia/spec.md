---
name: spec-recorrencia
description: Spec da spec 0005 — recorrência de agendamentos. Os critérios de aceite são o contrato e o oráculo de teste. RRULE via python-dateutil; o worker cria a próxima ocorrência (nova linha) no disparo, dedupada por UNIQUE(agendamento_pai_id, executar_em). Implementa ADR 0005; decide ADR 0009.
---

# Spec: Recorrência de agendamentos (spec 0005)

## Contexto
O BRIEFING §1/§3/§9 exige mensagens **recorrentes** ("todo dia 5", "toda segunda"). A Fase 4 (spec 0004)
entregou só o disparo de agendamentos avulsos; as colunas `agendamento_pai_id` e `recorrencia` já existem
**inertes** no schema (migração `5d75fec0aa05`, ADR 0005). Esta spec implementa o contrato do **ADR 0005**:
cada ocorrência de uma série é uma **nova linha** de agendamento, e o worker cria **só a próxima** ocorrência
(lazy) ao disparar a atual, dedupada por `UNIQUE(agendamento_pai_id, executar_em)`. Detalhes e trade-offs em
`product.md`/`design.md`. **Pronto quando**: um agendamento com regra de recorrência, ao ser disparado, gera a
próxima ocorrência como nova linha (sem duplicar, inclusive após reinício), a série termina quando a regra
esgota, e a API cria recorrente e cancela a série — e os AC abaixo passam.

**Dependências:** `python-dateutil` (RRULE), aprovado por Jefferson (§4, 2026-11-04) → **ADR 0009**. Envio
**real** à Meta segue adiado (número +55 — ver memória). **Não bloqueia os AC**, que passam com **mock** de
`enviar_template` e **PostgreSQL real em container** (§5.7).

## Decisões do gate (/clarificar 2026-11-04 — recorrência = regra de envio, §4, aprovadas por Jefferson)
1. **RRULE v1:** aceitar **qualquer RRULE válida** (validação = "o `dateutil` parseia"); garantir por teste o
   núcleo `FREQ=DAILY/WEEKLY/MONTHLY` + `INTERVAL` + `BYDAY` + `BYMONTHDAY` + `UNTIL` + `COUNT`.
2. **`cancelar-serie`:** afeta só ocorrências **futuras pendentes** (`status=aprovado` e `executar_em > agora`);
   as já enviadas ficam intactas.
3. **Criação lazy:** o worker cria **só a próxima** ocorrência no disparo (ADR 0005). → **ADR 0009**.

## Critérios de aceite (o contrato)

**Schema / migração (Alembic, com `downgrade` — §4.5 / /migracao)**
- **AC-1** — Dado banco com o schema da 0004, Quando `alembic upgrade head`, Então cria o índice **único
  parcial** `UNIQUE(agendamento_pai_id, executar_em) WHERE agendamento_pai_id IS NOT NULL` em `agendamentos`;
  `downgrade -1` o remove sem erro. Linhas com `agendamento_pai_id IS NULL` (avulsos/mães) **não** conflitam.

**Serviço de recorrência (`services/recorrencia.py`; unitário, sem banco)**
- **AC-2** — Dado uma RRULE válida e um `dtstart`, Quando `proxima_ocorrencia(regra, dtstart, apos)`, Então
  devolve a **próxima data estritamente após `apos`**, aware/UTC; cobre o núcleo (Q1): diária, semanal com
  `BYDAY`, mensal com `BYMONTHDAY`, `INTERVAL>1`.
- **AC-3** — Dado uma série que **esgotou** (`UNTIL` no passado ou `COUNT` atingido), Quando
  `proxima_ocorrencia(...)`, Então devolve **`None`**.
- **AC-4** — Dado uma RRULE **inválida** (sintaxe quebrada), Quando `validar_regra(regra)`, Então **levanta
  exceção**; RRULE válida → não levanta.
- **AC-5 (fuso/DST)** — Dado `dtstart`/`apos` e uma RRULE com `UNTIL`, Quando `proxima_ocorrencia(...)`, Então
  não quebra por mistura de datas aware/naive e as comparações ocorrem em `America/Sao_Paulo` (grava UTC — §8).

**Worker de disparo (`worker/`; mock de `enviar_template`, PostgreSQL real)**
- **AC-6** — Dado 1 agendamento `aprovado` **vencido** **com `recorrencia`** (mãe, `agendamento_pai_id=NULL`),
  Quando o worker roda 1 ciclo, Então, além de disparar a atual, cria **1 nova** linha de agendamento com
  `status='aprovado'`, `agendamento_pai_id` = id da mãe, `executar_em` = próxima data, e os mesmos
  `contato_id`/`grupo`/`modelo_id`/`variaveis`/`recorrencia`.
- **AC-7 (idempotência — §5.2)** — Dado o mesmo cenário do AC-6, Quando o worker processa a mãe **duas vezes**
  (reprocesso/reinício no meio), Então existe **no máximo uma** ocorrência-filha para aquele
  `(agendamento_pai_id, executar_em)` — o `ON CONFLICT DO NOTHING` não duplica.
- **AC-8 (encadeamento)** — Dado uma ocorrência-**filha** vencida com `recorrencia`, Quando o worker a dispara,
  Então cria a **próxima** filha com `agendamento_pai_id` = **mesma raiz** (não a filha), `executar_em`
  calculado a partir do `dtstart` = `executar_em` **da raiz**.
- **AC-9 (fim da série)** — Dado uma ocorrência cuja regra **esgota** após ela (`UNTIL`/`COUNT`), Quando o
  worker a dispara, Então **não** cria próxima ocorrência.
- **AC-10 (avulso intacto)** — Dado um agendamento vencido **sem `recorrencia`** (`NULL`), Quando o worker roda,
  Então **nenhuma** ocorrência nova é criada (comportamento da 0004 inalterado).

**API agendamentos (`/agendamentos`, `Depends(usuario_atual)`; §5.1 — só registra)**
- **AC-11** — Dado operador autenticado, Quando `POST /agendamentos` com `recorrencia` **válida**, Então
  **201**, agendamento criado como **raiz** (`agendamento_pai_id=NULL`) com a `recorrencia` gravada.
- **AC-12** — Dado `POST /agendamentos` com `recorrencia` **inválida**, Então **422** — nada é criado.
- **AC-13** — Dado uma série com ocorrências futuras pendentes e passadas já enviadas, Quando
  `POST /agendamentos/{id}/cancelar-serie` (com `id` da mãe **ou** de qualquer filha), Então as ocorrências da
  série com `status='aprovado'` e `executar_em > agora` viram **`cancelado`**; as **enviadas ficam intactas**;
  auditoria registrada (§5.8).

## Tabela de bordas (oráculo de teste)
| Caso | Entrada | Esperado |
|---|---|---|
| Diária simples | `FREQ=DAILY`, dtstart hoje 09:00, apos=hoje 09:00 | amanhã 09:00 |
| Semanal BYDAY | `FREQ=WEEKLY;BYDAY=MO`, apos=segunda | próxima segunda |
| Mensal BYMONTHDAY | `FREQ=MONTHLY;BYMONTHDAY=5`, apos=dia 5 | dia 5 do mês seguinte |
| Intervalo | `FREQ=WEEKLY;INTERVAL=2`, apos=semana 0 | +14 dias |
| Fim por data | `FREQ=DAILY;UNTIL=<ontem>` | `None` |
| Fim por contagem | `FREQ=DAILY;COUNT=1`, apos=dtstart | `None` |
| RRULE inválida | `FREQ=BANANA` | `validar_regra` levanta; API 422 |
| Reprocesso | worker processa a mãe 2× | 1 só filha (ON CONFLICT) |
| Avulso | `recorrencia=NULL` | nenhuma filha criada |
| cancelar-serie | mãe + 2 futuras pendentes + 1 enviada | 2 viram `cancelado`; enviada intacta |

## Fora de escopo (vinculante — ver product.md)
Envio real/número +55 (adiado); anexos DOCUMENT; texto livre/janela 24 h; telas do PWA; edição de série e
exceções ("pular esta ocorrência"); sugestões de recorrência pela IA. Cancelar uma ocorrência **isolada**
continua sendo o `POST /{id}/cancelar` da 0004.
