# Spec — 0014 Histórico de envios

Tier Pequeno. Tela do PWA (Fase 5) que lista os **envios realizados** para auditoria. Backend novo
**`GET /envios`** (read-only, molde de `GET /agendamentos`) + tela `historico` no frontend. Modelo
`Envio` já existe (**sem migração**).

## Resumo de entendimento (/clarificar, 2026-11-09, Jefferson)
- **Contato:** o endpoint faz join e devolve **nome + telefone** do contato (Histórico é paginado;
  resolver no front não escala).
- **Filtros v1:** **status** (criado/enviando/enviado/entregue/lido/falhou — `webhook_meta.py:34`) **+ período** (desde/até).
- **Campos por linha:** contato, modelo, status, data/hora e **motivo do erro** (só quando `falhou`).
  `pricing`/`conversation` **fora** da v1.

## Critérios de aceite (Given/When/Then)

**AC-1 — Lista envios (autenticado), mais recentes primeiro.**
Given o operador autenticado e envios no banco,
When `GET /envios`,
Then 200 com lista paginada ordenada por `criado_em` **desc**, cada item com
`id, contato_id, contato_nome, contato_telefone, modelo_id, modelo_nome, status, erro_codigo, erro_motivo, criado_em`.

**AC-2 — Filtro por status.**
Given envios com status variados,
When `GET /envios?status=falhou`,
Then retorna **apenas** os de status `falhou`.

**AC-3 — Filtro por período.**
Given envios em datas variadas,
When `GET /envios?desde=<ts>&ate=<ts>`,
Then retorna **apenas** os com `criado_em` dentro de `[desde, ate]` (limites inclusivos).

**AC-4 — Join traz contato e modelo.**
Given um envio com contato e modelo,
When listado,
Then `contato_nome`/`contato_telefone` vêm do contato e `modelo_nome` do modelo;
envio avulso (`modelo_id` nulo) → `modelo_nome` nulo.

**AC-5 — Exige autenticação.**
Given sem sessão,
When `GET /envios`,
Then 401.

**AC-6 — Erro só quando falhou.**
Given um envio `falhou` com `erro_codigo`/`erro_motivo`,
When listado,
Then os campos de erro vêm preenchidos; envios não-falhos trazem erro nulo.

**AC-7 — Paginação.**
Given mais envios que o limite,
When `GET /envios?limit=50&offset=50`,
Then retorna a página pedida; `limit` tem cap 200 (`>200`/`<1` → 422), `offset>=0`.

**AC-8 — Tela Histórico (frontend).**
Given o operador autenticado na rota `historico`,
When a tela carrega,
Then lista os envios (5 campos; erro só em `falhou`), permite filtrar por **status** e **período**,
mostra estado-vazio quando não há envios, e redireciona a `login` em 401.

## Casos de borda
- Sem envios → 200 lista vazia / estado-vazio na tela.
- `status` inválido no GET → 422; `desde > ate` → lista vazia (sem erro).
- Envio avulso (`agendamento_id`/`modelo_id` nulos) **aparece**; `modelo_nome` nulo tratado na tela.
- Telefone/`erro_motivo` são PII: **não** vão a logs (§6); na resposta autenticada da API, ok.

## Fora de escopo
- Ações sobre o envio (reenviar/cancelar vivem em `/agendamentos`).
- `pricing`/`conversation`; exportação; atualização em tempo real/polling.

## Definition of Ready
- [x] AC testáveis (pytest para o endpoint; vitest para a tela). Non-goals explícitos. Sem migração.
