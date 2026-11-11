# Tasks — 0019 Alertas de agregação (worker parado + taxa de falha)

TDD: teste que falha primeiro, depois implementação. Uma task por grupo de AC; gate executável em cada uma.

- [ ] **T1 — check-in do worker (Alerta A):** em `backend/app/worker/__main__.py`, no fim de cada ciclo do loop
      `executar()` (`:49-66`), chamar `sentry_sdk.crons.capture_checkin(monitor_slug=..., status="ok",
      monitor_config={schedule intervalo + checkin_margin >5min})` (upsert inline). No-op natural sem `SENTRY_DSN`.
      Slug fixo (ex.: `worker-ciclo`). — AC-1, AC-6
- [ ] **T2 — cálculo da taxa 24h (Alerta B):** helper novo (ex. `backend/app/core/observabilidade.py` ou
      `worker/`) que conta, nas últimas 24h por `Envio.criado_em`: `tentativas` (status ∈ `_CONTAM_LIMITE` ∪ `{falhou}`)
      e `falhas` (`falhou`). Reusa o molde de janela de `disparo.py:142`. Retorna (tentativas, falhas, pct) sem efeito colateral. — AC-2..AC-4 (borda tentativas=0)
- [ ] **T3 — idempotência diária + emissão (Alerta B):** na checagem por ciclo, se `tentativas ≥ 20` e `pct > 5%`,
      checar auditoria por `operacao == "envios.taxa_falha_alta"` com `criado_em >= início do dia (America/Sao_Paulo)`
      (molde `auth.py:68-77`); se count == 0, emitir via `registrar_auditoria(..., alertar=True)` → `alertar_evento`
      com metadados **só agregados** (tentativas, falhas, pct). — AC-2, AC-5, AC-7
- [ ] **T4 — ligar a checagem ao ciclo:** chamar T2+T3 a cada ciclo em `__main__.py` (junto do check-in T1),
      dentro de try não-bloqueante (não derruba o worker). — AC-6
- [ ] **T5 — testes** (`backend/tests/test_alertas_agregacao.py` + ajuste em `test_worker_*`):
      AC-1 (mock `capture_checkin`, verificar slug/status/monitor_config), AC-2..AC-5 (as 5 linhas da matriz, com
      envios semeados e tempo/contagem controlados; mock `capture_message`/`alertar_evento`), AC-6 (sem DSN → no-op,
      ciclo roda), AC-7 (metadados sem telefone/texto). Casos de borda: tentativas=0, virada de dia.
      Gate: `pytest backend/tests/ -k "agregacao or taxa_falha or checkin"`.

## Gate final (antes do PR)
- [ ] `/revisar` + `/seguranca` sem P0/P1 · `/validar` AC-1..AC-7 · CI completo via Docker.
- [ ] Cobertura ≥90% nas linhas novas (§8). Sem migração.
- [ ] Documentar no PR o **passo §4 manual**: criar/roteamento do monitor `worker-ciclo` e alerta de taxa no painel Sentry (e-mail/push).
- [ ] `STATE.md` atualizado.
