# Product — 0023 Notificações push (Web Push/VAPID) — dívida A3

## Problema
Os alertas de fluxo crítico (§12) que o código emite (modelo pausado/rejeitado, taxa de falha >5%,
envio falhou, erro de ciclo) hoje só chegam ao operador por **e-mail** (alert rules do Sentry). Não há
**notificação imediata no dispositivo** (celular/desktop) — o operador precisa abrir o e-mail para saber
que algo crítico aconteceu. O BRIEFING §12 pede alertas "e-mail **+ push**" e a Fase 5 pede
"PWA com notificações push"; a fundação PWA (0006) foi entregue **sem** push (débito A3).

## Para quem
O **operador** (1 admin) — recebe os alertas no celular/desktop onde tiver a PWA, em segundos.

## Métrica de sucesso
Um alerta crítico emitido pelo código (`alertar_evento`) gera uma **notificação push** em todos os
dispositivos inscritos, em segundos, **sem PII** no conteúdo.

## Goals
- Infra de Web Push (VAPID): inscrição do dispositivo + envio de push pelo backend.
- Enviar push nos alertas §12 que o **código** emite (enganche central em `alertar_evento`).
- No-op seguro sem chaves VAPID / sem inscrições (padrão do repo).

## Non-goals (fora do v1)
- Push de **aprovações** (sugestões/respostas) — Fases 7/8 (plugam no mesmo service depois).
- Push de **"worker parado"** — é detecção **externa** do Sentry Cron Monitor (o worker parado não roda
  código para avisar de si mesmo); segue pelo e-mail do alert rule do Sentry.
- Escolher por-canal quais alertas vão a push vs e-mail; agendar silêncio; histórico de notificações.
- iOS sem PWA instalada (Web Push exige Safari ≥16.4 + PWA na tela inicial, §7) — fallback é o e-mail.
