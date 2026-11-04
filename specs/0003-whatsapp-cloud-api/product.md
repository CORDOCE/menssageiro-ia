---
name: product-whatsapp-cloud-api
description: Product brief da Fase 3 (0003-whatsapp-cloud-api). Integração com a WhatsApp Cloud API — enviar template, webhook e modelos. Problema, métrica e fronteiras.
---

# Product: Integração WhatsApp Cloud API (Fase 3)

## Problema
Até a Fase 2 o sistema cadastra contatos, mas **não fala com o WhatsApp**. Para o Mensageiro cumprir
seu propósito (enviar comunicados/cobranças/notificações oficiais e saber se chegaram), é preciso a
fundação da integração com a **Meta WhatsApp Cloud API**: enviar uma mensagem de **template aprovado**,
receber o **webhook** da Meta de forma segura e **registrar o status** de cada envio. Sem isso, nenhuma
fase seguinte (agendamento, IA, respostas) tem como existir.

Para quem: o operador (via sistema) e, indiretamente, os contatos que recebem as mensagens oficiais.

## Métrica de sucesso
Observável no **número de teste** da Meta (nunca número real sem aprovação):
1. Um **template UTILITY aprovado** é enviado e a Meta retorna um `wamid`, gravado no `envio`.
2. O **webhook** recebe os eventos de status desse envio e grava **`entregue`/`lido`** no `envio`
   correspondente (casado pelo `wamid`).
3. Um evento de `message_template_status_update` atualiza o status do `modelo` no banco.

## Goals
- **Cliente WhatsApp** (`services/whatsapp_client.py`): enviar mensagem `type: template`; upload de mídia
  (PDF) e uso do `id`; listar/criar templates; retry exponencial em erro temporário (429/5xx, máx. 3);
  erro definitivo → `falhou` + código + alerta. Versão da Graph API via `GRAPH_API_VERSION` (confirmar a
  atual na doc oficial — não fixar de memória).
- **Webhook** (`api/webhook_meta.py`): `GET` de verificação (`hub.verify_token`→`hub.challenge`); `POST`
  com validação de `X-Hub-Signature-256` (HMAC-SHA256 do corpo cru com `APP_SECRET`, `compare_digest`);
  resposta 200 rápida; **deduplicação** por id de evento; **status → `envios`** pelo `wamid` (guardando
  `pricing`); `message_template_status_update` → `modelos`.
- **Modelo `modelos`** (templates): criar/sincronizar e refletir status Meta (rascunho→pendente→
  aprovado/rejeitado/pausado), com migração Alembic. Modelo `envios` com `wamid` e `status`.
- Observabilidade: auditoria e logs estruturados **sem PII** (telefone mascarado); erros ao Sentry.

## Non-goals (vinculante)
- **Worker, agendamentos, recorrência, janela de envio, anexos em escala** → **Fase 4**. Esta fase pode
  enviar um template **sob demanda** (gatilho de teste/endpoint protegido), mas **não** implementa o loop
  de disparo nem a expansão de grupo (ADR 0005). *(Invariante §5.1: só o worker inicia agendamentos — esta
  fase não cria agendamentos.)*
- **Mensagem RECEBIDA** (gravar em `mensagens`/`conversas`, `ultima_mensagem_recebida_em`, fila de
  respostas) e **respostas da IA** → **Fase 8**. *(Decisão do gate, 2026-11-03: o webhook da Fase 3 trata
  só verificação, assinatura, dedup, status→`envios` e `template_status_update`→`modelos`; mensagem
  recebida é 200-ack + dedup, sem persistir conteúdo.)*
- **Comandos do admin pelo WhatsApp** e resumo diário → **Fase 7**.
- **Descadastro por `SAIR`/`PARAR`** via webhook e **telas do PWA** → fora (Fase 5 / integra com §5.4 depois).
- **Envio para qualquer número real** → proibido sem aprovação explícita do responsável (§4).

## Dependências (pré-condições, domínio do responsável — Fase 0)
- Credenciais Meta configuradas na Railway (`WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`, `WABA_ID`, `APP_SECRET`,
  `WEBHOOK_VERIFY_TOKEN`, `GRAPH_API_VERSION`) — hoje ainda **não** definidas.
- **Número de teste** e **template UTILITY aprovado** na conta Meta.
- Webhook configurado no painel da Meta (callback URL + verify token) — por ambiente.
- Testes **nunca** chamam a API real da Meta (mocks); validação real só no número de teste em staging (§5.7).

## Questões em aberto (resolver no gate da spec, via /clarificar)
1. ✅ **Resolvida (gate 2026-11-03):** webhook da Fase 3 = só status/template; mensagem recebida → Fase 8.
2. **Gatilho de envio de teste:** endpoint protegido `POST /modelos/{id}/enviar-teste` (ou similar) só para
   provar o fluxo, sem virar caminho de produção (que é do worker na Fase 4).
3. Guardar `pricing`/`conversation` do status — quais campos mínimos.
