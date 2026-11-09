# Product — 0016 Teto de segurança por agendamento (dívida R1-d)

## Problema
Hoje o worker tem limite **global/dia** (`limite_diario`) e **por-contato/dia** (`limite_por_contato_dia`),
mas **não** há teto para o quanto **um único agendamento** pode disparar. Um agendamento de **grupo**
expande e envia para **todos** os contatos num ciclo só (`disparo.py:190` `for contato in contatos`).
Um grupo gigante por engano (import errado, grupo trocado) satura o dia e gasta cota da Meta antes de
qualquer humano perceber.

## Para quem
Operador/responsável (Jefferson e o cliente). É uma rede de proteção operacional, não um recurso de UX.

## Métrica de sucesso
- Nenhum agendamento envia mais que o teto configurado num disparo; o excedente **não** é enviado.
- Quando o teto corta um disparo, há **auditoria + sinal de alerta** (§7/§12) com contexto suficiente
  para o operador investigar (sem PII).

## Goals
- Teto configurável (um valor na config, aplicado a cada agendamento; `NULL` = sem teto).
- Ao atingir: envia até o teto, **para**, marca o agendamento e registra auditoria/alerta.
- Checado **a cada ciclo** a partir da config (§5.6), como os demais limites.

## Non-goals
- **Espalhar** o grupo em vários dias (descartado — seria outro produto).
- Teto **definível por agendamento** (coluna em `agendamentos` / campo no POST / UI) — fica para depois se preciso.
- Validação na criação (rejeitar grupo grande no POST).
- Implementar o pipeline de alerta O1/§12 em si (esta spec **emite o sinal**; o encanamento de alerta é a dívida O1).
