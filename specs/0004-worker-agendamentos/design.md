---
name: design-worker-agendamentos
description: Design doc da Fase 4 — núcleo do disparo (0004-worker-agendamentos, tier arquitetural). Modelo Agendamento, configuração de envio, worker de disparo idempotente. Implementa ADR 0005 + BRIEFING §9/§10.3. Alternativas, trade-offs, riscos e ADR 0008.
---

# Design: Worker de disparo + agendamentos — núcleo (Fase 4)

> **Fontes internas (contrato já aprovado):** ADR 0005 (expansão de grupo, idempotência por contato,
> consentimento, ciclo de status), BRIEFING §9 (schema `agendamentos`/`envios`/`configuracoes`), §10.3
> (algoritmo do worker), CLAUDE.md §5 (invariantes). **Nenhuma regra de envio nova** — só implementação.
> Sem API externa nova: `enviar_template` (Fase 3) já fala com a Meta; testes com **mocks** (§5.7).

## Solução proposta
Respeitar a arquitetura existente: SQLAlchemy 2 (`Mapped`/`mapped_column`), routers em `app/api` com
`Depends(usuario_atual)`, schemas Pydantic v2, migrações Alembic com `downgrade`, worker como processo
separado (`python -m app.worker`) sem estado em memória (§5 / BRIEFING §5.2). **Sem dependência nova**
(janela/fuso via `datetime` + `zoneinfo`; `httpx` já existe; RRULE/`python-dateutil` fica para a 0005).

### Modelos (novos) + migração aditiva
- **`agendamentos`** (`app/models/agendamento.py`):
  - `id` (uuid String(36) PK), `contato_id` (FK `contatos.id`, nullable) **xor** `grupo` (String(255),
    nullable) — **CHECK** `(contato_id IS NOT NULL) <> (grupo IS NOT NULL)` garante exatamente um.
  - `modelo_id` (FK `modelos.id`, **not null**), `variaveis` (JSONB, default `[]` — valores do corpo).
  - `executar_em` (timestamptz, **not null, index** — o worker filtra os vencidos).
  - `status` (String(20), default `aprovado`): ciclo 0004 = `aprovado`→`enviando`→`enviado`/`falhou`,
    `cancelado`, `aguardando_decisao`. `adia`/`reagenda` **não** mudam status (continuam `aprovado`, só mexem
    em `executar_em` — ADR 0005 §4).
  - `origem` (String(20), default `operador`), `criado_por` (FK `usuarios.id`), `aprovado_por` (nullable).
  - `motivo_ultima_transicao` (Text, nullable), `reagendamentos` (Integer, default 0).
  - **Colunas inertes p/ forward-compat (ADR 0005: "definir antes das migrations → sem retrabalho"):**
    `agendamento_pai_id` (String(36), nullable) e `recorrencia` (Text, nullable). **Sem lógica em 0004**; o
    `UNIQUE(agendamento_pai_id, executar_em)` e a expansão entram na **0005**. *(Decisão em aberto — ver Q5.)*
  - `criado_em`/`atualizado_em` (timestamptz). **`anexo_id` fica fora** (não há tabela de anexos ainda).
- **`configuracoes`** (`app/models/configuracao.py`, **linha única**): `id` fixo (`"default"`),
  `janela_envio` (JSONB: `{"dias":[0..5],"inicio":"08:00","fim":"20:00"}`, `dias` em `weekday()` 0=seg),
  `limite_diario` (Integer, default 200), `limite_por_contato_dia` (Integer, **nullable, default `NULL` = sem
  limite** — /clarificar 2026-11-04), `envios_pausados` (Boolean, default false), `atualizado_em`. O worker
  lê/cria essa linha **a cada ciclo** (§5.6).
- **FK `envios.agendamento_id`**: hoje é `String(36)` nullable com índice único **parcial** `(agendamento_id,
  contato_id) WHERE agendamento_id IS NOT NULL` (Fase 3). A migração **adiciona a FK** → `agendamentos.id`
  (mantém nullable: avulsos/teste têm `NULL`). O índice parcial **já é** a trava de idempotência da ADR 0005.

### Worker de disparo (`app/worker/disparo.py`, chamado por `executar()` a cada ciclo)
Ordem por ciclo (estende o heartbeat atual, que continua gravando `Saude.ultimo_ciclo_em`):
1. **Configuração:** carrega/cria o singleton `configuracoes`. `envios_pausados` → **não dispara** nada
   (só heartbeat). *(§5.6: checado a cada ciclo.)*
2. **Indisponibilidade:** lê o `ultimo_ciclo_em` **antes** de atualizar; se o gap até agora `>` `2×intervalo`
   → `houve_gap=True`.
3. **`aguardando_decisao`:** agendamentos em `aprovado`/`enviando` com `executar_em < agora−2h` **e**
   `houve_gap` → `aguardando_decisao` + motivo (ADR 0005 §4). Atraso **sem** gap segue o fluxo normal.
4. **Seleção:** `SELECT … FROM agendamentos WHERE status='aprovado' AND executar_em<=now() ORDER BY
   executar_em FOR UPDATE SKIP LOCKED LIMIT <lote>` (§5.2 — trava e pula os já travados).
5. **Por agendamento** (dentro da transação que o travou):
   - **Janela de horário** (agora em `America/Sao_Paulo`): fora da janela → **reagenda** `executar_em` p/ o
     próximo início de janela, `reagendamentos += 1`, motivo, **mantém `aprovado`**, segue.
   - **Modelo:** `modelo.status != 'aprovado'` → `falhou` + motivo + alerta, segue.
   - **Limite diário:** conta `envios` enviados nas últimas 24 h; `>= limite_diario` → **adia** `executar_em`,
     mantém `aprovado`, motivo, segue.
   - `status = 'enviando'`. **Destinatários:** `contato_id` → `[contato]`; `grupo` → todos os `contatos` com
     aquele `grupo` **no momento do disparo** (grupo dinâmico, ADR 0005).
   - **Por contato (elegibilidade):** `descadastrado_em` não nulo (§5.4) → pula; `consentimento=false` (§5.9)
     → pula; `limite_por_contato_dia` **configurado (não nulo)** e estourado → pula. Pulos → auditoria (motivo).
   - **Reserva idempotente:** `INSERT INTO envios(agendamento_id, contato_id, status='enviando') … ON CONFLICT
     DO NOTHING`. Se já existia linha (conflito) → **não reenvia** (§5.2: nunca duas vezes ao mesmo contato,
     nem após reinício).
   - **Envio:** `enviar_template(contato.telefone_e164, modelo.nome, modelo.idioma, componentes, client=lote)`
     com `componentes = [{"type":"body","parameters":[{"type":"text","text":v} for v in variaveis]}]`
     (só-texto; anexo/DOCUMENT → spec seguinte). Sucesso → grava `wamid`, `status='enviado'`. `WhatsappError`
     definitivo → `status='falhou'` + `erro_codigo`/`erro_motivo`.
   - **Auditoria** por envio (§5.8, telefone mascarado via `mascarar_telefone`), `correlation_id = agendamento_id`.
   - Todos os contatos processados → agendamento `status='enviado'`.
6. **Heartbeat** (grava `ultimo_ciclo_em`).

### API mínima (`app/api/agendamentos.py`, `Depends(usuario_atual)`) — §5.1: só registra, não envia
- `POST /agendamentos` (201): `{contato_id xor grupo, modelo_id, variaveis, executar_em, origem?}`; valida
  xor, modelo existe, `executar_em` presente; `status='aprovado'`, `criado_por=usuário atual`.
- `GET /agendamentos`: lista (filtros simples opcionais).
- `POST /agendamentos/{id}/cancelar`: `status='cancelado'` se não terminal.
- `POST /agendamentos/{id}/reenviar`: **só** a partir de `aguardando_decisao` → `status='aprovado'`,
  `executar_em=agora`, motivo (resolve o estado — /clarificar 2026-11-04). *(Cancelar também resolve.)*

## Alternativas consideradas
| Opção | Prós | Contras | Veredito |
|---|---|---|---|
| **`configuracoes` tabela linha-única** | operador muda janela/limite/pausa **sem redeploy** (§5.6) | 1 tabela a mais | **Escolhida (→ ADR)** |
| `limite_diario`/janela só em env | zero schema | exige redeploy p/ mudar; fura BRIEFING §9 | Descartada |
| **`limite_diario` na tabela; env só semeia o default** | fonte única runtime; resolve conflito §4.5×§9 | precisa seed inicial | **Escolhida (→ ADR)** |
| **Reserva-depois-envia (`ON CONFLICT DO NOTHING`) + at-most-once** | honra §5.2 (nunca duplica) mesmo em crash | mensagem rara pode se perder (linha órfã `enviando` sem `wamid`) → exposta ao operador | **Escolhida (→ ADR)** |
| Envia-depois-grava | não perde mensagem | **duplica** ao reiniciar no meio do envio (fura §5.2) | Descartada |
| Outbox/lock distribuído | exactly-once mais forte | infra/complexidade; volume é dezenas/dia | Descartada (overkill) |
| **Grupo dinâmico no disparo** | reflete quem está no grupo na hora (ADR 0005) | grupo muda entre agendar e enviar | **Escolhida** (é a ADR) |
| Snapshot do grupo ao agendar | previsível | contraria ADR 0005; perde entradas/saídas | Descartada |
| **Colunas inertes (`agendamento_pai_id`,`recorrencia`) já** | evita 2ª migração em `agendamentos` (ADR 0005) | colunas sem uso em 0004 | **Escolhida** (Q5) |
| **Disparo no mesmo loop do heartbeat** | sem serviço novo; volume pequeno | API/worker no mesmo código | **Escolhida** (revisitar se crescer) |

## Trade-offs e riscos
- **At-most-once consciente (§5.2 > entrega):** preferimos **não duplicar** a garantir entrega. Linha de
  `envios` em `enviando` sem `wamid` após crash = ambígua → **não reenviada**, fica visível ao operador
  (tela/consulta). A resolução manual fina fica para spec/tela posterior.
- **Fuso/janela:** comparar sempre em `America/Sao_Paulo` (`zoneinfo`), gravar `timestamptz` (§8). Teste de
  borda no limite da janela (20:00) e virada de dia/semana.
- **`aguardando_decisao`** depende de ler o heartbeat **anterior** antes de sobrescrevê-lo; cobrir com teste
  que simula gap. Atraso sem gap **não** deve ir para `aguardando_decisao` (contraexemplo explícito).
- **Contagem do limite diário** = janela deslizante de 24 h sobre `envios` enviados; custo baixo (dezenas/dia).
- **Sem Meta real nos testes** (§5.7): mock de `enviar_template`/`httpx`; validação real só quando a conta de
  teste (Fase 0) for desbloqueada — **não bloqueia** esta spec.
- **Concorrência:** `FOR UPDATE SKIP LOCKED` + reserva por `ON CONFLICT` tornam seguro rodar mais de um worker;
  rodamos 1 réplica (RAILWAY.md §5), mas o código não pode depender disso.

## Decisões irreversíveis (→ ADR 0008 proposto)
- **ADR 0008 — Disparo do worker: configuração, idempotência e janela.**
  (a) **`configuracoes`** linha-única como **fonte runtime** da janela/limite/pausa (§5.6); `limite_diario`
  mora nela — a env `LIMITE_DIARIO` vira, no máximo, **semente** do default (resolve o conflito BRIEFING
  §4.5 × §9). (b) **Idempotência**: `UNIQUE(agendamento_id, contato_id)` + **reserva-antes-de-enviar**; a
  invariante é **at-most-once por (agendamento, contato)** — linha existente após reinício **nunca** é
  reenviada (§5.2 tem precedência sobre entrega). (c) **`janela_envio`** como JSONB (dias + início/fim),
  comparado em `America/Sao_Paulo`. Difícil de reverter: define o schema de `agendamentos`/`configuracoes`
  e a semântica de envio do worker.

## Decisões fechadas (/clarificar 2026-11-04)
1. **`limite_diario` na `configuracoes`**; env `LIMITE_DIARIO` só semeia o default. *(resolve §4.5×§9)*
2. **`limite_por_contato_dia` default `NULL` = sem limite**; worker só aplica se o operador configurar.
3. **`aguardando_decisao`: detectar + resolver na API** — endpoints `reenviar` (→`aprovado`) e `cancelar` na 0004.
4. **reagenda** → próximo início de janela válida; **adia** (limite diário) → início da janela do **dia seguinte**.
5. **Colunas inertes** `agendamento_pai_id`/`recorrencia` **entram na migração 0004** (sem lógica), evitando 2ª migração.

## Questões para /clarificar (gate da spec)
1. **`limite_diario`** confirmado na `configuracoes` (recomendado), env só como semente? *(resolve §4.5×§9)*
2. **`limite_por_contato_dia`** default (proposta: **1** — uma mensagem por contato por dia; BRIEFING não fixa p/ envios).
3. **`aguardando_decisao`:** 0004 só **detecta e move**; resolução (reenviar→`aprovado`/cancelar via tela) fica depois? (recomendado).
4. **reagenda/adia:** regra exata do "próximo início de janela" e do atraso do `adia` (proposta: reagenda→próximo início; adia→próximo início do dia seguinte dentro da janela).
5. **Colunas inertes** `agendamento_pai_id`/`recorrencia` já na migração 0004 (recomendado, evita 2ª migração) ou só na 0005?
