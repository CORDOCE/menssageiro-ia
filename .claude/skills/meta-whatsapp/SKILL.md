---
name: meta-whatsapp
description: Regras obrigatórias para qualquer código que toque a WhatsApp Cloud API da Meta — envio de templates, mídia (PDF), janela de 24 h, webhook (assinatura, deduplicação, status, eco da coexistência), templates (criação, categoria, aprovação), erros, limites e custos. Exige consultar a documentação oficial antes de usar campo ou endpoint. Acione com /meta-whatsapp.
---

# Skill: Meta WhatsApp (Cloud API)

## Antes de escrever código
1. **Consulte a documentação oficial atual** (developers.facebook.com, seção WhatsApp Business Platform) para o
   endpoint/campo que vai usar. Registre URL e data no PR. **Não use campo, código de erro ou endpoint de memória.**
2. Versão da Graph API sempre via `GRAPH_API_VERSION`; nunca fixa no código.

## Regras de envio
- Iniciar conversa = **template aprovado**, categoria **UTILITY**, idioma `pt_BR`.
- Texto livre (`type: text`/interativo) só se `contatos.ultima_mensagem_recebida_em` ≥ agora − 24 h, checado no envio.
- PDF: subir mídia, usar o `id` no cabeçalho DOCUMENT do template; validar tipo e tamanho antes.
- Guardar o `wamid` de todo envio; status chegam pelo webhook.
- Erros temporários (limite de taxa, 5xx): retry exponencial, máx. 3, respeitando idempotência.
- Erros definitivos: marcar `falhou`/"não enviada" com código e motivo legível para o operador.

## Templates
- Criar via API com exemplos para cada variável; sem variável no início/fim; nada promocional.
- Aguardar `message_template_status_update`; rejeitado → guardar motivo e alertar.
- Template pausado/desativado bloqueia os agendamentos que dependem dele.

## Webhook
- `GET` de verificação com `WEBHOOK_VERIFY_TOKEN`.
- `POST`: validar `X-Hub-Signature-256` (HMAC-SHA256 do **corpo cru** com `APP_SECRET`) antes de parsear; 403 se inválido.
- Responder 200 rápido; processar em segundo plano; deduplicar por id do evento.
- Eco de mensagens enviadas pelo app do celular (coexistência) → origem `app_celular` e pausa da IA na conversa.
- Gravar o objeto `pricing` dos status para o cálculo de gasto.

## Custos e limites (conferir na doc antes de alterar cálculos)
- Cobrança por mensagem entregue, por categoria e país do destinatário; mensagens recebidas não são cobradas.
- Serviço: cota grátis mensal por número; utilidade cobrada inclusive dentro da janela.
- Limite de destinatários únicos por 24 h no portfólio; respeitar `LIMITE_DIARIO`.

## Testes
- Nunca chamar a API real em testes automatizados: usar mocks com payloads copiados da documentação oficial.
- Validação ponta a ponta só em staging, com o número de teste.
