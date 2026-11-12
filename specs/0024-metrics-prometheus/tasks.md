---
name: tasks-metrics-prometheus
description: Quebra de tasks da feature 0024-metrics-prometheus. Cada task mapeia 1+ AC e aponta o gate que a prova.
---

# Tasks: 0024 Expor `/metrics` protegido por token

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 1 | Dependência `prometheus-fastapi-instrumentator` em `pyproject.toml` + `uv lock`/`uv sync` | — | — | `cd backend && uv run python -c "import prometheus_fastapi_instrumentator"` | todo |
| 2 | Setting `metrics_token: str \| None` em `app/core/config.py` (sem default real) | S1/S2 | 1 | `cd backend && uv run python -c "from app.core.config import Settings; Settings()"` | todo |
| 3 | Guarda de token `verificar_token_metrics` (compara com `secrets.compare_digest`) | AC-5 | 2 | `cd backend && uv run pytest tests/test_metrics.py -k timing` | todo |
| 4 | Instrumentar o app + registrar `/metrics` guardado **só** se `metrics_token` setado (`main.py`); `include_in_schema=False` | AC-1..4, AC-6, AC-7 | 3 | `cd backend && uv run pytest tests/test_metrics.py` | todo |
| 5 | `.env.example`: documentar `METRICS_TOKEN` (comentário de uso pela central) | — | 2 | `grep -q METRICS_TOKEN backend/.env.example` (ou raiz, onde vive o exemplo) | todo |
| 6 | Testes `tests/test_metrics.py`: 1 por AC (401 sem token, 401 errado, 200+corpo, 404 sem token, timing, famílias de métrica, fora do OpenAPI) | AC-1..7 | 4 | `cd backend && uv run pytest tests/test_metrics.py -q` | todo |

> `[P]` na frente de uma task = pode rodar em paralelo. (nenhuma marcada: cadeia curta e sequencial)

## Pontos a verificar na implementação (regra §1.3 do CLAUDE.md: não inventar comportamento de lib)
- **API real do `prometheus-fastapi-instrumentator`**: confirmar como expor com auth — se
  `Instrumentator.expose(app, dependencies=[...])` existe, ou se é preciso rota custom chamando
  `prometheus_client.generate_latest()`. Decidir lendo a lib instalada, não de memória.
- **Nomes exatos das métricas** que a central consome (AC-3/AC-6): confirmar no corpo real do `/metrics`
  gerado (`http_requests_total`, `http_request_duration_seconds`), não assumir.
- **Idempotência do registro** no `CollectorRegistry` entre instâncias de app na suíte.

## Definition of Done (resumo — detalhe no CLAUDE.md §4)
- [ ] Todo AC verde pelo **gate executável** (pytest), não por inspeção
- [ ] Cobertura ≥ mínimo do repo, relatório anexado ao PR
- [ ] `/revisar` passou (sem P0/P1) e `/seguranca` passou (sem Crítico/Alto, zero segredo)
- [ ] Sem `SPEC_DEVIATION` aberto
- [ ] Commit limpo (**zero co-autoria de IA**, zero segredo); PR com objetivo/risco/plano de teste
- [ ] `STATE.md` atualizado
- [ ] **Fora da DoD desta spec** (passos manuais seus, pós-merge): `METRICS_TOKEN` na Railway + deploy;
      fiação na central (`novo-sistema.sh mensageiro-ia …`, `segredos/…`, `recarregar.sh`)
