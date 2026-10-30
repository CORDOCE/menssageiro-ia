---
name: nova-feature
description: Abre uma nova feature no padrao H.Tech SDD. Decide o tier (trivial/pequeno/arquitetural), cria specs/NNNN-<nome>/ a partir dos templates e conduz o preenchimento pelos gates (product -> design -> spec -> tasks), parando pra review em cada um. A spec e o contrato. Acione com /nova-feature.
---

# Skill: Nova feature (loop SDD)

Abre e conduz uma feature pela esteira. A **spec e o contrato**; preencha na ordem dos gates e
**pare em cada gate pra review**. Siga as regras do `CLAUDE.md` (dev-first, zero co-autoria).

## Fase 1 — Identidade
1. Proximo numero: maior `NNNN` em `specs/` + 1 (4 digitos). Pasta `specs/NNNN-<nome-kebab>/`.
2. Garanta que voce esta numa branch `dev`/feature — **nunca** comece na `main`.

## Fase 2 — Tier (gate)
Pergunte: **"isso introduz decisao dificil de reverter ou nova fronteira de dominio?"**

| Resposta | Tier | Artefatos |
|---|---|---|
| Nao, trivial (≤3 arquivos) | Trivial | so o PR (ou `specs/quick/` pra deixar rastro) |
| Nao, feature isolada | Pequeno | `spec.md` + `tasks.md` |
| Sim | Arquitetural | `product.md` + `design.md` + `spec.md` + `tasks.md` + ADR |

Na duvida, promova de tier. Copie os templates de `specs/_templates/`.

## Fase 3 — Preencher de cima pra baixo (pare em cada gate)
1. **product.md** (arquitetural): problema, pra quem, metrica de sucesso, goals/non-goals.
2. **design.md** (arquitetural): solucao + alternativas + trade-offs + riscos. Respeite a
   arquitetura **ja existente** do repo (nao imponha padrao novo). Decisao irreversivel -> ADR.
3. **spec.md** (sempre): AC em Given/When/Then, casos de borda, **fora de escopo**. Gate
   *Definition of Ready*: cada AC e testavel e nao-ambiguo? Algum "como se comporta quando..."
   em aberto? **Rode `/clarificar`** antes de gravar. Regra que combina flags/estados? Use
   tabela-verdade (cada linha vira teste).
4. **tasks.md** (sempre): cada task mapeia 1+ AC + o comando de teste (gate) que a prova.

## Fase 4 — Pronto pra implementar
- Cheque o Definition of Ready (AC testaveis, non-goals, design aprovado se arquitetural).
- Implemente respeitando a stack do repo, **um teste por AC**. Rode o gate da stack a cada passo
  (ex.: skill `gate` em Rust, `npm run test:coverage` em Node, `node --test`/pytest conforme o repo).
- Ofereca commit dos artefatos da spec (na `dev`, mensagem limpa).

## Fase 5 — Validacao
Depois de implementar (pode ser em outra sessao), rode **`/validar`** (UAT: AC->teste, DoD,
SPEC_DEVIATION) e **`/handoff`** se for pausar.
