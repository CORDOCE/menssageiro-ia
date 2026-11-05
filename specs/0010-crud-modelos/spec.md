# Spec — 0010 Listagem + sincronização de Modelos — dívida F1

Tier Pequeno. Destrava a UI "Nova mensagem": **`GET /modelos`** (listar/escolher template) e
**`POST /modelos/sincronizar`** (povoar o banco lendo os templates da Meta — Cloud API, só leitura;
a Meta é a **fonte da verdade** do status/categoria, §5.3). Ambos protegidos por sessão.
Escopo escolhido por Jefferson (2026-11-05): GET + sincronizar (criação de template na Meta = spec futura).

## Critérios de aceite (Given/When/Then)

**AC-1 — Lista modelos (autenticado).**
Given o operador autenticado e modelos no banco,
When `GET /modelos`,
Then retorna 200 com a lista (id, nome, idioma, categoria, status, corpo, cabecalho_tipo, variaveis), ordenada por `nome`.

**AC-2 — Filtro por status.**
Given modelos com status variados,
When `GET /modelos?status=aprovado`,
Then retorna **apenas** os de status `aprovado`.

**AC-3 — Exige autenticação.**
Given sem sessão (nem cookie nem Bearer),
When `GET /modelos` ou `POST /modelos/sincronizar`,
Then 401.

**AC-4 — Sincronizar faz upsert dos templates da Meta.**
Given a Meta retorna N templates (Cloud API, mockada nos testes),
When `POST /modelos/sincronizar`,
Then cada template vira/atualiza um `Modelo` por `(nome, idioma)`; o status é mapeado da Meta
(`APPROVED→aprovado`, `REJECTED→rejeitado`, `PENDING→pendente`, `PAUSED/DISABLED/...→pausado`);
retorna `{total, criados, atualizados}`.

**AC-5 — Sincronizar é idempotente/atualiza.**
Given um template já sincronizado,
When a Meta muda seu status e `sincronizar` roda de novo,
Then o `Modelo` existente é **atualizado** (não duplicado) e reflete o novo status.

## Casos de borda
- Sem modelos → 200 com lista vazia; sem templates na Meta → `{total:0}`.
- `status` inválido no GET → 422.
- Template sem BODY → `corpo` vazio; variáveis `{{n}}` extraídas do corpo.
- Testes **nunca** chamam a Meta real (mock; §5.7).

## Fora de escopo
- **Criar/submeter** template na Meta (aprovação assíncrona) — spec futura (ADR).
- Editar/apagar modelo; paginação do GET (lista pequena nesta fase).

## Definition of Ready
- [x] AC testáveis (pytest + mock quando houver Meta — aqui GET é só banco, sem Meta). Non-goals explícitos.
