# Tasks — 0017 Alerta de fluxo crítico ao Sentry (O1)

TDD: teste que falha primeiro, depois implementação. Gate: `pytest backend/tests/`.

- [ ] **T1 — helper:** `core/observabilidade.py` → `alertar_evento(operacao, status, correlation_id, metadados)`
      que chama `sentry_sdk.capture_message(operacao, level=...)` (error/warning) com `extra`. No-op se Sentry
      não inicializado (o próprio `sentry_sdk` já é no-op sem init). — AC-1, AC-2, AC-6, AC-7
- [ ] **T2 — flag na auditoria:** `core/audit.py` `registrar_auditoria(..., alertar: bool = False)`; se
      `alertar and status in {"error","warning"}`, chama `alertar_evento(...)` dentro do try não-bloqueante. — AC-1..AC-4, AC-6
- [ ] **T3 — pontos do disparo:** passar `alertar=True` em `worker/disparo.py` (`agendamento.erro_ciclo`,
      `agendamento.falhou`, `agendamento.limite_por_agendamento`, `envio.falhou`) e em `api/webhook_meta.py`
      (`template_status` quando pausado/rejeitado → `status="warning", alertar=True`). — AC-5
- [ ] **T4 — testes** (`tests/test_observabilidade.py` + `test_worker_disparo.py`): AC-1..AC-4 (mock
      `capture_message`, verificar nível/args), AC-5 (ciclo com modelo não aprovado/teto → emitiu), AC-6
      (sem DSN → no-op), AC-7 (sem PII nos args).
      Gate: `pytest backend/tests/ -k "observab or disparo or webhook"`.

## Gate final (antes do PR)
- [ ] `/revisar` + `/seguranca` sem P0/P1 · `/validar` AC-1..AC-7 · CI completo via Docker.
- [ ] Cobertura ≥90% nas linhas novas (§8). Sem migração.
