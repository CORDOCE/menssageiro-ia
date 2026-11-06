---
name: tasks-modelos
description: Quebra de tasks da feature 0013-modelos. Cada task mapeia 1+ AC e aponta o comando de teste (gate) que a prova.
---

# Tasks: Modelos (ver templates e sincronizar com a Meta)

Gate da stack (frontend): `cd frontend && npm run lint && npx tsc --noEmit && npm test && npm run build`.

> **Bloqueado no gate de spec:** resolver as "Questões em aberto" (filtro/enviar-teste/confirmação/detalhe)
> antes de implementar o que depende delas.

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 1 | `lib/api.ts`: `sincronizarModelos()` → `{total,criados,atualizados}` (POST /modelos/sincronizar) | AC-3 | — | teste unit do cliente (fetch mockado) | todo |
| 2 | Selo de status de modelo (mapa aprovado/pendente/rejeitado/pausado/rascunho → tom) | AC-1 | — | teste unit do mapa | todo |
| 3 | Página `app/(app)/modelos/page.tsx`: carrega `listarModelos`, lista (nome/selo/categoria/idioma/prévia/variáveis); esqueleto + estado vazio | AC-1, AC-5, borda | 1,2 | teste de componente | todo |
| 4 | Filtro por status (recarrega `?status=`), se aprovado na Q1 | AC-2 | 3 | teste de componente | todo |
| 5 | Botão **Sincronizar** → chama `sincronizarModelos`, mostra total/criados/atualizados, recarrega; erro legível (500/401→login) + guarda de duplo clique | AC-3, AC-4 | 1,3 | teste de componente (sucesso + erros) | todo |
| 6 | Entrada no shell/nav (item "Modelos" do AppShell deixa de ser "Em breve") + smoke SSR | AC-1 | 3-5 | `npm run build` + smoke | todo |

## Definition of Done (resumo — detalhe no CLAUDE.md §9)
- [ ] Todo AC verde pelo **gate executável** (Vitest), não por inspeção
- [ ] `/revisar` sem P0/P1 e `/seguranca` sem Crítico/Alto, zero segredo
- [ ] Sem `SPEC_DEVIATION` aberto
- [ ] Commit limpo; PR com objetivo/risco/plano de teste
- [ ] Validado em staging (sincronizar lê da Meta — staging tem credenciais)
- [ ] `STATE.md` atualizado
