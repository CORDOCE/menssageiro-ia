# Tasks — 0021 Tela "Saúde do sistema" + `/admin/health/deep`

Cada task mapeia AC(s) e o gate (teste) que a prova. TDD: teste vermelho → código → verde.

| # | Task | AC | Gate (teste) | Status |
|---|---|---|---|---|
| 1 | `schemas/saude.py`: modelos de resposta (`SaudeDeep`, seções banco/worker/envios/taxa/fila/gasto) | AC-2 | pytest importa + valida formato | todo |
| 2 | `core/config.py`: `tarifa_utility_brl = 0.035`; limiar worker 5 min como constante no módulo | AC-4,9,S2,S3 | referência nos testes | todo |
| 3 | `api/admin_health.py`: `GET /admin/health/deep` autenticado — banco (SELECT 1 degradável), worker (heartbeat), envios do dia por status, taxa do dia, fila, gasto do mês | AC-1..AC-9 | `test_admin_health.py`: 401; 200 com 6 seções; banco erro degrada; vivo/parado/desconhecido; envios por status (fronteira dia SP); taxa (50% e 0%); fila; gasto estimado | todo |
| 4 | Registrar router em `main.py` | AC-2 | smoke do app sobe com a rota | todo |
| 5 | Frontend `lib/api.ts`: `obterSaude()` + tipos da resposta | AC-10 | tsc | todo |
| 6 | Frontend `app/(app)/saude/page.tsx`: cartões das 6 seções, erro legível, 401→login | AC-10 | `page.test.tsx` (Vitest): render dos cartões + estado de erro | todo |
| 7 | `components/AppShell.tsx` + `icones.tsx`: item "Saúde" + ícone | AC-10 | teste do AppShell/eslint+tsc | todo |

## Gates finais (antes do PR)
- Backend: `ruff` + `mypy` + `pytest` (cobertura — endpoint novo 90%+ nas linhas de regra) + `pip-audit`.
- Frontend: `eslint` + `tsc` + `vitest` + `build` + `npm audit`.
- `/revisar` → `/seguranca` → `/validar` (AC-1..AC-10) → CI Docker completo. PR `feat/0021` → `develop`.

## Notas de implementação
- Reusar a semântica de falha/tentativa da 0019 (`worker/alertas.py`: `_FALHAS`, `_CONTAM_LIMITE`) para a taxa — extrair
  para um ponto comum se evitar duplicação, sem alterar o comportamento da 0019.
- Fronteira de dia/mês em SP: calcular `inicio_dia_sp`/`inicio_mes_sp` em UTC a partir de `America/Sao_Paulo` e filtrar por `Envio.criado_em`.
- `/admin/health/deep` é **read-only**; sem auditoria de escrita (nada muda de estado).
