# Spec — 0023 Notificações push (Web Push/VAPID) — dívida A3

> Tier **Arquitetural** (dep nova `pywebpush` + tabela nova + enganche em fluxo de observabilidade).
> **ADR 0015.** Ver `product.md` e `design.md`. Escopo aprovado por Jefferson: **alertas §12 que o código
> emite**; UI em **Configurações** (0018).

## Escopo (v1)
Infra de Web Push: o dispositivo se inscreve (VAPID) e o backend envia push nos alertas que o **código**
emite via `alertar_evento` (modelo pausado/rejeitado, taxa de falha >5%, envio falhou, erro de ciclo).
**"Worker parado" fica fora** (detecção externa do Sentry — segue por e-mail).

## Critérios de aceite (Given/When/Then)
- **AC-1 (chave pública)** — `GET /push/chave-publica`: sem sessão → **401**; com sessão → `{chave}` com a
  `VAPID_PUBLIC_KEY` (ou `null` se não configurada, para a UI degradar).
- **AC-2 (inscrever)** — `POST /push/inscrever`: sem sessão → **401**; com sessão + `{endpoint, keys:{p256dh,auth}}`
  válido → **200/201** e a inscrição é persistida.
- **AC-3 (inscrição idempotente)** — reinscrição com o **mesmo `endpoint`** → upsert (não duplica linha).
- **AC-4 (envio no-op sem VAPID)** — Dado `VAPID_PRIVATE_KEY`/`VAPID_PUBLIC_KEY` ausentes, Quando
  `enviar_push(...)`, Então **não** chama `pywebpush` e **não** levanta (Fase 0/testes → sem rede, §5.7).
- **AC-5 (envio + limpeza)** — Dado VAPID configurado e 2 inscrições (1 válida, 1 que responde **410**),
  Quando `enviar_push(...)`, Então envia às duas e **remove** a inscrição que deu 404/410.
- **AC-6 (envio nunca derruba)** — Dado que o envio a uma inscrição lança, Quando `enviar_push(...)`, Então
  as demais ainda recebem e a função **não propaga** (molde de `alertar_evento`).
- **AC-7 (enganche no alerta)** — Dado `alertar_evento(op, status)` com `status∈{error,warning}`, Então
  chama `enviar_push` (título=`op`); com `status∈{ok,info}` → **não** chama (mesma regra do Sentry).
- **AC-8 (sem PII)** — o corpo/título do push contém só `operacao` + resumo agregado (`metadados` sem PII);
  nunca nome/telefone/texto de mensagem (§6).
- **AC-9 (UI Configurações)** — na tela Configurações, um card **"Notificações"** com botão "Ativar": browser
  sem suporte / permissão negada → aviso legível (sem quebrar); sucesso → `pushManager.subscribe` + `POST /push/inscrever`.

## Fora de escopo (vinculante)
- Push de aprovações (Fases 7/8); push de "worker parado"; escolha por-canal; silêncio agendado; histórico.
- iOS sem PWA instalada (Safari <16.4) → fallback e-mail. Fila/async para o envio (v1 é inline, no-op sem VAPID).

## Arquivos (previsto)
- Backend: `backend/pyproject.toml` (+`pywebpush`); migração `push_subscriptions`; `models/push_subscription.py`;
  `services/push.py` (`chave_publica`/`inscrever`/`enviar_push`); `schemas/push.py`; `api/push.py` (+registro `main.py`);
  `core/observabilidade.py` (enganche em `alertar_evento`). Testes: `test_push_service.py`, `test_push_api.py`,
  `test_observabilidade.py` (+AC-7). Config: `vapid_public_key`/`vapid_private_key` já existem.
- Frontend: `public/sw.js` (handlers `push`/`notificationclick`); `app/(app)/configuracoes/page.tsx` (card);
  `lib/api.ts` (`obterChavePush`/`inscreverPush`); teste de componente. `lib/push.ts` (helper de inscrição).
