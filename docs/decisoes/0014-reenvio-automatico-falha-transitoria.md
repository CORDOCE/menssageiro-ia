# ADR 0014 — Reenvio automático de envios com falha transitória (at-most-once)

- **Status:** aceito
- **Data:** 2026-11-11
- **Contexto da feature:** `specs/0020-reenvio-automatico`; regra fechada na sabatina `/clarificar` de 2026-11-11
  (Q1–Q7, ver `specs/0020-reenvio-automatico/clarificar.md`).
- **Aprovação:** é mudança em **regra de envio** e evolui a invariante §5.2 (CLAUDE.md §4/§5) — **aprovada por
  Jefferson** ("ok", 2026-11-11).

## Contexto
Um `envio` que falha vira `falhou` **terminal**; o worker não o reprocessa (invariante §5.2 at-most-once;
`disparo.py:345,357-367`). Quando a falha foi um **blip transitório** nosso→Meta que não se recuperou nos 3 tiros
HTTP do `whatsapp_client` (`whatsapp_client.py:123-138`), a mensagem agendada **não sai** e o operador só vê
depois. Falta recuperação automática — **sem** reintroduzir risco de entrega dupla.

## Decisão
1. **§5.2 evolui, at-most-once preservado.** Uma falha de envio **com certeza de não-entrega** deixa de ser
   terminal: o envio entra em ciclo de reenvio na **mesma linha** (`(agendamento, contato)` continua único). A
   garantia "nunca entregar 2x ao mesmo contato" é mantida porque só se reenvia o que comprovadamente **não**
   entregou.
2. **Três baldes de falha** (Q4+Q7+Q9):
   - **Retentável** (certeza de não-entrega): HTTP **429**, **`ConnectError`/DNS antes do request**, allowlist
     curta de códigos Meta temporários-e-de-não-entrega (/meta-whatsapp + doc). → auto-retry.
   - **Ambíguo** (pode ter entregue): `5xx`/**timeout após o request**, **órfão** preso em `enviando` (crash).
     → `aguardando_decisao` direto, **sem** auto-retry (duplicaria, veda §5.2/Q7); humano decide.
   - **Definitivo** (número inválido, não-usuário, descadastrado, template rejeitado): → `falhou` terminal.
3. **Cadência limitada** (Q2): até **3 reenvios**, backoff `{1: +5min, 2: +15min, 3: +1h}`. Campos novos em
   `envios`: `tentativas` (int) e `proxima_tentativa_em` (timestamptz). Status novo `aguardando_retry`.
4. **Reavaliar elegibilidade a cada reenvio** (§5.4/§5.9/§5.3): consentimento, descadastro e janela/template
   checados no momento de retentar — contato que saiu nesse meio não recebe.
5. **Decisão humana por envio** (Q5/Q5b/Q9): esgotou o auto-retry **ou** falha ambígua → status novo
   `aguardando_decisao` **na linha do envio** + endpoint `POST /envios/{id}/reenviar` (autenticado) + botão no
   Histórico. Reusar o `aguardando_decisao` do agendamento foi rejeitado (a idempotência `(agendamento, contato)`
   bloquearia re-disparar só o contato que falhou; em grupo pausaria o agendamento todo).
6. **Sweep de órfãos** (ataque ao buraco latente): novo passo do worker recolhe `enviando` sem `wamid` preso além
   de uma margem conservadora (≫ timeout 30s; proposta 15min, configurável) → `aguardando_decisao` (ambíguo) +
   alerta. Conserta um bug pré-existente (hoje `ConnectError`/`TimeoutException` propagam e deixam órfão).
7. **Contagem/observabilidade** (Q6/Q8): `aguardando_retry` entra em `_CONTAM_LIMITE` — conta para os tetos
   (0016) e para "tentativas" da 0019, **sem** falha; `aguardando_decisao` **conta como falha** na taxa da 0019
   (Q8). Eventos `envio.retry_agendado` / `envio.retry_esgotado` / `envio.falha_ambigua` / `envio.orfao_detectado`
   (alertam via `alertar_evento`), sem PII.

## Alternativas
- **At-least-once (reenviar 5xx/timeout):** recupera mais blips, mas pode **entregar 2x** quando a Meta processou
  e só escondeu o `wamid` — enfraquece §5.2. Rejeitado (Q7).
- **Tabela de tentativas separada:** histórico por tentativa, mas duplica estado e complica
  locking/idempotência do worker. Rejeitado (Q3).
- **Fila/broker externo de retry:** robusto, porém nova infra/dependência desproporcional ao volume. Fora de escopo.
- **Decisão humana no agendamento** (reusar fluxo existente): esbarra na idempotência por contato. Rejeitado (Q5b).

## Consequências
- Toca o **worker** (passo de reenvio + **passo de sweep de órfãos**, ambos `FOR UPDATE SKIP LOCKED`; refatorar
  "enviar-1-contato + aplicar desfecho" em `disparo.py:331-367` num helper reusável — reenvio não re-reserva), o
  **client** (classificar a falha em retentável/ambíguo/definitivo + capturar `ConnectError`/`TimeoutException`,
  hoje não capturadas), a **API** (`POST /envios/{id}/reenviar`) e a **UI** (botão no Histórico). Mapear todos os
  pontos de status para não deixar `aguardando_retry`/`aguardando_decisao` órfãos.
- **Dependência da 0019:** a 0019 entra antes e não conhece os status novos; **task da 0020 atualiza a 0019** —
  `aguardando_retry` nas tentativas (não-falha, Q6) e `aguardando_decisao` nas falhas (Q8).
- **Migração aditiva** (duas colunas + default) com downgrade trivial (/migracao).
- **Limitação conhecida (aceita):** 5xx/timeout ambíguo não é recuperado automaticamente — cai em
  `aguardando_decisao` para reenvio manual (o humano assume o risco de duplicata, cientemente).
- Mudar a regra (cadência, allowlist, tetos de tentativa) exige **§4**.
