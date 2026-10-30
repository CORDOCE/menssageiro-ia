---
name: validar
description: Use APOS implementar uma feature pra valida-la (UAT) — roda os gates de teste do repo, mapeia cada AC-N ao seu teste e aponta ACs sem cobertura, resolve SPEC_DEVIATION pendente, checa o Definition of Done e atualiza o STATE.md. Prova pelo gate executavel, nao por inspecao. Acione com /validar.
---

# Skill: Validar (UAT)

Fecha o loop SDD: prova que a implementacao cumpre a **spec**, pelo **gate executavel** — nunca
por inspecao visual. Rode depois de implementar (pode ser em outra sessao).

## Processo
1. **Identifique a feature** (`specs/NNNN-<nome>/`) e leia `spec.md` + `tasks.md`.
2. **Rode os gates da stack do repo** — o comando que o CI roda. Exemplos por stack:
   - Rust (AffiliPro/orbita/CIFRA): a skill `gate` (Docker: migrations + clippy + cobertura).
   - Node/TS (HTECH-EVOLVE/tidybee/UNIQO): `npm run test:coverage` (+ e2e/integration se houver).
   - Python/Node (fluxo-service/Craving): `npm run test:*` / `pytest` conforme o repo.
   Se nao souber o comando, ache no `CLAUDE.md`/`package.json`/`Cargo.toml`/CI.
3. **Mapeie `AC-N -> teste`** e mostre a tabela; **aponte qualquer AC sem cobertura ou falhando**.
   Se a spec tem tabela-verdade, **toda linha** precisa de teste.
4. **SPEC_DEVIATION:** resolva os pendentes — corrige o codigo (a spec vence) ou atualiza a spec
   conscientemente (ADR se dificil de reverter). Ramificou? Rode `/clarificar`.
5. **Definition of Done** (ver `CLAUDE.md`): AC verdes pelo gate, sem deviation aberto, cobertura
   ≥ minimo com relatorio, commit limpo, ADRs registrados.
6. **Atualize `STATE.md`** (proximo passo/decisoes) — ou rode `/handoff` pra encerrar.

## Saida
Veredito claro: **pronto pra PR** ou a lista do que falta (AC sem cobertura, deviation aberto, item
de DoD pendente). Lembre: o merge na `main` e via PR aprovada — nunca push direto.
