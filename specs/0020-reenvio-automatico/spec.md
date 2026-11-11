---
name: spec-reenvio-automatico
description: Spec da feature 0020 Reenvio automático de envios com falha transitória. AC são o contrato e o oráculo de teste.
---

# Spec: Reenvio automático de envios (falha transitória)

## Contexto
Hoje um `envio` que falha é terminal (`disparo.py:357-367`); um blip transitório nosso→Meta faz a mensagem
agendada não sair. Esta feature reenvia **só o que comprovadamente não entregou**, preservando o at-most-once
(§5.2). Decisões em `product.md`/`design.md`; irreversível em **ADR 0014**. Tier Arquitetural; §4 aprovada.

## Classificação da falha (contrato — cada linha vira teste)
| Origem da falha | Classe | Destino no disparo |
|---|---|---|
| HTTP **429**; `httpx.ConnectError` (antes do request); código Meta na **allowlist** de temporários | **retentável** | `aguardando_retry` (se `tentativas<3`) |
| **5xx** após resposta; `httpx.TimeoutException`; órfão preso em `enviando` | **ambíguo** | `aguardando_decisao` |
| número inválido / não-usuário / descadastrado / template rejeitado (demais códigos) | **definitivo** | `falhou` |

> A allowlist de códigos Meta é montada com **/meta-whatsapp** + doc oficial (§1 — sem inventar código).

## Critérios de aceite (Given/When/Then)

### Classificação (client)
**AC-1 — Transporte pré-request é retentável.**
Given o envio à Meta levanta `httpx.ConnectError`,
When o client processa,
Then levanta `WhatsappError` com **classe `retentavel`** (nada foi entregue).

**AC-2 — Timeout/5xx é ambíguo.**
Given `httpx.TimeoutException` **ou** resposta HTTP 5xx após os 3 tiros,
When o client processa,
Then levanta `WhatsappError` com **classe `ambiguo`**.

**AC-3 — Código Meta definitivo não é retentável.**
Given a Meta devolve um código **fora** da allowlist (ex.: número inválido),
When o client processa,
Then levanta `WhatsappError` com **classe `definitivo`**.

**AC-4 — Código Meta temporário (allowlist) é retentável.**
Given a Meta devolve um código **na allowlist** de temporários,
When o client processa,
Then levanta `WhatsappError` com **classe `retentavel`**.

### Agendamento do reenvio (disparo)
**AC-5 — Falha retentável agenda o próximo reenvio.**
Given um envio falha com classe `retentavel` e `tentativas < 3`,
When o disparo trata,
Then status → `aguardando_retry`, `tentativas += 1`, `proxima_tentativa_em = agora + BACKOFF[tentativas]`
(`{1:5min, 2:15min, 3:1h}`), e grava auditoria `envio.retry_agendado` (sem PII).

**AC-6 — Esgotadas as 3 tentativas → decisão humana.**
Given um envio falha com classe `retentavel` e `tentativas == 3`,
When o disparo trata,
Then status → `aguardando_decisao` + alerta `envio.retry_esgotado`.

**AC-7 — Falha ambígua vai direto para decisão humana.**
Given um envio falha com classe `ambiguo`,
When o disparo trata,
Then status → `aguardando_decisao` (sem auto-retry) + alerta `envio.falha_ambigua`.

**AC-8 — Falha definitiva permanece `falhou`.**
Given um envio falha com classe `definitivo`,
When o disparo trata,
Then status → `falhou` + alerta (comportamento atual, inalterado).

### Execução do reenvio (worker)
**AC-9 — Reenvio no horário, na mesma linha.**
Given um envio `aguardando_retry` com `proxima_tentativa_em <= agora`,
When o worker roda o passo de reenvio (`FOR UPDATE SKIP LOCKED`),
Then **reenvia na mesma linha** (não cria 2ª); sucesso → `enviado`+`wamid`; falha → volta ao balde (AC-5/6/7).

**AC-10 — Reenvio futuro não dispara.**
Given um envio `aguardando_retry` com `proxima_tentativa_em > agora`,
When o worker roda,
Then **não** reenvia (aguarda o horário).

**AC-11 — Reavaliar elegibilidade no reenvio.**
Given um envio `aguardando_retry` cujo contato **descadastrou** (ou janela fechou) após a 1ª tentativa,
When o worker tenta reenviar,
Then **não** envia; status → `falhou` com motivo (descadastro respeitado, §5.4).

### Sweep de órfãos
**AC-12 — Órfão `enviando` preso é recolhido.**
Given um envio `enviando` sem `wamid` com idade `> MARGEM_ORFAO` (15 min),
When o worker roda o sweep,
Then status → `aguardando_decisao` + alerta `envio.orfao_detectado`.

**AC-13 — Envio em voo não é recolhido.**
Given um envio `enviando` recente (`< MARGEM_ORFAO`),
When o sweep roda,
Then **não** é tocado (não pega envio em andamento).

### Decisão humana por envio
**AC-14 — Reenvio manual reabre o envio.**
Given um operador autenticado chama `POST /envios/{id}/reenviar` num envio `aguardando_decisao`,
When processa,
Then status → `aguardando_retry`, `tentativas = 0`, `proxima_tentativa_em = agora`, auditoria `envio.reenvio_manual` (com `ator_email`).

**AC-15 — Reenvio manual só em `aguardando_decisao`.**
Given o envio **não** está `aguardando_decisao`,
When `POST /envios/{id}/reenviar`,
Then **409** (estado inválido), sem mudança.

**AC-16 — Endpoint exige autenticação.**
Given sem sessão válida,
When `POST /envios/{id}/reenviar`,
Then **401**.

### Invariantes e observabilidade
**AC-17 — At-most-once preservado.**
Given qualquer caminho de reenvio,
When executa,
Then **nunca** há 2ª linha de envio para `(agendamento, contato)` e **nunca** se reenvia classe `ambiguo`/`definitivo` (só certeza de não-entrega).

**AC-18 — Taxa da 0019 enxerga os status novos.**
Given envios em `aguardando_retry` e `aguardando_decisao` nas últimas 24 h,
When a 0019 computa a taxa,
Then `aguardando_retry` conta como **tentativa** (não falha) e `aguardando_decisao` conta como **falha**.

**AC-19 — Reenvio respeita o teto por-agendamento (0016).**
Given o teto do agendamento já foi atingido,
When um reenvio ocorreria,
Then o reenvio **conta** no teto e não o ultrapassa.

## Matriz de decisão — classe × tentativas (cada linha = teste)
| classe | tentativas | resultado |
|---|---|---|
| retentável | < 3 | `aguardando_retry` (agenda) |
| retentável | == 3 | `aguardando_decisao` (esgotou) |
| ambíguo | qualquer | `aguardando_decisao` |
| definitivo | qualquer | `falhou` |

## Casos de borda
- Reenvio cujo contato ficou inelegível → `falhou` (não envia).
- Sweep nunca pega envio `< 15 min` (evita duplicar envio em voo); margem ≫ timeout do client (30 s).
- Virada de dia não afeta o retry (cadência ~1h20, independe de dia-calendário).
- Concorrência: `FOR UPDATE SKIP LOCKED` no passo de reenvio e no sweep (nenhum envio pego por 2 ciclos).
- Reenvio manual zera `tentativas` (novo ciclo completo de 3).

## Fora de escopo (vinculante)
- Reenvio de falha de **entrega** reportada pela Meta via webhook e de erro **definitivo**.
- Retry de longa duração (horas/dias); fila/broker externo.
- Mudar o retry HTTP nosso→Meta (3×/backoff no `whatsapp_client`) — já existe.
- Decisão humana em **lote/agendamento** (a decisão é por envio).

## Definition of Ready
- [x] AC testáveis (pytest: client com `MockTransport`; disparo/worker com PostgreSQL real + `enviar` fake; API com `TestClient`). Non-goals explícitos. **Migração aditiva** (/migracao). Allowlist Meta via /meta-whatsapp. §4 aprovada (ADR 0014).
