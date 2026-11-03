---
name: spec-whatsapp-cloud-api
description: Spec da Fase 3 (0003-whatsapp-cloud-api). Os critérios de aceite são o contrato e o oráculo de teste. Cliente WhatsApp + webhook + modelos.
---

# Spec: Integração WhatsApp Cloud API (Fase 3)

## Contexto
Fundação da integração com a Meta WhatsApp Cloud API (BRIEFING §10.1/§10.2/§14, fase 3): enviar template
aprovado, receber o webhook com segurança, registrar status. Detalhes e fontes oficiais em `product.md`/
`design.md`. **Pronto quando** "template enviado ao número de teste; status entregue/lido gravados" e os AC
abaixo passam. **Sem worker/agendamentos (Fase 4), sem IA/respostas (Fase 8), sem comandos admin (Fase 7).**

**Dependências (pré-condições do responsável, Fase 0):** credenciais Meta na Railway (`WHATSAPP_TOKEN`,
`PHONE_NUMBER_ID`, `WABA_ID`, `APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`, `GRAPH_API_VERSION`), número de teste e
template UTILITY aprovado. Enquanto não existirem, os AC passam por **mock** (payloads da doc); a validação
real só em staging com o número de teste (§5.7).

## Decisões do gate (via /clarificar, 2026-11-03)
- Mídia/PDF: o cliente suporta, mas o gate "pronto" usa template **só-texto** (mídia = task de baixa prioridade).
- Prova do envio: endpoint protegido `POST /modelos/{id}/enviar-teste`, **restrito ao número de teste**.
- Status: persistir `pricing` **e** `conversation` como **JSONB inteiro** no `envio`.
- Webhook Fase 3: só verificação/assinatura/status/template; mensagem recebida = 200-ack sem persistir conteúdo.

## Critérios de aceite (o contrato)

**Cliente WhatsApp (testado com mock de `httpx`; nunca a API real — §5.7)**
- **AC-1** — Dado um template só-texto, Quando `enviar_template(...)`, Então faz `POST` em
  `{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages` com `messaging_product:"whatsapp"`, `to`, `type:"template"`
  e `template.name/language.code/components`, e **retorna o `wamid`** de `messages[0].id`.
- **AC-2** — Dado 429/5xx, Quando `enviar_template`, Então faz **retry exponencial (máx. 3)**; se persistir,
  levanta exceção com o código.
- **AC-3** — Dado erro definitivo (4xx não-retentável), Quando `enviar_template`, Então levanta exceção com
  código + motivo legível, **sem** retry.
- **AC-4** — Dado um PDF, Quando `upload_midia` e depois `enviar_template` com cabeçalho DOCUMENT, Então o
  componente `header` usa `{"type":"document","document":{"id":<media_id>}}`. *(task de baixa prioridade)*

**Webhook (`/webhook/meta`, público; segurança = assinatura)**
- **AC-5** — Dado `GET` com `hub.mode=subscribe` e `hub.verify_token` correto, Então **200** devolvendo
  `hub.challenge`; token errado → **403**.
- **AC-6** — Dado `POST` com `X-Hub-Signature-256` **inválida**, Então **403** e **nada** é processado/persistido
  (validação do corpo cru **antes** de parsear).
- **AC-7** — Dado `POST` assinado com `statuses[]` (`delivered`/`read`), Então casa pelo `id` (**wamid**),
  grava `status` e os objetos `pricing`+`conversation` (JSONB) no `envio`, e responde **200**.
- **AC-8** — Dado `POST` assinado com `statuses[].errors`, Então o `envio` vira `falhou` com `erro_codigo`/
  `erro_motivo`.
- **AC-9** — Dado o **mesmo** evento reentregue, Quando processado 2×, Então é **idempotente** (status não é
  aplicado em duplicidade; dedup por id de evento).
- **AC-10** — Dado `POST` assinado com `message_template_status_update`, Então `modelos.status` é atualizado
  (`aprovado`/`rejeitado`/`pausado`) e, se rejeitado, grava o motivo.
- **AC-11** — Dado `POST` assinado com **mensagem recebida**, Então responde **200** e **não** persiste o
  conteúdo (decisão do gate; conteúdo é Fase 8).

**Modelos / envios / dados**
- **AC-12** — Dado banco limpo, Quando `alembic upgrade head` e `downgrade base`, Então criam/revertem
  `modelos` e `envios` (com `wamid` **único**, `agendamento_id` **nullable**, índice único **parcial**
  `(agendamento_id, contato_id) WHERE agendamento_id IS NOT NULL`), ambos código 0.
- **AC-13** — Dado o índice parcial, Quando 2 envios com o **mesmo** `(agendamento_id≠null, contato_id)`, Então
  viola unicidade; 2 envios **avulsos** (`agendamento_id=null`) ao mesmo contato → **permitidos** (ADR 0005 ext.).

**Endpoint de teste (prova o "pronto quando")**
- **AC-14** — Dado `POST /modelos/{id}/enviar-teste` **sem** credencial → **401**.
- **AC-15** — Dado com credencial e `telefone` = **número de teste**, Então cria um `envio` avulso, chama o
  cliente (mock), grava o `wamid` e `status=enviado`, responde **200/201** com o `envio`.
- **AC-16** — Dado `telefone` **≠** número de teste (fora da allowlist/variável), Então **403/422** e **nada**
  é enviado (invariante §4: nunca número real sem aprovação).

**Qualidade / segurança**
- **AC-17** — Dado qualquer log/auditoria desta feature, Então o telefone aparece **mascarado** e o token/corpo
  com PII **nunca** são logados.
- **AC-18** — Dado o `backend/`, Quando `pytest --cov`, Então cobertura das **regras** (envio, retry, assinatura,
  dedup, status→envio, template_status) ≥ **90%**; `ruff`/`mypy` código 0; **nenhum** teste chama a API real.

## Matriz de decisão — processamento de um evento assinado (cada linha vira teste)
| tipo do evento | casa `wamid`? | resultado |
|---|---|---|
| `statuses` `delivered`/`read` | sim | atualiza `envio.status` + grava `pricing`/`conversation` |
| `statuses` `delivered`/`read` | não (wamid desconhecido) | ignora, registra auditoria (sem erro) |
| `statuses.errors` | sim | `envio.falhou` + código/motivo |
| evento já visto (id repetido) | — | **idempotente** (no-op) |
| `message_template_status_update` | — | atualiza `modelos.status` (+motivo se rejeitado) |
| mensagem recebida | — | **200-ack**, não persiste conteúdo (Fase 8) |
| assinatura inválida | — | **403**, não processa |

## Casos de borda
- Corpo cru vs re-serializado: o HMAC usa o `bytes` exato recebido; teste explícito de assinatura inválida → 403.
- `statuses` com `wamid` desconhecido (envio não encontrado) → ignora sem quebrar, auditoria sem PII.
- Payload inesperado/novo campo da Meta → responde 200 (não devolve erro à Meta), loga para investigação.
- 3 webhooks por envio (`sent`→`delivered`→`read`): cada um atualiza; ordem fora de sequência não rebaixa
  (`read` não volta para `delivered`).
- Retry respeita idempotência: reenviar após timeout não cria 2 mensagens (chave de idempotência no envio).
- `GRAPH_API_VERSION` ausente → erro de config claro na subida (não assume versão).

## Fora de escopo (vinculante)
- Worker, agendamentos, recorrência, janela de envio, expansão de grupo, anexos em escala → **Fase 4**.
- Mensagem recebida persistida, `conversas`/`mensagens`, fila de respostas, IA → **Fase 8**.
- `SAIR`/`PARAR` via webhook, comandos do admin pelo WhatsApp, resumo diário → **Fase 7**.
- Telas do PWA de modelos/envios → **Fase 5**.
- Qualquer envio a **número real**.

## Suposições (explícitas — confirmar no gate; CLAUDE §1.4)
1. `GRAPH_API_VERSION` default **`v26.0`** (confirmado na doc 2026-11-03; configurável por ambiente).
2. Idioma do template **`pt_BR`**, categoria **UTILITY** (invariante §5.3).
3. Número de teste vem de variável de ambiente (ex.: `WHATSAPP_TEST_NUMBER`) usada na allowlist do AC-16.
4. Dedup de evento por `id` do `status`/mensagem (ou `(wamid,status)` quando não houver id de evento).
5. Processamento do webhook via `BackgroundTasks` (volume pequeno); revisitar fila externa na Fase 8.
