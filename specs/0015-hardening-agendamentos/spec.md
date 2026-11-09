# Spec — 0015 Hardening da API de agendamentos (dívida R1)

Tier Pequeno. Dois endurecimentos de validação no `POST /agendamentos`, sem tocar regra de envio
nem schema do banco. Follow-ups do PR #22 (dívida R1).

## Contexto / re-verificação (evidência, 2026-11-09)
A dívida R1 listava 4 itens; re-verificados no código:
- **(a) `contato_id` inexistente → 500** — CONFIRMADO: `api/agendamentos.py` `criar()` valida `modelo_id`
  (404) mas **não** `contato_id`; FK viola no `commit` → 500.
- **(c) `variaveis` sem cap** — CONFIRMADO: `schemas/agendamento.py` `AgendamentoCriar.variaveis: list[str]`
  sem limite de itens/tamanho.
- **(b) N+1 na listagem** — **DESCARTADO**: `Agendamento` não tem `relationship`; `listar()` faz um único
  `select(Agendamento)` e `AgendamentoRead` expõe só ids (nenhum lazy-load). Não se materializa.
- **(d) limite diário por-agendamento** — **FORA** desta spec: toca regra de envio (invariante §5),
  exige aprovação §4 e migração. Vira spec própria (decisão de Jefferson, 2026-11-09).

## Decisões (suposições explícitas e reversíveis, §1.4)
- (a) código HTTP = **404 "Contato não encontrado"**, consistente com o 404 de modelo no mesmo endpoint.
- (c) cap defensivo (§6) = **máx. 50 variáveis, cada ≤ 1000 caracteres** (folgado p/ templates reais).

## Critérios de aceite (Given/When/Then)

**AC-1 — `contato_id` inexistente → 404 (não 500).**
Given o operador autenticado e um `contato_id` que não existe,
When `POST /agendamentos` com esse `contato_id` (e `modelo_id` válido),
Then retorna **404 "Contato não encontrado"** e **nenhum** agendamento é criado.

**AC-2 — contato válido segue criando (não regrediu).**
Given um `contato_id` existente e `modelo_id` válido,
When `POST /agendamentos`,
Then retorna **201** com o agendamento (caminho feliz intacto).

**AC-3 — `variaveis` acima do cap → 422.**
Given o operador autenticado,
When `POST /agendamentos` com `variaveis` contendo **>50 itens** OU algum item **>1000 chars**,
Then retorna **422** (validação Pydantic) e nada é criado.

**AC-4 — `variaveis` dentro do cap → ok.**
Given `variaveis` com até 50 itens, cada ≤ 1000 chars (inclui lista vazia),
When `POST /agendamentos`,
Then é aceito (201) — o cap não atrapalha uso legítimo.

## Casos de borda
- `grupo` informado (sem `contato_id`) → a validação de contato **não** dispara (xor já tratado, AC-4 da 0004).
- Limite exato: 50 itens / 1000 chars → aceito; 51 itens / 1001 chars → 422.
- `variaveis` vazia → aceito.

## Fora de escopo
- (b) N+1 (inexistente), (d) limite diário por-agendamento (spec futura, §4 + migração).
- Limite diário **global** (já existe, spec 0004); qualquer mudança de schema.

## Definition of Ready
- [x] AC testáveis (pytest sobre o endpoint). Non-goals explícitos. Sem migração, sem §4.
