# Tasks — 0014 Histórico de envios

Cada task mapeia AC(s) + o gate que a prova. TDD: teste que falha primeiro, depois implementação.

## Backend — `GET /envios`
- [ ] **T1** `schemas/envio.py` → `EnvioRead` (campos do AC-1, `from_attributes`). — AC-1
- [ ] **T2** `api/envios.py` → router `/envios` com `Depends(usuario_atual)`; `listar` com join
      `Contato`/`Modelo` (outer no modelo), filtros `status`/`desde`/`ate`, `limit`(1..200)/`offset`,
      `order_by(criado_em desc)`. — AC-1..AC-4, AC-6, AC-7
- [ ] **T3** registrar o router em `main.py` (import + `include_router`). — AC-1
- [ ] **T4** `tests/test_envios.py`: lista+ordem (AC-1), filtro status (AC-2), filtro período (AC-3),
      join contato/modelo + avulso (AC-4), 401 (AC-5), erro só em falhou (AC-6), paginação+422 (AC-7).
      Gate: `pytest backend/tests/test_envios.py` (Postgres container).

## Frontend — tela `historico`
- [ ] **T5** `lib/api.ts` → `listarEnvios(filtros)` + tipo `Envio` (reusa `ApiError`). — AC-8
- [ ] **T6** `app/(app)/historico/page.tsx`: lista (5 campos, erro só em `falhou`), filtro status +
      período, estado-vazio, 401→login. Ligar o item **Histórico** do `AppShell` à rota. — AC-8
- [ ] **T7** `historico/page.test.tsx` (vitest): render lista, filtro, estado-vazio, erro em falhou. — AC-8
      Gate: `npm run lint && tsc --noEmit && npm test && npm run build` (em `frontend/`).

## Gates finais (antes do PR)
- [ ] `/revisar` + `/seguranca` sem P0/P1 · `/validar` AC-1..AC-8 · CI completo via Docker.
- [ ] Cobertura ≥90% nas linhas novas do endpoint (§8). Sem migração (modelo `Envio` já existe).
