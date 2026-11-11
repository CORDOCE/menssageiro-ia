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
2. **Retentável = certeza de não-entrega** (Q4+Q7): HTTP **429** (limite), **falha de conexão antes do request**,
   e uma **allowlist curta** de códigos Meta temporários-e-de-não-entrega (montada com /meta-whatsapp + doc
   oficial). **Não retentável:** `5xx`/timeout após o request (ambíguo → poderia duplicar) e todo erro definitivo.
3. **Cadência limitada** (Q2): até **3 reenvios**, backoff `{1: +5min, 2: +15min, 3: +1h}`. Campos novos em
   `envios`: `tentativas` (int) e `proxima_tentativa_em` (timestamptz). Status novo `aguardando_retry`.
4. **Reavaliar elegibilidade a cada reenvio** (§5.4/§5.9/§5.3): consentimento, descadastro e janela/template
   checados no momento de retentar — contato que saiu nesse meio não recebe.
5. **Esgotou → decisão humana por envio** (Q5/Q5b): status novo `aguardando_decisao` **na linha do envio** +
   endpoint `POST /envios/{id}/reenviar` (autenticado) + botão no Histórico. Reusar o `aguardando_decisao` do
   agendamento foi rejeitado (a idempotência `(agendamento, contato)` bloquearia re-disparar só o contato que
   falhou; em grupo pausaria o agendamento todo).
6. **Contagem/observabilidade** (Q6): `aguardando_retry` entra em `_CONTAM_LIMITE` — conta para os tetos (0016) e
   para o denominador de "tentativas" da 0019, **sem** contar como falha até esgotar. Eventos de auditoria
   `envio.retry_agendado` / `envio.retry_esgotado` (este alerta via `alertar_evento`), sem PII.

## Alternativas
- **At-least-once (reenviar 5xx/timeout):** recupera mais blips, mas pode **entregar 2x** quando a Meta processou
  e só escondeu o `wamid` — enfraquece §5.2. Rejeitado (Q7).
- **Tabela de tentativas separada:** histórico por tentativa, mas duplica estado e complica
  locking/idempotência do worker. Rejeitado (Q3).
- **Fila/broker externo de retry:** robusto, porém nova infra/dependência desproporcional ao volume. Fora de escopo.
- **Decisão humana no agendamento** (reusar fluxo existente): esbarra na idempotência por contato. Rejeitado (Q5b).

## Consequências
- Toca o **worker** (novo passo de reenvio com `FOR UPDATE SKIP LOCKED`; refatorar "enviar-1-contato + aplicar
  desfecho" em `disparo.py:331-367` num helper reusável — reenvio não re-reserva), o **client** (sinalizar
  `retentavel` na falha + capturar conexão pré-request, hoje não capturada), a **API** (`POST /envios/{id}/reenviar`)
  e a **UI** (botão no Histórico). Mapear todos os pontos de status para não deixar `aguardando_retry`/
  `aguardando_decisao` órfãos.
- **Dependência da 0019:** a 0019 entra antes e não conhece `aguardando_retry`; **task da 0020 atualiza a
  definição de "tentativa" da 0019** (incluir em `_CONTAM_LIMITE`). Proposta a confirmar: `aguardando_decisao`
  (esgotado) conta como **falha** na taxa.
- **Migração aditiva** (duas colunas + default) com downgrade trivial (/migracao).
- **Limitação conhecida (aceita):** 5xx/timeout ambíguo não é recuperado automaticamente — cai em
  `aguardando_decisao` para reenvio manual (o humano assume o risco de duplicata, cientemente).
- Mudar a regra (cadência, allowlist, tetos de tentativa) exige **§4**.
