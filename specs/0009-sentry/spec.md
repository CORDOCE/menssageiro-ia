# Spec — 0009 Inicializar Sentry (observabilidade, dívida S3)

Tier Pequeno. Fecha a dívida **S3**: existe `sentry_dsn` em config, mas **nenhum `sentry_sdk.init()`** →
erros não chegam ao Sentry (CLAUDE.md §7 não cumprido).

**Dependência nova:** `sentry-sdk` (§4) — necessidade: observabilidade exigida pelo §7; mantida (Sentry/PyCA-grade);
licença MIT; versão fixada; coberta por `pip-audit`. Sem alternativa nativa equivalente.

## Critérios de aceite (Given/When/Then)

**AC-1 — Inicializa quando há DSN.**
Given `SENTRY_DSN` configurada,
When a **API** (`app.main`) e o **worker** (`app.worker`) iniciam,
Then `sentry_sdk.init` é chamado uma vez em cada, com `before_send` de mascaramento e `send_default_pii=False`.

**AC-2 — Inerte sem DSN.**
Given `SENTRY_DSN` ausente,
When API/worker iniciam,
Then **não** chamam `sentry_sdk.init` e sobem normalmente (sem erro).

**AC-3 — PII mascarada no envio.**
Given um evento com telefone (dígitos) na mensagem/exceção e um corpo de requisição,
When `before_send` processa o evento,
Then o telefone sai **mascarado** e o corpo de requisição (`request.data`) é removido — nada de PII/segredo vai ao Sentry (§6).

**AC-4 — Erro de ciclo do worker é capturado.**
Given uma exceção dentro de `processar_ciclo`,
When o worker trata o erro (não derruba o loop),
Then além da auditoria `worker.ciclo_erro`, o erro é **enviado ao Sentry** (`capture_exception`).

## Casos de borda
- `SENTRY_DSN` inválida/malformada → a inicialização **não derruba** a app (falha contida, logada).
- `before_send` nunca levanta (um scrub ruim não pode impedir o report de chegar sanitizado ou ser descartado).

## Fora de escopo
- Tracing/performance (APM) e profiling — `traces_sample_rate=0` por ora.
- Alertas do §12 (observabilidade de disparo) — item separado (O1 da dívida).
- Front-end (Sentry no browser).

## Definition of Ready
- [x] AC testáveis (mock de `sentry_sdk.init`; `before_send` é função pura).
- [x] Dep justificada; sem ADR (reversível).
