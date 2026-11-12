---
name: product-reenvio-automatico
description: Product brief da feature 0020 Reenvio automático de envios que falharam por causa transitória. Problema, métrica, fronteiras.
---

# Product: Reenvio automático de envios (falha transitória)

## Problema
Hoje um `envio` que falha vira `falhou` **terminal** — o worker não o reprocessa (invariante §5.2;
`disparo.py:345,357-367`). Quando a falha foi um **blip transitório** nosso→Meta (internet/limite/5xx) que não
se recuperou nos 3 tiros HTTP do `whatsapp_client`, a mensagem agendada simplesmente **não sai**, e o operador só
descobre depois (Histórico / alerta de taxa da 0019). Falta uma **rede de recuperação** para esse caso.

## Métrica de sucesso
- **Taxa de recuperação:** dos envios que entram em `aguardando_retry` (falha transitória), % que termina
  `enviado` sem intervenção humana. Alvo: a maioria dos blips se resolve sozinha.
- **Falhas definitivas por transitório → ~0:** envios que hoje virariam `falhou` por blip passam a ser
  recuperados; o que sobra em falha definitiva é erro real (número inválido, não-usuário, etc.).

## Goals
- Reenvio **automático e limitado** (até 3x, backoff curto) de falhas **transitórias de envio**.
- **Preservar a idempotência de ENTREGA** (§5.2): nunca entregar a mesma mensagem ao mesmo contato duas vezes.
- Ao esgotar as tentativas: **decisão humana por envio** (estado + ação de reenvio manual).
- Observabilidade: contadores de tentativa e eventos/alertas no esgotamento.

## Non-goals (vinculante)
- Reenviar **erro definitivo** (número inválido, não-usuário WhatsApp, descadastrado, template rejeitado).
- Reenviar **falha de entrega** reportada pela Meta via webhook (a Meta já retenta a entrega).
- Retry de **longa duração** (horas/dias) ou fila/broker externo.
- Mudar o **retry HTTP** nosso→Meta (3x/backoff no `whatsapp_client`) — já existe, permanece.
- Fluxo de decisão humana em **lote/agendamento** — a decisão é por envio (contato).
