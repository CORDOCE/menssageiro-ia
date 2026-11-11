---
name: design-reenvio-automatico
description: Design doc da feature 0020 Reenvio automático (Tier Arquitetural). Solução, alternativas, trade-offs. Decisão irreversível → ADR 0014.
---

# Design: Reenvio automático de envios (falha transitória)

> Decisões de escopo em `clarificar.md` (Q1–Q7). Respeita a arquitetura atual do worker/disparo (ADR 0008).

## Solução proposta

### 1. Esquema (migração aditiva — sem destrutivo)
Em `envios` (reusa a linha — **Q3**; mantém 1 linha por `(agendamento, contato)`, §5.2):
- `tentativas INT NOT NULL DEFAULT 0` — nº de **reenvios** já feitos (0 = só o envio original).
- `proxima_tentativa_em TIMESTAMPTZ NULL` — quando o worker deve retentar.
- Dois valores novos de status (coluna já é `String(20)`; só atualizar o enum em `schemas/envio.py:17-22`):
  `aguardando_retry` (retentar depois) e `aguardando_decisao` (esgotou → humano).

### 2. Classificar a falha em 3 baldes (Q4 + Q7 at-most-once + Q9)
| Balde | O que é | Destino |
|---|---|---|
| **Retentável** (certeza de não-entrega) | HTTP **429** (limite); **`ConnectError`/DNS antes do request** (nenhum byte enviado); **allowlist curta** de códigos Meta temporários-e-de-não-entrega (via /meta-whatsapp + doc) | **auto-retry** (passo 3) |
| **Ambíguo** (pode ter entregue) | `5xx`/**timeout após o request** (`TimeoutException`); **órfão** preso em `enviando` (crash no meio) | **`aguardando_decisao`** — humano decide reenviar ciente do risco (Q9); **sem** auto-retry (§5.2/Q7) |
| **Definitivo** | número inválido, não-usuário WhatsApp, descadastrado, template rejeitado | **`falhou`** terminal (como hoje) |

Mecânica: o `whatsapp_client` passa a sinalizar na falha a **classe** (ex.: `classe: retentavel|ambiguo|definitivo`
em `WhatsappError`, derivada do status HTTP / tipo de exceção). Hoje `WhatsappError` só carrega `codigo`/`motivo`
(`whatsapp_client.py:22`) e **conexão/timeout não são capturados** (propagam — por isso o órfão existe hoje); a
task passa a capturar `httpx.ConnectError` (→ retentável) e `httpx.TimeoutException` (→ ambíguo).

### 3. Agendar o reenvio (Q2 — até 3x, backoff curto)
No ponto de falha do disparo (`disparo.py:357-367`), pelo balde (passo 2):
- **Retentável** e `tentativas < 3`: status → `aguardando_retry`, `tentativas += 1`,
  `proxima_tentativa_em = agora + BACKOFF[tentativas]` com `BACKOFF = {1: 5min, 2: 15min, 3: 1h}`;
  auditoria `envio.retry_agendado` (sem PII).
- **Retentável** e `tentativas == 3` (esgotou): status → `aguardando_decisao` + auditoria/alerta
  `envio.retry_esgotado` (`alertar_evento`, warning). **Q5/Q5b.**
- **Ambíguo**: status → `aguardando_decisao` direto (sem auto-retry) + alerta `envio.falha_ambigua`. **Q9.**
- **Definitivo**: `falhou` + alerta (comportamento atual).

### 4. Executar o reenvio (novo passo do worker)
A cada ciclo (`__main__.py` `executar()`), um novo passo seleciona
`status='aguardando_retry' AND proxima_tentativa_em <= agora` com **`FOR UPDATE SKIP LOCKED`** (padrão §5.2/ADR
0008). Para cada envio: **reavaliar elegibilidade** (consentimento/descadastro/janela — reusa `_motivo_inelegivel`,
`disparo.py:323`); se inelegível agora → `falhou` com motivo (descadastro respeitado, §5.4); se elegível → reenvia
pelo mesmo caminho de envio e aplica o desfecho (sucesso→`enviado`; falha→volta ao passo 3). Refatorar o
"enviar-1-contato + aplicar desfecho" (`disparo.py:331-367`) num helper reusável (o reenvio **não** re-reserva —
a linha já existe).

### 4b. Sweep de órfãos `enviando` (fecha buraco latente de hoje)
Hoje um `ConnectError`/`TimeoutException` no envio **propaga** (não vira `WhatsappError`) → sobe ao
`except Exception` do ciclo (`__main__.py:58`) e o envio fica **preso em `enviando`** para sempre (sem reaper —
`grep` confirmou). Mesmo capturando essas exceções (passo 2), um **crash do worker** entre a reserva
(`disparo.py:336`, commit `enviando`) e a gravação do desfecho ainda deixa órfão.

Novo passo do worker a cada ciclo: seleciona `status='enviando' AND wamid IS NULL` com idade
`> MARGEM_ORFAO` (conservadora: **muito maior** que o timeout do client de 30s + 1 ciclo, p/ nunca pegar um envio
**em voo**; proposta: **15 min**, configurável) e os move para **`aguardando_decisao`** (balde **ambíguo** — o
worker pode ter caído *depois* de a Meta entregar; não auto-retenta, §5.2) + alerta `envio.orfao_detectado`.
Isso conserta um bug pré-existente de graça, dentro desta feature.

### 5. Decisão humana por envio (Q5b)
Novo endpoint autenticado `POST /envios/{id}/reenviar`: exige `status == 'aguardando_decisao'` (409 senão), zera
`tentativas`, status → `aguardando_retry`, `proxima_tentativa_em = agora`, auditoria `envio.reenvio_manual` com
`ator_email`. Botão "Reenviar" na tela **Histórico** (só quando `aguardando_decisao`). Molde: o
`POST /agendamentos/{id}/reenviar` existente (`agendamentos.py:112-131`).

### 6. Limites e observabilidade
- `aguardando_retry` entra em **`_CONTAM_LIMITE`** (`disparo.py:46`): conta para os tetos (0016) — é um envio
  reservado/pretendido — **e** para o denominador de "tentativas" da 0019 (**Q6**), sem contar como falha.
- **Dependência 0019:** a 0019 vai a produção antes; task da 0020 **atualiza a definição da 0019** — incluir
  `aguardando_retry` nas **tentativas** (não-falha, Q6) e `aguardando_decisao` nas **falhas** (Q8, confirmado:
  não-entrega real aguardando humano).

## Alternativas consideradas
| opção | prós | contras | veredito |
|---|---|---|---|
| A (escolhida) reusar linha + at-most-once estrito | §5.2 intacta (nunca entrega 2x), migração aditiva, menos código | recupera menos blips (5xx/timeout não reenvia) | **escolhida (Q3+Q7)** |
| Tabela de tentativas separada | histórico rico por tentativa | duplica estado, complica locking/idempotência | rejeitada (Q3) |
| At-least-once (reenvia 5xx) | recupera o máximo | entrega dupla possível → enfraquece §5.2 | rejeitada (Q7) |
| Fila/broker externo (retry infra) | robusto, desacoplado | nova dependência/infra, § exagero p/ o volume | fora de escopo |

## Trade-offs e riscos
- **Recupera menos automaticamente** (ambíguo vai p/ decisão humana, não auto-retry) — preço do at-most-once (Q7/Q9).
- **Órfão `enviando` — ATACADO**: (a) o client passa a capturar `ConnectError`→retentável e `TimeoutException`→
  ambíguo; (b) o **sweep** (passo 4b) recolhe qualquer `enviando` preso (inclui crash) p/ `aguardando_decisao`.
  Fecha um bug **pré-existente**. Riscos do próprio sweep: **não** pegar envio em voo (margem 15min ≫ timeout 30s)
  e idempotência sob concorrência (`FOR UPDATE SKIP LOCKED`). Testes de borda explícitos.
- **Reavaliar elegibilidade no reenvio** é obrigatório (§5.4/§5.9): contato que saiu entre o 1º envio e o reenvio
  não pode receber. Caso de ataque/borda → teste.
- **Interação com teto 0016**: cada reenvio conta; não pode ultrapassar o teto por-agendamento/contato.
- **Janela/template (§5.3)**: reenvio continua template UTILITY aprovado; backoff máx ~1h20 não estoura validade.

## Decisões irreversíveis (→ ADR 0014)
- Evoluir a invariante **§5.2**: falha transitória **com certeza de não-entrega** deixa de ser terminal e entra
  em ciclo de reenvio limitado na **mesma linha**; at-most-once preservado. (ADR 0014, aprovação §4 dada.)
