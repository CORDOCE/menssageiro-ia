---
name: spec-worker-agendamentos
description: Spec da Fase 4 — núcleo do disparo (0004-worker-agendamentos). Os critérios de aceite são o contrato e o oráculo de teste. Agendamento + configuração + worker de disparo idempotente.
---

# Spec: Worker de disparo + agendamentos — núcleo (Fase 4)

## Contexto
Caminho de produção de envio (BRIEFING §9/§10.3, ADR 0005): o operador agenda uma mensagem (contato **ou**
grupo, modelo aprovado, data/hora) e o **worker dispara no minuto certo, sem duplicar** — inclusive após
reiniciar — com as checagens por contato. Detalhes e trade-offs em `product.md`/`design.md`. **Pronto quando**:
um agendamento vencido para um grupo vira N `envios` (um por contato elegível), com `wamid` gravado, idempotente
a reinício, e as checagens de janela/limite/pausa/consentimento/descadastro valendo — e os AC abaixo passam.

**Dependências:** para **validação real** em staging, Fase 0 (credenciais Meta — hoje bloqueada, erro 131031).
**Não bloqueia os AC**, que passam com **mock** de `enviar_template` e **PostgreSQL real em container** (§5.7).

## Decisões do gate (/clarificar 2026-11-04)
Fonte única em `configuracoes` (env só semeia); `limite_por_contato_dia` default `NULL` (sem limite);
`aguardando_decisao` **detectado e resolvível** por API (`reenviar`/`cancelar`); reagenda→próximo início de
janela, adia→início da janela do dia seguinte; colunas inertes de recorrência já na migração. → **ADR 0008**.

## Critérios de aceite (o contrato)

**Schema / migração (Alembic, com `downgrade` — §4.5 / /migracao)**
- **AC-1** — Dado banco limpo, Quando `alembic upgrade head`, Então cria `agendamentos` (com `CHECK` de
  `contato_id` **xor** `grupo`, FK `modelo_id→modelos`, FK `criado_por→usuarios`, colunas inertes
  `agendamento_pai_id`/`recorrencia`) e `configuracoes` (linha única semeada com defaults); `downgrade base`
  reverte tudo sem erro.
- **AC-2** — Dado o schema aplicado, Então `envios.agendamento_id` tem **FK → `agendamentos.id`** (nullable,
  avulsos/teste com `NULL`) e o índice único parcial `(agendamento_id, contato_id) WHERE agendamento_id IS NOT NULL` persiste.

**API agendamentos (`/agendamentos`, `Depends(usuario_atual)`; §5.1 — só registra, nunca envia)**
- **AC-3** — Dado operador autenticado, Quando `POST /agendamentos` com `contato_id`, `modelo_id`, `executar_em`,
  Então **201**, agendamento `status='aprovado'`, `criado_por` = usuário atual; **nenhuma** chamada à Meta.
- **AC-4** — Dado `POST /agendamentos` com **ambos** `contato_id` e `grupo` (ou **nenhum**), Então **422**
  (viola o xor) — nada é criado.
- **AC-5** — Dado `modelo_id` inexistente, Quando `POST /agendamentos`, Então **404/422**; sem sessão → **401**.
- **AC-6** — Dado um agendamento não-terminal, Quando `POST /agendamentos/{id}/cancelar`, Então `status='cancelado'`;
  se já terminal (`enviado`/`cancelado`) → **409** (sem efeito).
- **AC-7** — Dado um agendamento em `aguardando_decisao`, Quando `POST /agendamentos/{id}/reenviar`, Então
  `status='aprovado'` e `executar_em=agora`; a partir de **qualquer outro** status → **409**.

**Worker de disparo (`worker/`; mock de `enviar_template`, PostgreSQL real)**
- **AC-8** — Dado 1 agendamento `aprovado` **vencido** para 1 contato elegível, Quando o worker roda 1 ciclo,
  Então cria **1 `envio`**, chama `enviar_template` 1×, grava o `wamid`, `envio.status='enviado'` e
  `agendamento.status='enviado'`.
- **AC-9** — Dado 1 agendamento de **grupo** com N contatos elegíveis, Quando o worker roda, Então cria **N
  `envios`** (um por contato), um `wamid` por envio.
- **AC-10 (idempotência — §5.2)** — Dado um agendamento de grupo cujo lote foi **interrompido** (parte dos
  contatos já tem `envio`), Quando o worker roda de novo, Então **não reenvia** aos contatos já com `envio`
  (nenhum contato recebe 2×); `enviar_template` é chamado só para os restantes.
- **AC-11 (pausa — §5.6)** — Dado `configuracoes.envios_pausados=true`, Quando o worker roda, Então **não
  dispara nada** (zero chamadas à Meta) e **grava heartbeat**.
- **AC-12 (janela)** — Dado um agendamento vencido **fora** da janela de horário, Quando o worker roda, Então
  **reagenda** (`executar_em` = próximo início de janela, `reagendamentos += 1`, `motivo_ultima_transicao`
  preenchido), **mantém `aprovado`** e **não envia**.
- **AC-13 (limite diário)** — Dado que os `envios` nas últimas 24 h já atingiram `limite_diario`, Quando o
  worker roda um agendamento vencido, Então **adia** (`executar_em` = início da janela do **dia seguinte**),
  **mantém `aprovado`**, **não envia**.
- **AC-14 (modelo)** — Dado um agendamento cujo `modelo.status != 'aprovado'`, Quando o worker roda, Então
  `agendamento.status='falhou'` com motivo (e alerta registrado); **não envia**.
- **AC-15 (descadastro — §5.4)** — Dado um contato com `descadastrado_em` não-nulo no grupo, Quando o worker
  expande, Então esse contato **não recebe** (sem `envio` para ele) e o pulo é auditado.
- **AC-16 (consentimento — §5.9)** — Dado um contato com `consentimento=false` no grupo, Quando o worker
  expande, Então esse contato **não recebe** e o pulo é auditado.
- **AC-17 (limite por contato)** — Dado `limite_por_contato_dia=NULL`, Então o contato **não** é bloqueado por
  essa regra; dado `limite_por_contato_dia=k` **configurado** e já atingido no dia, Então o contato é **pulado**.
- **AC-18 (`aguardando_decisao` — ADR 0005)** — Dado um agendamento `aprovado` **>2 h atrasado** **e** um
  **gap de heartbeat** (último `ultimo_ciclo_em` mais velho que `2×intervalo`), Quando o worker roda, Então o
  agendamento vai para **`aguardando_decisao`** e **não dispara**.
- **AC-19 (contraexemplo)** — Dado um agendamento **>2 h atrasado** **sem** gap de heartbeat, Quando o worker
  roda, Então ele **dispara normalmente** (não vai para `aguardando_decisao`).
- **AC-20 (erro definitivo da Meta)** — Dado que `enviar_template` levanta erro definitivo para um contato,
  Então o `envio` dele vira `falhou` com `erro_codigo`/`erro_motivo`; os demais contatos do grupo seguem.
- **AC-21 (auditoria sem PII — §5.8/§7)** — Cada envio gera auditoria com **telefone mascarado** e
  `correlation_id = agendamento_id`; nenhum log com telefone/texto em claro.
- **AC-22 (concorrência — §5.2)** — Dado dois ciclos concorrentes, Quando selecionam agendamentos vencidos,
  Então `FOR UPDATE SKIP LOCKED` garante que o **mesmo agendamento não é processado por ambos** (sem duplicar envios).

## Matriz de decisão — nível agendamento (precedência de cima para baixo; cada linha = 1 teste)
| envios_pausados | dentro da janela | modelo aprovado | limite_diario ok | ação do worker |
|---|---|---|---|---|
| **true** | — | — | — | não envia nada (só heartbeat) — AC-11 |
| false | **não** | — | — | reagenda, mantém `aprovado` — AC-12 |
| false | sim | **não** | — | `falhou` + alerta — AC-14 |
| false | sim | sim | **não** | adia, mantém `aprovado` — AC-13 |
| false | sim | sim | sim | **expande e envia** (aplica checagens por contato) — AC-8/9 |

## Matriz de decisão — por contato (dentro de um agendamento que vai enviar; cada linha = 1 teste)
| descadastrado_em | consentimento | limite_por_contato_dia | recebe? |
|---|---|---|---|
| não-nulo | — | — | **não** (§5.4) — AC-15 |
| nulo | **false** | — | **não** (§5.9) — AC-16 |
| nulo | true | `NULL` (sem limite) | **sim** — AC-17 |
| nulo | true | configurado, **não** atingido | **sim** — AC-17 |
| nulo | true | configurado e **atingido** | **não** (pula) — AC-17 |

## Casos de borda
- **Grupo sem contato elegível** (todos descadastrados/sem consentimento): nenhum `envio`; agendamento vai para
  `enviado` (nada a enviar) com auditoria de "0 enviados" — não fica preso em `enviando`.
- **Borda da janela:** `20:00` exato (fim) e virada de semana (domingo fora de seg–sáb) — testar os limites.
- **Reinício entre reservar e enviar:** `envio` em `enviando` sem `wamid` **não** é reenviado (at-most-once, §5.2);
  fica visível para o operador.
- **Envio avulso/teste da Fase 3** (`agendamento_id IS NULL`): o worker **não** o toca.
- **Cancelar/`reenviar` em status inválido:** `409` (AC-6/AC-7).
- **`executar_em` no futuro:** não é seleccionado (worker só pega vencidos).

## Fora de escopo (vinculante)
- **Recorrência (RRULE)** → spec 0005 (colunas já criadas, mas sem lógica; sem `python-dateutil`).
- **Anexos / cabeçalho DOCUMENT** → spec seguinte (0004 envia template **só-texto**).
- **Texto livre / janela de 24 h** (respostas da IA) → Fase 8.
- **Telas do PWA** (agenda/calendário), **sugestões da IA**, **comandos do admin pelo WhatsApp** → Fases 5/6/7.
- **Envio para número real** sem aprovação explícita (§4) — validação real só no número de teste.

## Gate de cobertura (§8)
Regras de envio (worker) e checagens: **≥90% de linhas** + os testes de borda acima explícitos. Nenhum teste
chama a API real da Meta (mock); integração com PostgreSQL real em container.
