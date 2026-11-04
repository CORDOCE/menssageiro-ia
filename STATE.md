# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-04_

## Em andamento
- **Fase 4 — núcleo do disparo** (spec `specs/0004-worker-agendamentos/`), na branch **`feat/0004-worker-agendamentos`**.
  Esteira SDD completa (product/design/spec/tasks) + **tasks 1–6 implementadas, testadas e commitadas** (119 passed, ruff+mypy limpos). **Faltam tasks 7–11.**

## Próximo passo (retomar aqui)
1. **Task 7** — `services/janela.py`: `dentro_da_janela`/`proximo_inicio`/`inicio_dia_seguinte` (fuso America/Sao_Paulo via `zoneinfo`; sem dep nova) + helper singleton de `configuracoes` (create-if-missing usando `settings.limite_diario_default`). Testes de borda: 20:00 exato, domingo fora, próximo início, dia seguinte.
2. **Tasks 8–10** — worker `worker/disparo.py` (TDD, PostgreSQL real): decisão por agendamento (SKIP LOCKED → pausa/janela/modelo/limite) → expansão de grupo + checagens por contato + **reserva `ON CONFLICT DO NOTHING`** → `enviar_template` (mock) → `wamid`/auditoria; detecção de `aguardando_decisao`. ⚠️ **Trocar o teste `tests/test_worker.py::test_worker_fase1_nao_envia_nada`** (ele asserta que o worker NÃO menciona "whatsapp" — a Fase 4 faz o worker enviar; requisito mudou pela spec 0004, §1.7).
3. **Task 11** — cobertura ≥90% das regras de envio; `pytest --cov`.
4. Antes do PR: **/revisar → /seguranca → /validar** + suíte CI completa via Docker (§4.4). PR para `develop`.

## Decisões/trabalho desta sessão (2026-11-04)
- **Spec 0004 + ADR 0008** (config runtime em `configuracoes`; idempotência **at-most-once por (agendamento, contato)** com reserva-antes-de-enviar; janela JSONB em America/Sao_Paulo). `/clarificar` fechou: `limite_diario` na tabela (env só semeia), `limite_por_contato_dia` default NULL (sem limite), `aguardando_decisao` detectado **e** resolvível por API (`reenviar`/`cancelar`), reagenda→próximo início/adia→dia seguinte, colunas inertes de recorrência já na migração.
- **Implementado (tasks 1–6):** ADR 0008; modelos `Agendamento` (CHECK contato xor grupo) + `Configuracao`; FK `envios.agendamento_id→agendamentos` + migração `5d75fec0aa05` (downgrade ok, seed da config); `config.limite_diario_default`; API `/agendamentos` (criar/listar/cancelar/reenviar). Recorrência e anexos ficaram **fora** (specs seguintes).
- **PR #21 aberto** (branch `docs/fase0-webhook-callback-e-test-number` → `develop`): corrige a callback do webhook para **`/webhook/meta`** (RAILWAY.md estava com `/api/...` → daria 404) e documenta `WHATSAPP_TEST_NUMBER` + `GRAPH_API_VERSION=v26.0`. `/revisar` limpo; PR só de doc.

## Bloqueios / pendências
- **Fase 0 (WhatsApp real) BLOQUEADA — erro `131031` "Business Account locked".** O portfólio Meta novo do responsável foi travado (conta nova sem site). **Desbloqueio depende de análise da Meta:** em `business.facebook.com` → Informações da empresa (com **site**, pode ser GitHub/LinkedIn) → **Qualidade da conta → Solicitar análise**. Enquanto isso, **desenvolvimento não bloqueia** (testes com mock). Estratégia acordada: tocar a Fase 4 com mocks; validação real quando a conta liberar (ou na conta do **cliente**, caminho de produção).
  - **Valores já coletados** (app de teste do responsável): `PHONE_NUMBER_ID=1457634440766192`, `WABA_ID=1679341853598307`, número de teste `+1 555-148-9020`. (App id `2093735544592019`.)
  - Projeto é **para terceiro**: número real pertence ao cliente → produção exige o cliente dar acesso admin ao Business Manager dele (ou Embedded Signup). Decisão/§4 para depois.
- **Gap p/ validação real:** **não há CRUD de `Modelo`** — a tela/endpoint só existe para `enviar-teste`. Para o worker ter o que enviar, hoje precisa **insert manual** de `Modelo` (nome idêntico ao template aprovado; webhook casa por `Modelo.nome`). Considerar um endpoint de modelos numa spec futura.
- **Validar Fase 2 em staging** (DoD 0002): import com `validar_fase2.csv` (scratchpad), esperado total=3/criados=2/erros=1.
- Pendência de segurança herdada: **cifrar `totp_secret` em repouso**.

## Estado do git
- Branch atual: **`feat/0004-worker-agendamentos`** (a partir de `develop`), com commits: `d12d8c6` (spec SDD), `1c7def2` (ADR 0008), `35dc4d6` (tasks 2–4), `e52d352` (tasks 5–6). **Árvore limpa, nada por commitar.** Ainda **sem PR** (abrir só após tasks 7–11 + gates).
- **PR #21 aberto** (doc, Fase 0) da branch `docs/fase0-webhook-callback-e-test-number` → `develop`.
- `develop` segue à frente de `origin/main` (Fase 3 ainda não promovida; promover só após staging/Fase 0).
- Locais não mergeadas: `docs/codebase-map` (`6f03cdc`), `chore/railway-procfile` (`879c09a`), `feat/0003-whatsapp-cloud-api` (mergeada, pode apagar).

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07`)
- **staging** 🟢 segue `develop`; **produção** segue `main`. Dev/testes locais: `docker compose up -d db` (container `mensageiro-ia-db-1`, Postgres 17, porta 5434) — **está de pé** (healthy).
- Webhook staging (quando a Fase 0 liberar): `https://menssageiro-ia-backend-staging.up.railway.app/webhook/meta`.

## Fase 3 — entregue (PR #20; specs/0003-whatsapp-cloud-api)
- `whatsapp_client` (enviar_template c/ retry, upload_midia, componente_documento), webhook `/webhook/meta` (verify, HMAC corpo-cru, statuses→envios por wamid, template_status_update→modelos), `POST /modelos/{id}/enviar-teste` restrito ao nº de teste. 102 passed. Pendente p/ "pronto": validação real (depende da Fase 0).
