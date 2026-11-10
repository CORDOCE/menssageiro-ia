---
name: spec-tela-configuracoes
description: Spec da feature 0018-tela-configuracoes. A fonte da verdade — os critérios de aceite são o contrato e o oráculo de teste.
---

# Spec: Tela de Configurações (editar controles de envio pela UI)

## Contexto

Os controles de envio vivem na linha única `configuracoes` (`id="default"`), que o worker lê **a cada ciclo** (ADR 0008, §5.6). Hoje só é possível alterá-los via banco ou semente de env — o operador não tem como pausar envios, ajustar limites ou a janela sem acesso ao banco. Esta feature expõe esses controles numa tela autenticada, com validação e auditoria, sem mudar a **semântica** das regras de envio (janela/limites/pausa continuam significando o mesmo; muda só o meio de edição).

> Toca controles de envio (§4/§5) — **exige aprovação explícita do responsável** antes de implementar.

## Decisões (explícitas, confirmar no gate de review)

1. **Endpoints:** `GET /configuracoes` e `PATCH /configuracoes` (recurso singular, linha única `default`), ambos `dependencies=[Depends(usuario_atual)]`. Não há criação/exclusão.
2. **PATCH parcial:** o corpo aceita qualquer subconjunto dos 5 campos; só os presentes mudam (permite "pausar" mandando só `envios_pausados`). Corpo vazio → 422.
3. **Efeito:** a mudança vale **no próximo ciclo do worker** (ADR 0008); não há "aplicar agora".
4. **Janela no mesmo dia:** `fim > inicio` (sem cruzar meia-noite), alinhado ao `services/janela.py#dentro_da_janela` atual (`[inicio, fim)`). Uma janela única para todos os dias selecionados.
5. **Auditoria (§5.8):** todo PATCH válido registra `configuracao.atualizada` com os campos alterados (config não tem PII).
6. **Autorização:** usuário autenticado (admin único, ADR 0001). Sem papéis.
7. **UI:** rota `(app)/configuracoes`; ativa o item hoje "Em breve" no `AppShell`. Confirmação explícita (`window.confirm`) ao **ativar** a pausa geral.

## Critérios de aceite (o contrato)

- **AC-1** — Dado operador autenticado, Quando `GET /configuracoes`, Então 200 com os 5 campos da linha `default` (`janela_envio`, `limite_diario`, `limite_por_contato_dia`, `limite_por_agendamento_dia`, `envios_pausados`) + `atualizado_em`.
- **AC-2** — Dado request sem sessão válida (sem cookie), Quando `GET` ou `PATCH /configuracoes`, Então 401 JSON.
- **AC-3** — Dado operador autenticado, Quando `PATCH /configuracoes` com `limite_diario=500` válido, Então 200, valor persistido e o worker no ciclo seguinte lê 500 como limite diário (fonte runtime, ADR 0008).
- **AC-4** — Quando `PATCH` com `envios_pausados=true`, Então 200 e o worker, no ciclo seguinte, **não dispara envios** (retorna cedo por pausa, §5.6).
- **AC-5** — Quando `PATCH` com `janela_envio={"dias":[0,1,2,3,4],"inicio":"09:00","fim":"18:00"}` válido, Então 200 e a janela é persistida.
- **AC-6** — Quando `PATCH` com entrada inválida (ver [matriz](#matriz-de-decisão-validação-do-patch)), Então **422** e **nenhum** campo é alterado (nada persiste).
- **AC-7** — Quando `PATCH` com `limite_por_contato_dia=null` (ou `limite_por_agendamento_dia=null`), Então 200 e o limite é **removido** (sem limite), conforme semântica `NULL` do modelo.
- **AC-8** — Quando um `PATCH` válido altera ≥1 campo, Então grava auditoria `configuracao.atualizada` com os campos alterados e **sem PII** (§5.8).
- **AC-9** — Quando `PATCH` com corpo vazio `{}` (nenhum campo), Então 422 ("nenhum campo para atualizar"); nada muda e não gera auditoria.
- **AC-10** — Dado operador logado, Quando abre `/configuracoes`, Então o formulário vem preenchido com os valores atuais; ao salvar chama `PATCH` e mostra feedback de sucesso; ao **ativar** a pausa pede confirmação; erro do backend aparece legível; 401 → redireciona a `/login`.

## Casos de borda

- `limite_diario` ausente num PATCH que muda só a janela → mantém o valor atual (parcial).
- Janela com `dias` fora de ordem (ex.: `[5,0,2]`) → aceita e normaliza (ordena); duplicados → 422.
- Horas com segundos (`"08:00:00"`) → 422 (formato é `HH:MM`).
- Valores de limite muito grandes → cap defensivo (ex.: `limite_diario ≤ 100000`) → acima disso 422 (§6, evita absurdo/overflow de intenção).
- Ativar a pausa não cancela nem apaga agendamentos; só impede o disparo enquanto pausado.
- Reverter a pausa (`envios_pausados=false`) retoma no ciclo seguinte.

## Fora de escopo (vinculante)

- Múltiplos perfis de configuração (só a linha única `default`).
- Janela cruzando a meia-noite (`fim ≤ inicio`) ou janela distinta por dia da semana.
- Pausa agendada (pausar/retomar automático por horário).
- Histórico/rollback de versões da config na UI (a auditoria já registra as mudanças).
- Editar `OPENAI_MODEL`, prompts, assuntos ou verificações da IA (regra de resposta §4 — spec própria; a IA nem existe ainda).
- Semear/alterar variáveis de ambiente pela UI.

## Matriz de decisão (validação do PATCH)

Cada linha vira um teste (AC-6, exceto as marcadas ok).

| campo | entrada | resultado |
|---|---|---|
| `janela_envio.dias` | `[0,1,2,3,4,5]` | ok |
| `janela_envio.dias` | `[]` (vazio) | 422 |
| `janela_envio.dias` | `[7]` ou `[-1]` (fora de 0..6) | 422 |
| `janela_envio.dias` | `[0,0,1]` (duplicado) | 422 |
| `janela_envio` inicio/fim | `"09:00"`/`"18:00"` | ok |
| `janela_envio` inicio/fim | `"18:00"`/`"09:00"` (fim ≤ inicio) | 422 |
| `janela_envio` inicio | `"25:00"` / `"8:0"` / `"08:00:00"` | 422 |
| `limite_diario` | `1` | ok |
| `limite_diario` | `0` ou negativo | 422 |
| `limite_diario` | `null` (campo NOT NULL) | 422 |
| `limite_diario` | `> 100000` | 422 |
| `limite_por_contato_dia` | `null` | ok (remove limite) |
| `limite_por_contato_dia` | `0` | 422 |
| `limite_por_agendamento_dia` | `null` | ok (remove teto) |
| corpo PATCH | `{}` (vazio) | 422 |
