# ADR 0015 — Notificações push via Web Push (VAPID)

Data: 2026-11-12 · Status: proposto (spec 0023 / dívida A3) · Responsável: Jefferson

## Contexto
Os alertas §12 que o código emite só chegam por e-mail (Sentry). O BRIEFING §12/Fase 5 pede push; a
fundação PWA (0006) saiu sem ele (débito A3). Precisamos de notificação imediata no dispositivo do
operador para eventos críticos, sem acoplar a uma plataforma proprietária nem vazar PII.

## Decisão
1. **Web Push com VAPID**, biblioteca **`pywebpush`** (MIT; traz `py-vapid`; usa `cryptography` já presente).
   Padrão aberto, sem conta de plataforma; funciona em Chrome/Firefox/Edge e Safari ≥16.4 (PWA instalada).
2. **Inscrições no banco** — tabela `push_subscriptions` (endpoint único + chaves), múltiplos dispositivos;
   inscrições expiradas (404/410 no envio) são removidas.
3. **Enganche central em `alertar_evento`** (`core/observabilidade.py`): todo alerta `alertar=True` que o
   código emite (0017/0019) dispara push, além do Sentry. **Não** cobre "worker parado" (detecção externa
   do Sentry — o worker parado não roda código); esse segue por e-mail.
4. **No-op sem chaves VAPID / sem inscrições** (padrão do repo); `enviar_push` nunca levanta; **sem PII** no corpo.
5. Chaves VAPID em env (`VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`), nunca no código.

## Alternativas rejeitadas
- **Webhook do Sentry → push** (cobriria worker parado): complexidade alta (endpoint público + assinatura)
  para 1 evento; worker parado fica com e-mail.
- **FCM/APNs nativo**: exige contas/credenciais por plataforma; Web Push é aberto e suficiente.

## Consequências
- **+** Push imediato dos alertas críticos em todos os dispositivos inscritos; fundação reusável pelas
  Fases 7/8 (aprovações plugam no mesmo `enviar_push`).
- **−** Dependência nova (`pywebpush`) e 2 segredos novos (VAPID) na infra. iOS limitado a Safari ≥16.4 +
  PWA instalada — mitigado pelo fallback de e-mail. `enviar_push` adiciona rede ao fluxo de alerta
  (raro; no-op sem VAPID; nunca bloqueia).
- **Reversível**: migração aditiva com `downgrade`; sem VAPID o recurso fica inerte.
