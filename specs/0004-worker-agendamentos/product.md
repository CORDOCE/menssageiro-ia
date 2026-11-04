---
name: product-worker-agendamentos
description: Product brief da Fase 4 — núcleo do disparo (0004-worker-agendamentos). O worker expande agendamentos vencidos em envios, dispara o template no minuto certo, sem duplicar mesmo após reinício, com as checagens por contato. Problema, métrica e fronteiras.
---

# Product: Worker de disparo + agendamentos — núcleo (Fase 4)

## Problema
A Fase 3 provou que o sistema **consegue** enviar um template (via endpoint de teste protegido), mas não há
**caminho de produção**: ninguém agenda uma mensagem e o worker hoje só grava heartbeat, **sem enviar nada**.
Falta o coração do produto (BRIEFING §1): o operador agenda uma mensagem (para um **contato ou um grupo**, com
um **modelo aprovado**, data/hora) e o **worker dispara no minuto certo**, **sem duplicar** — mesmo que caia e
reinicie no meio de um lote — respeitando as checagens por contato (descadastro, consentimento, modelo aprovado,
janela de horário, limite diário, pausa geral). É o marco da Fase 4: *"envios no minuto certo, sem duplicidade,
inclusive após reiniciar"* (BRIEFING, tabela de fases).

Para quem: o operador (agenda e confia que sai certo) e, indiretamente, os contatos que recebem as mensagens
oficiais — e **só** os elegíveis.

## Métrica de sucesso
Observável em **staging com o número de teste** (nunca número real sem aprovação, §4) e por testes de integração
com PostgreSQL real:
1. Operador cria um agendamento **vencido** para um **grupo de N contatos elegíveis**; no ciclo seguinte o worker
   materializa **N `envios`** (um por contato), envia o template e grava o `wamid` em cada um.
2. **Idempotência:** reiniciar o worker no meio do lote **não gera envio duplicado** ao mesmo contato
   (`UNIQUE(agendamento_id, contato_id)` — ADR 0005); nenhum contato recebe duas vezes.
3. **Checagens por contato:** contato **descadastrado** (§5.4) ou **sem consentimento** (§5.9) no grupo **não**
   recebe; modelo **não aprovado** → agendamento falha + alerta.
4. **Janela/limite/pausa:** fora da janela de horário → **reagenda** (mantém `aprovado`, atualiza `executar_em`);
   acima do `limite_diario` → **adia** (mantém `aprovado`); `envios_pausados` ligado → **não envia** nada.
5. **Resiliência:** quando há **indisponibilidade** (gap no heartbeat `ultimo_ciclo_em`) **e** o item está **>2h
   atrasado**, o worker move o agendamento para **`aguardando_decisao`** (ADR 0005) em vez de disparar cego.

## Goals
- **Modelo `Agendamento`** + migração Alembic com o schema do **ADR 0005 / BRIEFING §9**: `contato_id` **ou**
  `grupo`, `modelo_id`, `variaveis` (JSON), `executar_em` (timestamptz), `status`, `origem`, `criado_por`,
  `motivo_ultima_transicao`, `reagendamentos`, `agendamento_pai_id` (coluna já criada p/ a recorrência futura,
  sem lógica agora). Promover o índice parcial de `envios` para **FK real** `envios.agendamento_id → agendamentos`.
- **Configuração mínima de envio** (janela de horário, `limite_diario`, `limite_por_contato_dia`,
  `envios_pausados`) — fonte única que o worker lê a cada ciclo (§5.6). Formato/local decididos no `design.md`.
- **API mínima de agendamentos** (`api/agendamentos.py`, autenticada): **criar** (contato ou grupo; one-off),
  **listar** e **cancelar**. É o que dá ao worker o que disparar e torna o fluxo testável ponta a ponta.
  *(Invariante §5.1: a API só registra o agendamento; quem envia é o worker.)*
- **Worker de disparo** (`worker/`, estende o loop de heartbeat): `SELECT … FOR UPDATE SKIP LOCKED` nos
  agendamentos `aprovado` **vencidos** → `enviando`; expande grupo em `envios` idempotentes; checagens por
  contato; chama `whatsapp_client.enviar_template` (já existe, Fase 3); grava `envios`/`wamid`, auditoria sem PII
  (§5.8) e heartbeat. Detecção de `aguardando_decisao` por gap de heartbeat + atraso >2h.
- Observabilidade: `correlation_id` por agendamento/envio (§7); logs estruturados sem PII; alerta de falha.

## Non-goals (vinculante)
- **Recorrência (RRULE):** criação da próxima ocorrência fica para a **spec 0005**. A coluna `agendamento_pai_id`
  e o `UNIQUE(agendamento_pai_id, executar_em)` podem entrar no schema, mas **sem** lógica de expansão aqui.
  *(Evita a dependência nova `python-dateutil`/RRULE — §4.)*
- **Anexos (PDF no cabeçalho DOCUMENT):** `upload_midia`/`componente_documento` já existem (Fase 3), mas o fluxo
  de agendamento com anexo fica para a **spec seguinte**. 0004 envia template **só-texto** (corpo + variáveis).
- **Texto livre / janela de 24 h:** agendamento é **sempre template aprovado** (§5.3); envio de `type: text`
  dentro da janela de atendimento é das respostas da IA → **Fase 8**.
- **Resolução do `aguardando_decisao` pelo operador** (reenviar/cancelar via tela) e **telas do PWA** (agenda,
  calendário) → fora; o worker apenas **move** para o estado. Cancelar via API entra (transição simples).
- **Sugestões da IA que viram agendamento** → Fase 6. **Comandos do admin pelo WhatsApp** → Fase 7.
- **Envio para qualquer número real** → proibido sem aprovação explícita (§4); validação real só no número de teste.

## Dependências (pré-condições)
- Para a **validação real** em staging: Fase 0 (credenciais Meta) — ainda pendente (conta de teste bloqueada,
  erro 131031). **Não bloqueia o desenvolvimento**: testes usam **mocks** do `whatsapp_client` e PostgreSQL em
  container (§5.7). O caminho real roda quando houver conta liberada.
- Modelos `Modelo`, `Contato`, `Envio`, `Saude` e `whatsapp_client.enviar_template` já existem (Fases 2–3).

## Questões em aberto (resolver no gate da spec, via /clarificar)
1. **`limite_diario` — onde mora?** BRIEFING §4.5 fala em env `LIMITE_DIARIO` (padrão 200); BRIEFING §9 coloca
   `limite_diario` na tabela `configuracoes`. **Conflito a resolver** (fonte única; §5.6 exige checar a cada ciclo).
2. **`configuracoes`:** tabela nova (modelo) com linha única vs. subconjunto mínimo. Decidir no `design.md`.
3. **Janela de horário:** default seg–sáb 8h–20h (BRIEFING §10.3); formato de armazenamento e fuso
   (America/Sao_Paulo para comparação, timestamptz no banco — §8).
4. **Expansão de grupo:** `grupo` é um rótulo em `contatos.grupo`; confirmar "grupo dinâmico" = todos os contatos
   com aquele rótulo **no momento do disparo** (ADR 0005). Agendamento tem `contato_id` **xor** `grupo`.
5. **`aguardando_decisao`:** 0004 detecta e move; a resolução (reenviar→`aprovado`) fica para spec/tela depois?
