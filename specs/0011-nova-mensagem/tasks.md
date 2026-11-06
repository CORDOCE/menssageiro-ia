---
name: tasks-nova-mensagem
description: Quebra de tasks da feature 0011-nova-mensagem. Cada task mapeia 1+ AC e aponta o comando de teste (gate) que a prova.
---

# Tasks: Nova mensagem (criar agendamento pela UI)

Gate da stack (frontend): `cd frontend && npm run lint && npx tsc --noEmit && npm test && npm run build`
(`npm test` = `vitest run`, infra adicionada na task 0 — o frontend não tinha framework de teste).

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 0 | Infra de teste do frontend: `vitest`+`@testing-library/react`+`@testing-library/jest-dom`+`jsdom` (devDeps), `vitest.config.ts`, script `test`, step no `ci.yml` | — (habilita todas) | — | `npm test` (verde vazio) | todo |
| 1 | Cliente de API: `listarModelos({status})` e `criarAgendamento(dados)` em `lib/api.ts` (tipos `Modelo`, `AgendamentoCriar`) | AC-1, AC-4 | 0 | `npx tsc --noEmit` + teste unit do cliente (fetch mockado) | todo |
| 2 | Util de data: horário local America/Sao_Paulo → ISO-8601 com offset (UTC) para `executar_em` | AC-4 | — | teste unit do util (casos de borda de fuso/DST) | todo |
| 3 | Seletor de modelo (só aprovados, ordenado) + prévia do `corpo` + estado vazio | AC-1, borda | 1 | teste de componente (cliente mockado) | todo |
| 4 | Campos de variável dinâmicos conforme `variaveis[]` (recria ao trocar modelo; 0 var = nenhum campo) | AC-2, borda | 3 | teste de componente | todo |
| 5 | Seletor de contato elegível (consentimento + não descadastrado) + estado vazio | AC-3, borda | 1 | teste de componente | todo |
| 6 | Validação de formulário + habilitação do botão (matriz de decisão) | AC-5 | 3,4,5 | teste de componente (uma linha da matriz por caso) | todo |
| 7 | Submissão: monta payload, chama `criarAgendamento`, trata 201/erros (422/limite/401→login) sem perder preenchimento | AC-4, AC-6 | 1,2,6 | teste de componente (sucesso + cada erro) | todo |
| 8 | Pós-sucesso: confirmação + "criar outra" (limpa) / "voltar" | AC-7 | 7 | teste de componente | todo |
| 9 | Rota/entrada da tela no shell + smoke SSR (render autenticado, sem flash) | todos | 3-8 | `npm run build` + smoke SSR | todo |

> `[P]` = pode rodar em paralelo. Tasks 3/5 são [P] após a 1.

## Definition of Done (resumo — detalhe no CLAUDE.md §9)
- [ ] Todo AC verde pelo **gate executável** (não por inspeção)
- [ ] Cobertura ≥ mínimo do repo; relatório anexado ao PR
- [ ] `/revisar` sem P0/P1 e `/seguranca` sem Crítico/Alto, zero segredo (atenção: variável = dado não confiável, §6)
- [ ] Sem `SPEC_DEVIATION` aberto
- [ ] Commit limpo (zero co-autoria, zero segredo); PR com objetivo/risco/plano de teste
- [ ] Validado em staging (toca criação de agendamento → fluxo de envio)
- [ ] `STATE.md` atualizado
