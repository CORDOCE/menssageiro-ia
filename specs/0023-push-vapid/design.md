# Design — 0023 Notificações push (Web Push/VAPID)

## Solução (visão geral)
Web Push padrão (VAPID), com o backend enviando as notificações e o service worker da PWA exibindo-as.

1. **Modelo + migração** — tabela `push_subscriptions` (`id`, `endpoint` único, `p256dh`, `auth`,
   `criado_em`). Suporta **múltiplos dispositivos** (o operador usa celular + desktop).
2. **Service `services/push.py`**:
   - `chave_publica()` → devolve `VAPID_PUBLIC_KEY` (o browser precisa dela para inscrever).
   - `inscrever(db, sub)` → upsert por `endpoint` (reinscrição não duplica).
   - `enviar_push(titulo, corpo, url=None)` → itera as inscrições e usa **`pywebpush`** com claims VAPID;
     **no-op** sem `vapid_private_key`/`vapid_public_key`; remove a inscrição em **404/410** (expirada);
     **nunca levanta** (como `alertar_evento`).
3. **Endpoints `api/push.py`** (autenticados por sessão):
   - `GET /push/chave-publica` → `{chave}`.
   - `POST /push/inscrever` → recebe o `PushSubscription` do browser (endpoint + keys), faz upsert.
4. **Enganche central** — em `core/observabilidade.py::alertar_evento`, **após** o `capture_message` ao
   Sentry, chamar `enviar_push(titulo=operacao, corpo=<resumo sem PII>)`. Assim **todos** os eventos
   `alertar=True` da 0017/0019 (modelo rejeitado, taxa, envio falhou, erro de ciclo) viram push de uma vez.
5. **Frontend**:
   - `public/sw.js` — handlers `push` (exibe `showNotification`) e `notificationclick` (foca/abre a PWA).
   - UI de inscrição — um card **"Notificações"** na tela **Saúde** (0021): botão "Ativar notificações"
     → `Notification.requestPermission()` → `pushManager.subscribe({applicationServerKey})` → `POST /push/inscrever`.
     Estados: indisponível (browser sem suporte / iOS sem PWA) → aviso + "use o e-mail".

## Alternativas consideradas
- **Webhook do Sentry → backend → push** (cobriria "worker parado"): acopla ao Sentry, exige endpoint
  público recebendo webhook assinado + parsing — complexidade alta para 1 evento. **Rejeitado** no v1
  (worker parado segue por e-mail). O enganche em `alertar_evento` cobre tudo que o código emite.
- **FCM/APNs nativo**: exige contas/credenciais de push por plataforma. **Web Push (VAPID)** é padrão
  aberto, sem conta, funciona em Chrome/Firefox/Edge/Safari(≥16.4 PWA). **Escolhido.**
- **Guardar a chave privada VAPID no código**: não — vai para env (`VAPID_PRIVATE_KEY`), como os demais segredos.

## Trade-offs / riscos
- **iOS**: Web Push só com Safari ≥16.4 **e PWA instalada** (§7). Mitigação: a UI detecta e orienta; o
  **e-mail** segue como fallback universal (alert rules do Sentry, já ativos).
- **Rede no fluxo de alerta**: `enviar_push` faz HTTP aos endpoints de push dentro de `alertar_evento`
  (worker/webhook). Mitigação: alertas são raros; **no-op sem VAPID** (zero rede em testes/Fase 0);
  nunca levanta; limpa inscrições expiradas. (Se virar gargalo, mover para fila — fora do v1.)
- **PII**: o corpo do push **não** leva PII — só `operacao` + resumo agregado, como o Sentry já faz (§6).
- **Best-effort**: push não é entrega garantida; o e-mail continua sendo o canal confiável.

## Impacto / §4
- **Dependência nova**: `pywebpush` (MIT, mantida; traz `py-vapid`; usa `cryptography`, já no projeto). **Aprovada** por Jefferson.
- **Infra**: `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` na Railway (eu gero o par; você seta). As vars já existem em `config.py`.
- **Migração**: tabela nova `push_subscriptions` (aditiva, `downgrade` dropa). **ADR 0015.**
