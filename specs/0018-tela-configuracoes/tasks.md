---
name: tasks-tela-configuracoes
description: Quebra de tasks da feature 0018-tela-configuracoes. Cada task mapeia 1+ AC e aponta o comando de teste (gate) que a prova.
---

# Tasks: Tela de Configurações

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 1 | Schema `ConfiguracaoRead` + `ConfiguracaoPatch` (Pydantic): validação de janela (dias 0..6 `StrictInt` não-vazios/únicos, `HH:MM`, `fim>inicio`), limites (≥1, cap 100000, opcionais `null`), `null` nos 3 campos NOT NULL rejeitado, rejeita corpo vazio | AC-6, AC-7, AC-9 | — | `uv run pytest backend/tests/test_configuracoes_schema.py` | ✅ feito |
| 2 | Router `api/configuracoes.py`: `GET /configuracoes` + `PATCH /configuracoes` (parcial), `Depends(usuario_atual)`; registra em `main.py`; reusa `services/janela.py#obter_configuracao` | AC-1, AC-2, AC-3, AC-5 | 1 | `uv run pytest backend/tests/test_configuracoes_api.py` | ✅ feito |
| 3 | Auditoria `configuracao.atualizada` com **diff real** (só campos alterados + valores, sem PII; no-op não audita) via `core/audit.registrar_auditoria` — **consolidada na task 2** | AC-8 | 2 | `uv run pytest backend/tests/test_configuracoes_api.py -k auditoria` | ✅ feito |
| 4 | Teste de integração worker: `envios_pausados=true` → ciclo não dispara; `limite_diario` novo é respeitado (fonte runtime) | AC-3, AC-4 | 2 | `uv run pytest backend/tests/test_worker_disparo.py -k config` | todo |
| 5 | [P] Frontend `lib/api.ts`: tipo `Configuracao`, `obterConfiguracao()`, `atualizarConfiguracao(patch)` | AC-10 | 2 | `npm test -- lib/api.test.ts` | todo |
| 6 | [P] Tela `app/(app)/configuracoes/page.tsx` + form (pausa c/ confirmação, 3 limites, janela: 7 checkboxes + 2 horas); ativa item no `AppShell`; `IconeConfiguracoes` | AC-10 | 5 | `npm test -- 'app/(app)/configuracoes'` | todo |
| 7 | Gate completo: CI backend (ruff/mypy/pytest ≥90%) + frontend (eslint/tsc/vitest/build) via Docker; `/revisar` + `/seguranca` + `/validar` | todos | 1-6 | suíte CI completa (`.github/workflows/ci.yml`) | todo |

> `[P]` = pode rodar em paralelo. Sem migração (todos os campos já existem no modelo `Configuracao`).
> Tasks 1-3 ✅ (backend). AC-4 persistido no endpoint; o efeito no ciclo do worker é a task 4.

## Definition of Done (resumo — detalhe no CLAUDE.md)
- [ ] Todo AC verde pelo **gate executável** (não por inspeção)
- [ ] Cobertura ≥ 90% (regras de envio); relatório anexado ao PR
- [ ] `/revisar` passou (sem P0/P1) e `/seguranca` passou (sem Crítico/Alto, zero segredo)
- [ ] Sem `SPEC_DEVIATION` aberto
- [ ] Commit limpo (zero co-autoria, zero segredo); PR com objetivo/risco/plano de teste
- [ ] **Aprovação explícita do responsável** registrada (controles de envio, §4)
- [ ] Validado em **staging** (toca regra de envio: pausar/retomar + limite pela UI)
- [ ] `STATE.md` atualizado
