# ADR 0007 — Integração WhatsApp Cloud API (cliente, webhook, envios por `wamid`)

- **Status:** aceito
- **Data:** 2026-11-03
- **Contexto da feature:** `specs/0003-whatsapp-cloud-api/` (design.md)
- **Fontes oficiais (consultadas 2026-11-03):** `developers.facebook.com/docs/whatsapp/cloud-api/reference/messages`,
  `.../cloud-api/webhooks/payload-examples`, `.../graph-api/webhooks/getting-started`, `.../graph-api/changelog` (v26.0).

## Contexto
A Fase 3 abre a fronteira da Meta WhatsApp Cloud API: enviar template aprovado, receber o webhook com
segurança e registrar o status de cada envio. São decisões que definem o formato gravado (`modelos`/`envios`)
e o contrato do webhook — difíceis de reverter depois que houver dados.

## Decisão
1. **Cliente via `httpx`** (dependência já existente — **sem dependência nova**); versão da Graph API sempre
   em `GRAPH_API_VERSION` (default **`v26.0`**, configurável por ambiente), nunca fixa no código.
2. **`envios` identificados pelo `wamid`** (id retornado pela Meta no envio) — é a chave para casar os eventos
   de status (`sent`/`delivered`/`read`/`failed`) que chegam pelo webhook. `pricing` e `conversation` guardados
   como **JSONB inteiro** (a Meta muda esses campos; evita migração futura e serve o cálculo de custo).
3. **Webhook assinatura-primeiro:** o `POST` valida `X-Hub-Signature-256` (HMAC-SHA256 do **corpo cru** com
   `APP_SECRET`, via `hmac.compare_digest`) **antes de parsear**; inválido → 403. Responde 200 rápido; processa
   em segundo plano; **deduplica** por id de evento.
4. **`envios.agendamento_id` nullable** com **índice único parcial** `(agendamento_id, contato_id) WHERE
   agendamento_id IS NOT NULL` — **extensão consciente da ADR 0005**: permite envios avulsos/de teste (sem
   agendamento, usados para provar a Fase 3) sem furar a idempotência do worker (Fase 4), que continua garantida
   para os envios com agendamento. O `agendamento_id` é `String(36)` nullable por ora; a FK para `agendamentos`
   entra na Fase 4 (tabela ainda não existe).

## Consequências
- O `wamid` e o formato de `modelos`/`envios` passam a definir a identidade do envio e o contrato do webhook;
  reverter exige migração de dados — por isso é um ADR.
- Nenhuma dependência nova (httpx + `hmac`/`hashlib` da stdlib).
- A Fase 3 **não** envia a número real (§4) nem cria agendamentos (§5.1); o envio de teste é restrito ao número
  de teste. A validação ponta a ponta depende das credenciais Meta (Fase 0) e roda só em staging (§5.7).
- Testes nunca chamam a API real: mocks com payloads copiados da doc oficial.
- Relação com a ADR 0005: a idempotência de disparo (worker) permanece; esta ADR só abre espaço para envios sem
  agendamento via índice **parcial**.
