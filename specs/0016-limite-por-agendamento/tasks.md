# Tasks — 0016 Teto de segurança por agendamento (R1-d)

TDD: teste que falha primeiro, depois implementação. Gates: pytest (worker) + vitest (selo) + CI Docker.

## Backend
- [ ] **T1 — migração (/migracao):** `+limite_por_agendamento_dia INT NULL` em `configuracoes`; downgrade = drop.
      Gate: `alembic upgrade head && alembic downgrade base && alembic upgrade head`.
- [ ] **T2 — config:** `core/config.py` `limite_por_agendamento_default` via env `LIMITE_POR_AGENDAMENTO`
      (default `None`); `models/configuracao.py` (+coluna); `services/janela.py` semeia na criação da linha. — AC-6
- [ ] **T3 — worker:** `worker/disparo.py` lê `cfg.limite_por_agendamento_dia`; em `_processar_agendamento`,
      conta envios do agendamento, envia até o teto, corta o excedente, marca `parcial` + auditoria
      `agendamento.limite_por_agendamento` (sem PII). Ordem: global → por-agendamento → por-contato. — AC-1..AC-6
- [ ] **T4 — status terminal `parcial`:** incluir no conjunto de terminais do worker/API (não reprocessa). — AC-5
- [ ] **T5 — testes worker** (`tests/test_worker_disparo.py` ou novo): tabela-verdade AC-1/AC-2/AC-3,
      auditoria AC-4, terminal AC-5, lê config AC-6, bordas (N==T, N==T+1, individual).
      Gate: `pytest backend/tests/ -k "limite_por_agendamento or disparo"`.

## Frontend
- [ ] **T6 — selo `parcial`:** `components/Selo.tsx` `seloAgendamento` (+caso `parcial` → "Parcial", tom neutro/aguardando)
      + teste. Agenda/Histórico já usam o selo. — AC-7
      Gate: `npm run lint && tsc --noEmit && npm test && npm run build`.

## Gate final (antes do PR)
- [ ] `/revisar` + `/seguranca` sem P0/P1 · `/validar` AC-1..AC-7 · CI completo via Docker.
- [ ] Cobertura ≥90% nas linhas novas do worker (§8). ADR 0013 registrado. §4 aprovado.
