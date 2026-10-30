---
name: tasks-<slug>
description: Quebra de tasks da feature <NNNN-nome>. Cada task mapeia 1+ AC e aponta o comando de teste (gate) que a prova.
---

# Tasks: <titulo>

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 1 |      | AC-1     | —          |                          | todo   |

> `[P]` na frente de uma task = pode rodar em paralelo (delegavel a subagente).

## Definition of Done (resumo — detalhe no CLAUDE.md)
- [ ] Todo AC verde pelo **gate executavel** (nao por inspecao)
- [ ] Cobertura ≥ minimo do repo, relatorio anexado ao PR
- [ ] `/revisar` passou (sem P0/P1) e `/seguranca` passou (sem Critico/Alto, zero segredo)
- [ ] Sem `SPEC_DEVIATION` aberto
- [ ] Commit limpo (zero co-autoria, zero segredo); PR com objetivo/risco/plano de teste
- [ ] `STATE.md` atualizado
