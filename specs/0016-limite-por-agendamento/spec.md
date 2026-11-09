# Spec — 0016 Teto de segurança por agendamento (dívida R1-d)

Tier Arquitetural (regra de envio §5, migração, §4). Ver `product.md`, `design.md`, **ADR 0013**.
Novo controle `limite_por_agendamento_dia` na config: nenhum agendamento envia mais que o teto num disparo;
o excedente **não** é enviado e o agendamento vira **`parcial`** com auditoria/alerta.

## Regra (tabela-verdade) — cada linha vira teste
Sendo `T` = `limite_por_agendamento_dia`, `N` = contatos a enviar no disparo, `E` = envios já feitos do agendamento.

| T | N vs (T−E) | Resultado |
|---|---|---|
| `NULL` | — | envia todos; status `enviado` (comportamento atual, sem corte) |
| def. | `N ≤ T−E` | envia todos; status `enviado` |
| def. | `N > T−E` | envia exatamente `T−E`; excedente **não** enviado; status `parcial` + auditoria/alerta |

## Critérios de aceite (Given/When/Then)

**AC-1 — Sem teto (`NULL`) não corta.**
Given `limite_por_agendamento_dia = NULL` e um grupo de N contatos,
When o worker dispara o agendamento,
Then envia a **todos** os N; status `enviado` (comportamento atual preservado).

**AC-2 — Grupo dentro do teto.**
Given teto `T` e grupo com `N ≤ T` contatos (nenhum envio prévio),
When dispara,
Then envia a todos; status `enviado`; **sem** evento de corte.

**AC-3 — Grupo excede o teto → corta e marca `parcial`.**
Given teto `T` e grupo com `N > T` contatos,
When dispara,
Then envia **exatamente `T`**; os `N−T` restantes **não** têm envio criado; status do agendamento = **`parcial`**;
`motivo_ultima_transicao` descreve o corte.

**AC-4 — Corte emite auditoria/alerta (§7/§12).**
Given o cenário AC-3,
When o corte ocorre,
Then há auditoria `agendamento.limite_por_agendamento` (warning) com `{enviados, total, teto}` **sem PII**.

**AC-5 — `parcial` é terminal.**
Given um agendamento `parcial`,
When o worker roda de novo,
Then **não** reprocessa (não envia mais nada); `parcial` conta como estado terminal.

**AC-6 — Teto lido a cada ciclo.**
Given o operador altera `limite_por_agendamento_dia` na config,
When o próximo disparo ocorre,
Then usa o **novo** valor (sem redeploy), como os demais limites (§5.6).

**AC-7 — UI mostra `parcial`.**
Given um agendamento `parcial`,
When exibido na Agenda/Histórico,
Then tem selo próprio (texto "Parcial"), distinto de "Enviada"/"Não enviada".

## Casos de borda
- `N == T` (exato) → envia todos, `enviado` (não corta: não excedeu).
- `N == T+1` → envia `T`, `parcial`.
- Agendamento **individual** (N=1) com `T ≥ 1` → envia, `enviado` (teto não dispara).
- Interação com **global** (adia tudo antes) e **por-contato** (pula contato): ordem global → por-agendamento → por-contato.
- Idempotência: reprocesso não duplica; a contagem `E` usa envios existentes do agendamento.

## Fora de escopo
- Espalhar o grupo em vários dias; teto definível por agendamento; validação no POST.
- Pipeline de alerta §12 (dívida O1) — esta spec só **emite** o sinal.

## Definition of Ready
- [x] ACs testáveis (pytest no worker + vitest no selo). Tabela-verdade coberta. Migração com downgrade (/migracao). §4 aprovado (ADR 0013).
