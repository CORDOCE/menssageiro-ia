---
name: design-whatsapp-cloud-api
description: Design doc da Fase 3 (0003-whatsapp-cloud-api, tier arquitetural). Cliente WhatsApp, webhook e modelos, fundamentado na doc oficial da Meta. Alternativas, trade-offs, riscos e ADR.
---

# Design: Integração WhatsApp Cloud API (Fase 3)

> **Fontes oficiais consultadas em 2026-11-03** (registrar no PR):
> - Envio de template + mídia: `developers.facebook.com/docs/whatsapp/cloud-api/reference/messages`
> - Payload de status do webhook: `developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples`
> - Verificação/validação do webhook (X-Hub-Signature-256, handshake): `developers.facebook.com/docs/graph-api/webhooks/getting-started`
> - Versão da Graph API: `developers.facebook.com/docs/graph-api/changelog` → **v26.0** (mais recente, 29/07/2026).
>
> **Regra (§1.3/§11):** nenhum campo/endpoint/versão fixado de memória; a versão vai em `GRAPH_API_VERSION`.
> Campos marcados **[confirmar na doc]** devem ser reverificados no momento da implementação.

## Solução proposta
Respeitar a arquitetura já existente (SQLAlchemy 2 `Mapped`/`mapped_column`, routers em `app/api`,
schemas Pydantic v2, `core/*`, migrações Alembic com downgrade, `httpx` já é dependência). **Sem
dependência nova** (cliente via `httpx`; assinatura via `hmac`/`hashlib` da stdlib).

### Componentes (novos)
- **`app/services/whatsapp_client.py`** (mypy estrito, §8): cliente da Cloud API.
  - `enviar_template(telefone_e164, nome_template, idioma, componentes) -> str` (devolve o `wamid`).
    - `POST https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages`, header
      `Authorization: Bearer {WHATSAPP_TOKEN}`, corpo (doc oficial):
      ```json
      {"messaging_product":"whatsapp","to":"<E.164 sem +>","type":"template",
       "template":{"name":"<nome>","language":{"code":"pt_BR"},
         "components":[{"type":"body","parameters":[{"type":"text","text":"<valor>"}]}]}}
      ```
    - Resposta de sucesso: `messages[0].id` = **wamid**; `contacts[].wa_id`.
    - Cabeçalho DOCUMENT (PDF): componente `{"type":"header","parameters":[{"type":"document",
      "document":{"id":"<media_id>"}}]}`.
  - `upload_midia(bytes, tipo) -> str` (media id): `POST /{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/media`
    (multipart, `messaging_product=whatsapp`) **[confirmar na doc]**. Validar tipo/tamanho antes.
  - `listar_templates()` / `criar_template(...)`: `/{GRAPH_API_VERSION}/{WABA_ID}/message_templates`.
  - **Retry** exponencial (máx. 3) em 429/5xx; erro definitivo → exceção com código/motivo legível (o
    chamador marca `falhou`). Retry via laço stdlib (sem `tenacity`, sem dep nova).
- **`app/api/webhook_meta.py`** (router, **público** — a Meta chama; proteção é a assinatura, não auth de sessão).
  - `GET /webhook/meta`: se `hub.mode==subscribe` e `hub.verify_token==WEBHOOK_VERIFY_TOKEN` → devolve
    `hub.challenge` cru (text/plain, 200); senão 403.
  - `POST /webhook/meta`: **1º** lê o **corpo cru** (`await request.body()`), calcula
    `hmac.new(APP_SECRET, corpo_cru, sha256).hexdigest()`, compara com o header `X-Hub-Signature-256`
    (formato `sha256=<hex>`) via `hmac.compare_digest`. **Inválido → 403, antes de parsear** (CLAUDE §6).
  - Responde **200 rápido**; processamento via `BackgroundTasks` (upserts curtos). **Dedup** por id do
    evento antes de aplicar efeito.
  - **Status → `envios`**: para cada `entry[].changes[].value.statuses[]` casa pelo `id` (wamid) e grava
    `status` (`sent`/`delivered`/`read`/`failed`), `timestamp`, e o objeto `pricing` (+`conversation`) como
    JSONB. `statuses[].errors` → `falhou` + código/motivo.
  - **`message_template_status_update`**: atualiza `modelos` (aprovado/rejeitado/pausado) + motivo.
  - **Mensagem recebida**: só 200-ack + dedup nesta fase (conteúdo/`mensagens` → Fase 8, decisão do gate).
- **Modelos (novos) + migração aditiva:**
  - `modelo` (tabela `modelos`): `id` (uuid), `nome` (unique por idioma), `idioma` (`pt_BR`), `categoria`
    (`UTILITY`), `status` (`rascunho`/`pendente`/`aprovado`/`rejeitado`/`pausado`), `corpo`, `cabecalho_tipo`
    (nullable: `DOCUMENT`...), `variaveis` (JSONB), `motivo_rejeicao` (nullable), `criado_em`/`atualizado_em`.
  - `envio` (tabela `envios`, estende ADR 0005): `id` (uuid), `contato_id` (FK), `modelo_id` (FK, nullable),
    `agendamento_id` (**nullable** — envios de teste/avulsos da Fase 3 não têm agendamento; o worker preenche
    na Fase 4), `wamid` (String, **unique**, nullable até a Meta responder), `status`
    (`criado`/`enviando`/`enviado`/`entregue`/`lido`/`falhou`), `pricing` (JSONB nullable), `erro_codigo`/
    `erro_motivo` (nullable), `criado_em`/`atualizado_em`. Índice único parcial `(agendamento_id, contato_id)
    WHERE agendamento_id IS NOT NULL` (preserva a idempotência da ADR 0005 sem travar os avulsos).
- **Gatilho de teste** (prova o "pronto quando", sem ser caminho de produção): endpoint **protegido**
  `POST /modelos/{id}/enviar-teste` (auth de sessão) que cria um `envio` avulso e chama `enviar_template`
  **apenas para o número de teste** (nunca número real sem aprovação, §4). A Fase 4 (worker) é o caminho real.
- **Config** (`core/config.py`): já há os campos Meta (hoje `None`); acrescentar `graph_api_version` com
  default a confirmar (`v26.0`). Auditoria/log sem PII (telefone mascarado via `core/telefone.mascarar_telefone`).

## Fluxo "pronto quando"
1. Operador chama `POST /modelos/{id}/enviar-teste` → cria `envio` (`status=enviando`) → `enviar_template`
   → Meta responde `wamid` → grava `wamid`, `status=enviado`.
2. Meta chama o webhook com `statuses` (`sent`→`delivered`→`read`) → casa pelo `wamid` → atualiza `status`
   e grava `pricing`. **Entregue/lido gravados** ✅.
3. `message_template_status_update` → `modelos.status`.

## Alternativas consideradas
| Opção | Prós | Contras | Veredito |
|---|---|---|---|
| **Cliente via `httpx` (dep existente)** | zero dep nova; assíncrono/síncrono | escrever retry à mão | **Escolhida** |
| SDK não-oficial WhatsApp | menos código | dep nova, manutenção/risco, esconde a versão da API | Descartada |
| **Assinatura validada no corpo cru, antes de parsear** | correto e seguro (§6) | exige ler `request.body()` cru | **Escolhida** |
| Validar após o Pydantic parsear | simples | o corpo re-serializado ≠ cru → HMAC quebra | Descartada |
| **`envios.agendamento_id` nullable + índice único parcial** | permite envio avulso/teste sem furar ADR 0005 | estende a ADR 0005 | **Escolhida (→ ADR)** |
| Exigir agendamento sempre | fiel à ADR 0005 literal | impossível provar a Fase 3 sem o worker (Fase 4) | Descartada |
| **Processar no webhook via BackgroundTasks** | 200 rápido; sem fila | acoplado ao processo da API | **Escolhida** (volume pequeno) |
| Fila externa (Redis/worker) | desacopla | infra nova; overkill agora | Descartada (revisitar Fase 8) |
| **Dedup por id de evento (status/`wamid`+status)** | idempotente a reentrega da Meta | tabela/estado de dedup | **Escolhida** |

## Trade-offs e riscos
- **Não testável contra a API real** (§5.7): testes usam **mocks com payloads copiados da doc**; validação
  ponta a ponta só em **staging com número de teste**. Nenhum teste chama a Meta.
- **Corpo cru p/ HMAC:** o endpoint precisa do `bytes` exato recebido — cuidado com middlewares que
  re-serializam. Teste explícito de assinatura inválida → 403.
- **Segredos** (`WHATSAPP_TOKEN`, `APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`) só em env; **hoje não setados**
  (pré-condição Fase 0, responsável). Mascarar telefone em log; nunca logar token/corpo com PII.
- **Superfície de ataque do webhook** (público): rate limit (§6), rejeição por assinatura antes de qualquer
  processamento, dedup, resposta 200 mesmo em payload inesperado (não vazar erro à Meta).
- **Versão da Graph API** muda; `GRAPH_API_VERSION` configurável; confirmar `v26.0` no deploy.
- **Extensão da ADR 0005** (envios sem agendamento): documentar para não conflitar com a idempotência do worker.

## Decisões irreversíveis (→ ADR)
- **ADR 0007 (proposto):** integração WhatsApp Cloud API — (a) `httpx` + versão em `GRAPH_API_VERSION`
  (default v26.0); (b) `envios` identificados pelo **`wamid`** para casar status do webhook; (c) validação
  do webhook **assinatura-primeiro** sobre o corpo cru; (d) **`envios.agendamento_id` nullable** com índice
  único parcial — extensão consciente da ADR 0005 para permitir envios avulsos/teste. Difícil de reverter:
  define o formato gravado de `envios`/`modelos` e o contrato do webhook.

## Questões para /clarificar (gate da spec)
1. Nome/assinatura exata do endpoint de teste (`POST /modelos/{id}/enviar-teste`?) e se aceita variáveis do corpo.
2. Campos mínimos de `pricing`/`conversation` a persistir (proposta: JSONB inteiro do `pricing` + `conversation`).
3. Mídia/PDF entra na Fase 3 ou fica para quando houver anexos (Fase 4)? (proposta: cliente suporta, mas o
   gate "pronto" usa template só-texto).
