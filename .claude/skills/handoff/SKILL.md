---
name: handoff
description: Use ao PAUSAR/encerrar uma sessao (grava o estado atual em STATE.md pra retomar depois) ou ao RETOMAR (le STATE.md + a spec ativa e recompoe o contexto, propondo o proximo passo). Mantem a continuidade entre sessoes de humanos e de IA. Acione com /handoff.
---

# Skill: Handoff (pausar / retomar)

Garante que a proxima sessao — sua, de outra pessoa do time, ou de outra IA — comeca de onde esta,
sem reconstruir contexto na mao. Complementa o hook `SessionStart` (que carrega o STATE no inicio).

## Ao PAUSAR (encerrar a sessao)
Grave/atualize o `STATE.md` (na raiz, ou `docs/STATE.md` se o repo usa esse padrao) com:
- **Em andamento:** o que estava fazendo + a spec/feature ativa (`specs/NNNN-*`).
- **Proximo passo:** a primeira acao concreta de quem retomar.
- **Decisoes da sessao:** o que mudou e por que (decisao duravel -> ADR, nao STATE).
- **Bloqueios/pendencias:** o que trava + de quem depende.
- **Estado do git:** branch atual, se ha trabalho nao commitado, PR aberta.
Mensagem final curta: onde parou e qual o proximo passo.

## Ao RETOMAR
1. Leia o `STATE.md` (o hook ja injeta no inicio) e a `spec.md` da feature ativa.
2. Confira a branch (`git status`) e se ha PR aberta (`gh pr list`).
3. Proponha o **proximo passo** do STATE e confirme antes de agir.

Mantenha o STATE **curto e atual** — e memoria volatil, nao historico. Historico vive no git/ADR.
