# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-04_

## Em andamento
- **Nada em implementação.** **Fase 4 (núcleo do disparo) MERGEADA** em `develop` (PR #22, merge `c46bc89`; CI verde backend+frontend). Staging (segue `develop`) redeploya com o worker; a migração `5d75fec0aa05` (agendamentos/configuracoes + FK) é aplicada pela **api** no start. Próxima implementação: **Fase 4b** (recorrência) ou **anexos**.

## Próximo passo (retomar aqui)
1. ✅ **Deploy da Fase 4 em staging CONFIRMADO** (2026-11-04 17:50, commit `c46bc89`): backend+worker `SUCCESS`; migração `5d75fec0aa05` aplicada (start `alembic upgrade head` ok); smoke `GET /agendamentos` sem auth → 401 (endpoint no ar), `/health` → 200. *(Nota: o erro de build "Railpack/start.sh" que apareceu no painel era um log antigo de 01/11, já resolvido — rootDirectory.)* Falta criar um agendamento autenticado via API como smoke adicional.
2. **Validação REAL do envio** (DoD Fase 3 e 4): **bloqueada pela Fase 0** (Meta 131031 — desbloqueio depende da análise da Meta: Business Info + site + "Solicitar análise"). Gap: sem CRUD de `Modelo` (insert manual até uma spec futura).
3. **Promover `develop`→`main`** só após staging validado de verdade (§4.2) — hoje `develop` à frente de `main` (Fases 3 e 4 não promovidas).
4. **Follow-ups registrados no PR #22** (não bloqueiam): alerta de observabilidade §12; P2 (limite diário por-agendamento, N+1, `contato_id` inexistente→500, cap em `variaveis`).
5. **Próximas specs:** recorrência (RRULE/`python-dateutil`, spec 0005) e anexos (DOCUMENT) — colunas inertes já no schema.
6. ⚠️ **Flakiness local:** `localhost`→IPv6(`::1`) falha; container em `127.0.0.1`. Testes locais com `DATABASE_URL=...@127.0.0.1:5434/mensageiro`. (CI usa Postgres próprio.)

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
- Branch atual: **`develop`** = `c46bc89` (merge do PR #22, Fase 4), sincronizada com `origin`. **Sem PRs abertos.** Branch `feat/0004-worker-agendamentos` **apagada** (local+remota) no merge.
- `develop` está **à frente de `origin/main`** (Fases 3 e 4 não promovidas — promover só após validação real em staging/Fase 0).
- Locais não mergeadas preservadas: `docs/codebase-map` (`6f03cdc`), `chore/railway-procfile` (`879c09a`). `feat/0003` já pode ser apagada se ainda existir.
- **PR #21 aberto** (doc, Fase 0) da branch `docs/fase0-webhook-callback-e-test-number` → `develop`.
- `develop` segue à frente de `origin/main` (Fase 3 ainda não promovida; promover só após staging/Fase 0).
- Locais não mergeadas: `docs/codebase-map` (`6f03cdc`), `chore/railway-procfile` (`879c09a`), `feat/0003-whatsapp-cloud-api` (mergeada, pode apagar).

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07`)
- **staging** 🟢 segue `develop`; **produção** segue `main`. Dev/testes locais: `docker compose up -d db` (container `mensageiro-ia-db-1`, Postgres 17, porta 5434) — **está de pé** (healthy).
- Webhook staging (quando a Fase 0 liberar): `https://menssageiro-ia-backend-staging.up.railway.app/webhook/meta`.

## Fase 3 — entregue (PR #20; specs/0003-whatsapp-cloud-api)
- `whatsapp_client` (enviar_template c/ retry, upload_midia, componente_documento), webhook `/webhook/meta` (verify, HMAC corpo-cru, statuses→envios por wamid, template_status_update→modelos), `POST /modelos/{id}/enviar-teste` restrito ao nº de teste. 102 passed. Pendente p/ "pronto": validação real (depende da Fase 0).
