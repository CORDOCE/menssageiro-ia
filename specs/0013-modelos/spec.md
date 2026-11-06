---
name: spec-modelos
description: Spec da feature 0013-modelos. A fonte da verdade — os critérios de aceite são o contrato e o oráculo de teste.
---

# Spec: Modelos (ver templates e sincronizar com a Meta)

## Contexto
Próxima tela da **Fase 5** (BRIEFING §14; `docs/divida-tecnica.md` F2), após Agenda (0012). O operador
precisa **ver os templates (modelos) disponíveis** e seus status, e **disparar a sincronização** com a Meta
(a Meta é a fonte da verdade do status/categoria — §5.3). Backend já pronto (spec 0010): `GET /modelos`
e `POST /modelos/sincronizar`. **Criar/submeter template à Meta fica fora** (spec futura). Tier **Pequeno**
(frontend sobre endpoints existentes).

## Contrato do backend (verificado em `backend/app/api/modelos.py`)
- `GET /modelos?status=` → `list[ModeloRead]`, **ordenado por `nome`**; filtra por `status` no servidor.
  `ModeloRead = {id, nome, idioma, categoria, status, corpo, cabecalho_tipo, variaveis}`.
- **Status** (mapeado da Meta): `aprovado`, `pendente`, `rejeitado`, `pausado`, `rascunho`.
- `POST /modelos/sincronizar` → `{total, criados, atualizados}`. Lê templates da Meta (Cloud API, só
  leitura) e faz upsert por `(nome, idioma)`. **Exige credenciais Meta** (`WHATSAPP_TOKEN`+`WABA_ID`):
  staging tem; **produção não** → lá a sincronização falha até a Fase 0.
- Ambos protegidos por sessão (spec 0010).

## Suposições de escopo do v1 (aprovar no gate — reversíveis)
- **S1** Tela **só leitura + sincronizar**: não cria, não edita, não submete template à Meta.
- **S2** Prévia do `corpo` como **texto puro** (§6 — sem HTML/markdown interpretado).
- **S3** Reuso do selo (novo mapa status-de-modelo→tom) e dos padrões de lista/estado-vazio da 0006/0012.

## Critérios de aceite (o contrato)
Um teste por AC (Vitest + Testing Library, cliente de API mockado — nunca Meta real, §5.7).

- **AC-1** — Dado modelos no backend, Quando a tela Modelos carrega, Então lista os itens de `GET /modelos`
  (ordem do backend), cada um com: **nome**, **selo de status**, **categoria**, **idioma**, **prévia do corpo**
  (texto puro) e as **variáveis** (`{{n}}`) do template.
- **AC-2** — Dado modelos de vários status, Quando o operador seleciona um **filtro de status**, Então a lista
  recarrega chamando `GET /modelos?status=<status>`; "Todos" não envia `status`.
- **AC-3** — Dado que o operador aciona **Sincronizar**, Quando a chamada `POST /modelos/sincronizar` retorna
  200, Então exibe o resultado (**total / criados / atualizados**) e **recarrega** a lista.
- **AC-4** — Dado que a sincronização falha (ex.: 500 por falta de credenciais Meta em produção, ou 401),
  Quando o operador aciona Sincronizar, Então exibe mensagem legível (sem stack/PII) e **não** quebra a tela;
  em 401 redireciona ao login.
- **AC-5** — Dado nenhum modelo, Quando a lista carrega vazia, Então mostra **estado vazio** orientando a
  **Sincronizar**; durante o carregamento, esqueleto.

## Casos de borda
- Modelo com `variaveis = []` → mostra "sem variáveis" (não quebra).
- Modelo com `cabecalho_tipo` (DOCUMENT/IMAGE) → exibir o tipo de cabeçalho (informativo); envio de mídia fica fora.
- `corpo` longo → prévia com limite/estética, sem HTML interpretado.
- Sincronizar em andamento → botão desabilitado (evita duplo disparo).

## Fora de escopo (vinculante)
- **Criar / editar / submeter** template à Meta — spec futura.
- **Enviar teste** (`POST /modelos/{id}/enviar-teste`, restrito ao número de teste) — ação de QA, fora da UI do operador (ver Questão 2).
- Excluir modelo.

## Questões em aberto (resolver no gate / `/clarificar`)
1. **Filtro de status** na lista: incluir no v1 (como na Agenda) ou só listar tudo?
2. **Enviar teste:** expor o botão (só funciona p/ o número de teste em staging) ou deixar fora do v1?
3. **Confirmação antes de sincronizar:** a sincronização é idempotente (só leitura + upsert) — botão direto
   com feedback, ou pedir confirmação?
4. **Detalhe do modelo:** mostrar corpo/variáveis **inline** na lista, ou um painel/diálogo de detalhe ao clicar?
