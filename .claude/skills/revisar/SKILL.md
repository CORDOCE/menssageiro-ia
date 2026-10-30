---
name: revisar
description: Code review do diff ANTES da PR — caca bug de correcao, aderencia aos AC da spec e oportunidades de reuso/simplificacao. Veredito bloqueante por severidade (P0/P1 travam o PR). Prova as suspeitas no codigo em vez de chutar; quando achar pouco, prefere poucos achados de alta confianca. Roda em par com /seguranca. Acione com /revisar.
---

# Skill: Revisar (code review)

Segunda opiniao critica sobre o que voce **acabou de escrever**, antes de abrir PR. O objetivo nao e
elogiar: e **achar o que esta errado** enquanto e barato consertar. Revise o **diff**, nao o repo todo.

## Escopo da revisao
1. **Pegue o diff.** `git diff` (nao-commitado) ou `git diff <base>...HEAD` (branch da feature vs `dev`/`main`).
   Se nao houver diff, pergunte qual mudanca revisar.
2. Revise **so o que mudou** + o que o mudado afeta de perto. Nao audite codigo intocado.

## O que procurar (em ordem de prioridade)
- **Correcao** (P0/P1): a logica faz o que a spec pede? Off-by-one, condicao invertida, `null`/`undefined`,
  promessa nao-aguardada, caso de borda da spec sem tratamento, erro engolido, recurso nao fechado,
  estado compartilhado mutado, regex/parsing fragil. **Race**/concorrencia onde houver async.
- **Aderencia a spec** (P0): cada **AC** da `spec.md` tem codigo que o cumpre? Algo **fora de escopo** foi
  implementado? Algum `SPEC_DEVIATION` nao registrado? Se a spec tem matriz-verdade, toda linha esta coberta?
- **Teste** (P1): existe um teste por AC e ele realmente *poderia falhar* (nao e tautologico)? O gate cobre o caminho mudado?
- **Reuso / simplificacao** (P2): duplicou algo que ja existe no repo? Da pra usar um util/abstracao existente?
  Dah pra remover indireção/branch morto? **Respeite os padroes do repo** — nao imponha estilo novo.
- **Eficiencia** (P2): N+1, loop que poderia ser uma query, alocacao em hot-path, recomputo evitavel.

## Como conduzir (nao chute)
- **Prove cada suspeita** lendo o codigo ao redor (definicao da funcao, chamadas, tipos). Achado que voce
  nao conseguiu confirmar -> marque como **"a verificar"**, nao como bug.
- Severidade honesta: **P0** quebra/risco de dados · **P1** bug provavel/AC nao cumprido · **P2** qualidade.
- Poucos achados certeiros > muitos palpites. Se esta limpo, **diga que esta limpo**.

## Saida
Lista por severidade, cada item com **arquivo:linha + por que esta errado + correcao sugerida**:

```
P0  src/x.ts:42  — <bug>; AC-3 nao e cumprido quando <caso>. Corrigir: <como>.
P1  ...
P2  ...
```

Feche com **veredito**: `PRONTO PRA PR` (sem P0/P1) **ou** `BLOQUEADO` + a lista do que travar.
Depois rode **`/seguranca`** (review de seguranca) e so entao **`/validar`** (gate + DoD).
Aplicou correcoes? Re-rode o diff. Lembre: merge na `main` so via PR aprovada.
