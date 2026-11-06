---
name: spec-agenda
description: Spec da feature 0012-agenda. A fonte da verdade — os critérios de aceite são o contrato e o oráculo de teste.
---

# Spec: Agenda (gerenciar agendamentos pela UI)

## Contexto
A 0011 entregou **criar** agendamento (tela Nova mensagem). A tela **Hoje** só mostra um recorte
(próximos envios `aprovado`, limite 8). Falta a tela de **gestão completa** dos agendamentos — o
"acompanha" da Fase 5 (BRIEFING §14; `docs/divida-tecnica.md` F2). Esta feature entrega a **Agenda**:
listar todos os agendamentos com filtro, ver status/destino/horário, e agir sobre eles (cancelar,
reenviar quando aplicável, cancelar série recorrente). **Backend já pronto** — usa só endpoints
existentes (spec 0004/0005): `GET /agendamentos`, `POST /agendamentos/{id}/cancelar`,
`.../reenviar`, `.../cancelar-serie`. Tier **Pequeno** (frontend sobre endpoints existentes).

> **Suposições de escopo do v1 (aprovar no gate — reversíveis):**
> - **S1** Sem **edição** de agendamento (não há endpoint PATCH) — só cancelar/reenviar/cancelar-série.
> - **S2** Sem **criação** aqui (é a Nova mensagem, 0011).
> - **S3** Reuso do vocabulário de status via `seloAgendamento` (`components/Selo.tsx`) e da formatação
>   de data/hora America/Sao_Paulo da tela Hoje.

## Contrato do backend (verificado em `backend/app/api/agendamentos.py`)
- `GET /agendamentos?status=&limit=&offset=` → lista `AgendamentoRead`, **ordenada por `executar_em`**.
  Filtra **só por `status`** no servidor (sem filtro de período/data). `limit` 1–200 (default 50).
- Status possíveis (via `seloAgendamento`): `aprovado` (Agendada), `enviando`/`enviado` (Enviada),
  `entregue`, `lido`, `aguardando_decisao` (Aguardando), `falhou` (Não enviada), `cancelado`.
  **Terminais:** `enviado`, `cancelado`.
- `POST /{id}/cancelar` → 200 (`cancelado`); **409** se já terminal.
- `POST /{id}/reenviar` → 200; **só** quando status == `aguardando_decisao` (senão 409). Zera `executar_em` p/ agora.
- `POST /{id}/cancelar-serie` → `{ "cancelados": N }`; aceita id da raiz ou de filha; cancela as
  ocorrências **futuras** `aprovado` da série.
- `AgendamentoRead`: `id, contato_id, grupo, modelo_id, variaveis, executar_em, status, origem,
  recorrencia, agendamento_pai_id, reagendamentos, motivo_ultima_transicao, criado_em`.

## Critérios de aceite (o contrato)
Um teste por AC (Vitest + Testing Library, cliente de API mockado — nunca Meta/OpenAI real, §5.7).

- **AC-1** — Dado agendamentos no backend, Quando a Agenda carrega, Então lista os itens de
  `GET /agendamentos` **ordenados por `executar_em`**, cada linha com: destino (nome do contato
  resolvido via `GET /contatos`, ou `Grupo: X`), **selo de status** (`seloAgendamento`), data e hora
  em America/Sao_Paulo, e indicador de **recorrência** quando `recorrencia != null`.
- **AC-2** — Dado itens de vários status, Quando o operador seleciona um **filtro de status**, Então a
  lista recarrega chamando `GET /agendamentos?status=<status>`; "Todos" não envia `status`.
- **AC-3** — Dado um agendamento em status **não terminal** (ex.: `aprovado`), Quando o operador aciona
  **Cancelar** e confirma, Então chama `POST /agendamentos/{id}/cancelar`; ao receber 200 a lista
  reflete o novo status (`Cancelada`). Para agendamento **terminal** (`enviado`/`cancelado`) a ação
  **Cancelar não é oferecida**.
- **AC-4** — Dado um agendamento em `aguardando_decisao`, Quando o operador aciona **Reenviar**, Então
  chama `POST /agendamentos/{id}/reenviar`; a ação **só** aparece para esse status.
- **AC-5** — Dado um agendamento **recorrente** (`recorrencia != null` ou `agendamento_pai_id != null`),
  Quando o operador aciona **Cancelar série** e confirma, Então chama `POST /agendamentos/{id}/cancelar-serie`
  e exibe quantas ocorrências foram canceladas (`{cancelados}`); a ação **não** aparece em agendamento avulso.
- **AC-6** — Dado erro do backend (ex.: 409 estado terminal, 401 sessão expirada), Quando uma ação
  falha, Então exibe mensagem legível (sem stack/PII) e **não** quebra a lista; em 401 redireciona ao login.
- **AC-7** — Dado nenhum agendamento (ou nenhum no filtro), Quando a lista carrega vazia, Então mostra
  **estado vazio** orientando (link para Nova mensagem); durante o carregamento, esqueleto.

## Casos de borda
- Agendamento com `grupo` em vez de `contato_id` → destino "Grupo: X" (como a Hoje faz).
- Contato do agendamento não encontrado no mapa → rótulo neutro "Contato" (sem quebrar).
- Ação em andamento → botões desabilitados até concluir (evita duplo clique / dupla transição).
- Reenviar/cancelar que volta 409 (corrida: status mudou) → mensagem e recarrega a lista.
- Lista grande (> limit) → ver Questão em aberto sobre paginação.

## Fora de escopo (vinculante)
- **Editar** agendamento (sem endpoint PATCH) — spec futura se necessário.
- **Criar** agendamento (é a Nova mensagem, 0011).
- Histórico de envios/status detalhado por mensagem (tela Histórico, precisa de `GET /envios` — não existe).
- Ações em lote (cancelar vários de uma vez).

## Questões em aberto (resolver no gate / `/clarificar`)
1. **Filtros do v1:** além do filtro por **status**, incluir filtro de **período** (futuros / passados /
   todos — feito no cliente, já que o GET não filtra por data)? Quais status no seletor?
2. **Paginação:** base pequena hoje — carregar `limit=200` e pronto, ou botão "carregar mais"/paginação?
3. **Confirmação destrutiva:** cancelar / cancelar-série via `window.confirm` (padrão atual da tela
   Contatos) ou diálogo próprio?
4. **Reenviar no v1:** expor a ação (só aparece em `aguardando_decisao`, que surge do limite diário) ou
   deixar para depois? (Não custa, mas confirma o escopo.)
