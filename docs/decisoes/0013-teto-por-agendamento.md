# ADR 0013 — Teto de segurança por agendamento (limite diário por disparo)

- **Status:** aceito
- **Data:** 2026-11-09
- **Contexto da feature:** dívida R1-d (`specs/0016-limite-por-agendamento`); regra fechada na sabatina
  `/clarificar` de 2026-11-09.
- **Aprovação:** é mudança em **regra de envio** (CLAUDE.md §4/§5) — decisões abaixo **aprovadas por Jefferson**
  no `/clarificar` (2026-11-09).

## Contexto
O worker já aplica limite **global/dia** (`limite_diario`) e **por-contato/dia** (`limite_por_contato_dia`),
mas nada limita quanto **um único agendamento** dispara. Um agendamento de grupo expande e envia a **todos** os
contatos num ciclo (`disparo.py` `for contato in contatos`); um grupo gigante por engano satura o dia e gasta
cota da Meta antes de um humano perceber. Falta uma rede de proteção por disparo.

## Decisão
1. **Novo controle na config:** `configuracoes.limite_por_agendamento_dia: int | None` (`NULL` = **sem teto**),
   espelhando `limite_por_contato_dia`. Semeado pela env opcional `LIMITE_POR_AGENDAMENTO` (como `LIMITE_DIARIO`
   semeia `limite_diario`). Lido **a cada ciclo** (§5.6) — operador muda sem redeploy.
2. **Ao exceder: parar, não espalhar.** No disparo, se os envios daquele agendamento alcançarem o teto, envia
   **até o teto**, **não** envia o excedente e **para**. *Não* re-enfileira para os dias seguintes (espalhar foi
   descartado — seria outro produto).
3. **Status terminal novo `parcial`.** Distingue de `enviado` (tudo) e `falhou` (nada). `motivo_ultima_transicao`
   descreve o corte ("teto por-agendamento atingido — N de M"). É **terminal** (não reprocessa).
4. **Auditoria + sinal de alerta:** evento `agendamento.limite_por_agendamento` (warning) com
   `{enviados, total, teto}` (sem PII) + log com `correlation_id`. O pipeline de alerta (§12) é a dívida O1 —
   esta decisão só **emite o sinal**.

## Alternativas
- **Espalhar o grupo em vários dias** (reusando idempotência): preserva tudo, mas vira "campanha fracionada" —
  não protege de acidente (só atrasa o dano). Rejeitado (non-goal).
- **Reusar `enviado`+motivo** em vez de `parcial`: menos invasivo, mas `enviado` mente e o corte some na visão
  por status. Rejeitado.
- **Teto por agendamento (coluna em `agendamentos` + POST + UI)**: mais flexível; adiado — o caso é proteção
  global e um valor na config basta.

## Consequências
- Toca a **UI** (selo de `parcial` na Agenda/Histórico) e o conjunto de **status terminais** no worker/API —
  mapear todos os pontos para não deixar `parcial` órfão.
- Default `NULL` (sem teto) → comportamento inalterado até o operador configurar; mudar o valor exige **§4**.
- A contagem usa `COUNT(envios do agendamento)` → idempotente sob reprocesso; corte determinístico exige ordem
  estável dos contatos.
