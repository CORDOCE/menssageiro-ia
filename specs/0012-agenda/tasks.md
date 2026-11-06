---
name: tasks-agenda
description: Quebra de tasks da feature 0012-agenda. Cada task mapeia 1+ AC e aponta o comando de teste (gate) que a prova.
---

# Tasks: Agenda (gerenciar agendamentos pela UI)

Gate da stack (frontend): `cd frontend && npm run lint && npx tsc --noEmit && npm test && npm run build`
(infra Vitest já existe desde a 0011).

> **Bloqueado no gate de spec:** resolver as "Questões em aberto" (filtros/paginação/confirmação/reenviar)
> antes de implementar as tasks que dependem delas (T5, T6).

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 1 | `lib/api.ts`: `cancelarAgendamento(id)`, `reenviarAgendamento(id)`, `cancelarSerie(id)` (retorna `{cancelados}`) | AC-3,4,5 | — | teste unit do cliente (fetch mockado) | ✅ feito |
| 2 | Página `app/(app)/agenda/page.tsx`: carrega `listarAgendamentos` + `listarContatos` (mapa de nomes), lista ordenada com destino/selo/data-hora/recorrência; esqueleto + estado vazio | AC-1, AC-7, borda | 1 | teste de componente (cliente mockado) | ✅ feito |
| 3 | Filtro por status (recarrega com `?status=`; "Todos" sem filtro) + (período, se aprovado na Q1) | AC-2 | 2 | teste de componente (cada filtro) | ✅ feito |
| 4 | Ação **Cancelar** (não-terminal; confirma; atualiza linha) — ausente em terminal | AC-3, borda | 2 | teste de componente | ✅ feito |
| 5 | Ações **Reenviar** (só `aguardando_decisao`) e **Cancelar série** (só recorrente; mostra `{cancelados}`) | AC-4, AC-5 | 2 | teste de componente | ✅ feito |
| 6 | Tratamento de erro das ações (409 legível + recarrega; 401→login) + guarda de duplo clique | AC-6, borda | 4,5 | teste de componente (cada erro) | ✅ feito |
| 7 | Entrada no shell/nav (item "Agenda" do AppShell deixa de ser "Em breve") + smoke SSR | AC-1 | 2-6 | `npm run build` + smoke | ✅ feito |

## Definition of Done (resumo — detalhe no CLAUDE.md §9)
- [ ] Todo AC verde pelo **gate executável** (Vitest), não por inspeção
- [ ] `/revisar` sem P0/P1 e `/seguranca` sem Crítico/Alto, zero segredo
- [ ] Sem `SPEC_DEVIATION` aberto
- [ ] Commit limpo (zero co-autoria, zero segredo); PR com objetivo/risco/plano de teste
- [ ] Validado em staging (toca estado de agendamento — cancelar/reenviar)
- [ ] `STATE.md` atualizado
