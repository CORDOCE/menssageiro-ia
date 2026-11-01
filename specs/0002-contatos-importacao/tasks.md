---
name: tasks-contatos-importacao
description: Quebra de tasks da feature 0002-contatos-importacao. Cada task mapeia 1+ AC e aponta o comando de teste (gate) que a prova.
---

# Tasks: Contatos + importação (Fase 2 do Mensageiro)

**Pré-condições (não são tasks desta feature):**
- Task 5 (auth) **mergeada em `develop`** — fornece `usuario_atual`, `core/audit`, `models/`, `schemas/` e a migration `ab30d72b78e4`.
- Aprovação §4 das libs `phonenumbers` + `openpyxl` (ADR 0006) antes das tasks marcadas `[dep]`.

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 1 | `models/contato.py` + `schemas/contato.py` (campos BRIEFING §9; `tags` JSONB; `consentimento` default false) | AC-1 | task 5 | `ruff check .` + `mypy app` → 0; teste que instancia o modelo | todo |
| 2 | Migration Alembic aditiva: tabela `contatos` + índice único `telefone_e164` | AC-19 | 1 | `alembic upgrade head && alembic downgrade base` → 0 (via `/migracao`) | todo |
| 3 | `core/telefone.py`: `normalizar_e164` (phonenumbers) + `mascarar_telefone` `[dep]` | AC-1, AC-16 | — | teste unit: normalização (variações BR) + máscara | todo |
| 4 | `api/contatos.py` CRUD protegido: POST/GET(lista+filtros)/GET{id}/PATCH | AC-1..AC-6, AC-18 | 1,3 | testes: 201/422/409, 401 sem auth, filtros, PATCH | todo |
| 5 | Endpoint `POST /contatos/{id}/descadastrar` (soft, imediato) | AC-7 | 4 | teste: `descadastrado_em` setado; contato permanece/bloqueado | todo |
| 6 | Endpoint `POST /contatos/{id}/consentimento` | AC-8 | 4 | teste: opt-in registrado (bool+data+origem) | todo |
| 7 | `services/contatos_import.py`: parse CSV+XLSX, validação, consentimento, upsert, skip-descadastrado, relatório `[dep]` | AC-9..AC-16 | 1,3 | testes da **matriz de decisão** + casos de borda | todo |
| 8 | `POST /contatos/importar` (multipart) + limites de tamanho/linhas | AC-9,10,11,17,18 | 7 | testes: parcial por linha, limite → 413/422, 401 sem auth | todo |
| 9 | Mascaramento aplicado em log/auditoria da feature (sem PII) | AC-16 | 3,4,7 | teste: captura log/auditoria e verifica máscara; sem lista de telefones | todo |
| 10 | Suíte + cobertura ≥90% das regras (E.164, consentimento, dedup, descadastro) | AC-20 | 1–9 | `pytest --cov` → 0 e cobertura ≥90% das regras | todo |
| 11 | Dependências: `phonenumbers` + `openpyxl` no `pyproject` (versão fixada) + `pip-audit` `[dep]` | — | aprovação §4 | `pip-audit` sem vulnerabilidades | todo |
| 12 | ADR 0006 (E.164/phonenumbers + openpyxl) em `docs/decisoes/` | — | aprovação §4 | arquivo presente e linkado no `design.md` | todo |

> `[dep]` = bloqueada até a aprovação §4 das dependências. CI: reaproveita o `ci.yml` da Fase 1 (task 12 da spec 0001); nenhum workflow novo.

## Ordem de execução sugerida
1 → 2 → 3 → (4 → 5 → 6) e 7 → 8 em paralelo onde possível → 9 → 10. Tasks 11/12 assim que a aprovação §4 sair.
Migração (task 2) via `/migracao`. Antes do PR: `/revisar` → `/seguranca` → `/validar` + suíte de CI no host via Docker (CLAUDE.md §4.4).

## Definition of Done (resumo — detalhe no CLAUDE.md §9)
- [ ] Todo AC verde pelo **gate executável** (matriz de decisão coberta linha a linha)
- [ ] Cobertura ≥ 90% nas regras; relatório anexado ao PR
- [ ] `/revisar` sem P0/P1 e `/seguranca` sem Crítico/Alto (atenção a upload/arquivo e PII em log), zero segredo
- [ ] Sem `SPEC_DEVIATION` aberto; invariantes §5.4 (descadastro) e §5.9 (consentimento) provados por teste
- [ ] Commit limpo (zero co-autoria); PR com objetivo/risco/plano de teste; ADR 0006 presente
- [ ] Validado em staging (importação de planilha com validação; nenhum envio)
- [ ] `STATE.md` atualizado
