# Spec — 0010 Listagem de Modelos (`GET /modelos`) — parte da dívida F1

Tier Pequeno. Primeiro passo da F1: expõe a **leitura** de modelos (templates) para destravar a UI
"Nova mensagem" (escolher um template aprovado). Protegido por sessão.

> **Decisão de escopo PENDENTE (Jefferson):** o **povoamento** dos modelos — `POST /modelos/sincronizar`
> (ler templates da Meta via Graph API e fazer upsert) **vs** criação/submissão de template na Meta — fica
> **fora desta spec**, aguardando escolha (toca a Cloud API → `/meta-whatsapp`, §4/§5.3). Sem povoamento,
> o GET reflete o que já existir no banco.

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
When `GET /modelos`,
Then 401.

## Casos de borda
- Sem modelos → 200 com lista vazia.
- `status` inválido (fora do conjunto conhecido) → 422 (validação).

## Fora de escopo
- **Povoamento** (sincronizar da Meta / criar template) — decisão pendente, spec/parte seguinte.
- Editar/apagar modelo; paginação (lista pequena nesta fase).

## Definition of Ready
- [x] AC testáveis (pytest + mock quando houver Meta — aqui GET é só banco, sem Meta). Non-goals explícitos.
