# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-05_

## Última frente concluída (spec 0006 — PWA telas v1: MERGEADA #25 + EM PRODUÇÃO #26)
- **Spec 0006 — PWA telas v1 EM PRODUÇÃO** (promovida `develop`→`main` via PR **#26**, 2026-11-05, `main = 8b1d43f`). Deploy de produção: **frontend `SUCCESS`** (reconstruiu — `frontend/` mudou; commit `8b1d43f`); **backend/worker `SKIPPED`** (inalterados). Head Alembic de produção `4ff11dacdb87` inalterado. URL: `https://menssageiro-ia-frontend-production.up.railway.app`.
  - ⚠️ **Login em produção exigiu 2 ajustes de config (2026-11-05)** — produção nunca tinha sido logada antes; o deploy da 0006 expôs isso:
    1. **CORS**: backend de produção estava **sem `FRONTEND_URL`** → `_origens=[]` (ver `main.py:23`) → preflight do login bloqueado → "NetworkError". **Corrigido**: setada `FRONTEND_URL=https://menssageiro-ia-frontend-production.up.railway.app` no backend de produção + redeploy. Preflight CORS verificado (200 + `access-control-allow-origin`).
    2. **Admin não semeado**: banco de produção tinha **0 usuários** → 401. Admin criado por **Jefferson** rodando `python -m app.criar_admin` (vars `ADMIN_EMAIL`/`ADMIN_PASSWORD` **inline** via `railway ssh` no container de produção — nada gravado na Railway, sem limpeza). Verificado: `usuarios_no_banco=1`, `tem_totp=True`, `ativo=True`.
  - ⏳ **Pendente**: Jefferson cadastrar o TOTP no autenticador e **validar o login + UI de produção** (staging já validado no #25). Nota: prod backend ainda **sem `ADMIN_EMAIL`/`OPENAI_MODEL`/`TZ`** que o staging tem (só `FRONTEND_URL` foi reconciliado).
- **Spec 0006 MERGEADA em develop** (PR **#25** → `develop` = `9ca49d7`; CI backend+frontend SUCCESS). **Validado na UI de staging por Jefferson** (login real; Hoje/Contatos/tema ok). DoD completo. Tier Arquitetural; **ADR 0010** (tema/tokens/shell). Escopo: **Fundação + Hoje + Contatos** (Nova mensagem → 0007, depende de GET /modelos).
- ✅ **Fundação:** tokens claro+escuro (variáveis) + selos; tema claro/escuro/sistema (`data-theme` + script pré-pintura, sem flash); shell responsivo (lateral ≥1024 / barra inferior <640); Inter (next/font); guarda de auth; esqueletos. **Sem dep nova.**
- ✅ **Hoje** (indicador Programadas + envios programados via GET /agendamentos, contato resolvido, selo, recorrência, limite 8; demais indicadores stub) e **Contatos** (lista tabela/cartões, criar/editar, consentimento, descadastro, import CSV/XLSX).
- ✅ **Gates:** tsc+eslint+build verdes; smoke SSR (login/tema/hoje/contatos/painel); /revisar+/seguranca sem P0/P1. Arquivos: `frontend/app/(app)/{hoje,contatos}`, `components/*`, `lib/{api,tema}.ts`, `globals.css`, `layout.tsx`.

## Frente anterior (concluída): spec 0005 — recorrência MERGEADA (#23) e EM PRODUÇÃO (#24)
- **Spec 0005 — recorrência MERGEADA** (PR **#23** → `develop` = `07eb60e`, 2026-11-04; branch `feat/0005-recorrencia` apagada). Esteira SDD completa + código TDD. Implementa ADR 0005/0009 (ocorrência = nova linha; `agendamento_pai_id`; dedup por índice único parcial `UNIQUE(agendamento_pai_id, executar_em) WHERE agendamento_pai_id IS NOT NULL`; criação lazy via RRULE/`python-dateutil`).
- ✅ **/clarificar (aprovado por Jefferson):** aceitar qualquer RRULE válida (núcleo testado); `cancelar-serie` só futuras pendentes; criação **lazy**. `UNTIL` exigido em UTC.
- ✅ **Gates verdes (CI do PR #23: backend+frontend SUCCESS):** ruff/mypy limpos; ciclo de migração ok; **168 passed, cobertura 97.2%**; pip-audit sem vulns. **/revisar**+**/seguranca** sem P0/P1 (hardening `max_length=500`). **/validar** AC-1..AC-13 cobertos (double-check adicionou guarda explícita do índice parcial).
- Arquivos: `services/recorrencia.py`, migração `4ff11dacdb87`, `models/agendamento.py` (índice no `__table_args__`), `worker/disparo.py` (`_criar_proxima_ocorrencia` + auditoria `agendamento.ocorrencia_criada`), `api/agendamentos.py` (recorrencia no criar + `cancelar-serie`), `schemas/agendamento.py`. Head Alembic em develop: `4ff11dacdb87` (único).

## Próximo passo (retomar aqui — NADA em andamento; escolher a frente)
1. **Validar visualmente a UI de produção** (0006): login + Hoje/Contatos/tema em `https://menssageiro-ia-frontend-production.up.railway.app` — pendente com Jefferson.
2. **Escolher a próxima frente** e abrir com `/nova-feature`. Candidata natural: **Nova mensagem (spec 0007)** — criar agendamento pela UI; **pré-requisito: criar `GET /modelos` no backend** (hoje só existe `enviar-teste`). Alternativas: mais telas do PWA (Agenda/Modelos/Histórico), anexos (DOCUMENT).
3. **Observação P2 da 0005 (não bloqueia):** worker usa `apos=executar_em` → série atrasada recupera 1 ocorrência/ciclo. Envio real à Meta segue adiado (número +55).

## Contexto de fundo (não é a frente ativa)
1. ✅ **Deploy da Fase 4 em staging CONFIRMADO + write path validado** (2026-11-04): backend+worker `SUCCESS` no commit `c46bc89`; migração `5d75fec0aa05` aplicada (visto no log do deploy). **Smoke E2E autenticado** (via `railway ssh` no container, hitando o uvicorn deployado): seed Modelo `teste_fase4` → `POST /agendamentos` **201** → `GET` 200. Sessão+agendamento de teste limpos; **Modelo `teste_fase4` (aprovado) mantido** em staging p/ futuros testes. *(O erro "Railpack/start.sh" do painel era log antigo de 01/11, já resolvido.)* **Falta só o envio REAL (worker→Meta), que depende da Fase 0.**
2. **Validação REAL do envio: ADIADA para o go-live** (precisa de número +55 real — ver Bloqueios). Não é frente ativa. Próxima frente de implementação a escolher: **recorrência (spec 0005)**, **anexos (DOCUMENT)**, ou **telas do PWA (Fase 5)**. Follow-ups P2/§12 do PR #22 também abertos. Gap: sem CRUD de `Modelo`.
3. ✅ **Promoção `develop`→`main` FEITA** (PR #24, 2026-11-04, `main=d43fc8f`). Produção no ar: backend `577359d9` SUCCESS + worker `8d0ca1d5` SUCCESS (online); frontend `SKIPPED` (inalterado desde 01/11 — já estava atual). Migração `4ff11dacdb87` aplicada no banco de produção (visto no log do deploy). Envio real segue inerte (sem número +55).
4. **Follow-ups registrados no PR #22** (não bloqueiam): alerta de observabilidade §12; P2 (limite diário por-agendamento, N+1, `contato_id` inexistente→500, cap em `variaveis`).
5. **Próximas specs:** recorrência (RRULE/`python-dateutil`, spec 0005) e anexos (DOCUMENT) — colunas inertes já no schema.
6. ⚠️ **Flakiness local:** `localhost`→IPv6(`::1`) falha; container em `127.0.0.1`. Testes locais com `DATABASE_URL=...@127.0.0.1:5434/mensageiro`. (CI usa Postgres próprio.)

## Decisões/trabalho desta sessão (2026-11-04)
- **Spec 0004 + ADR 0008** (config runtime em `configuracoes`; idempotência **at-most-once por (agendamento, contato)** com reserva-antes-de-enviar; janela JSONB em America/Sao_Paulo). `/clarificar` fechou: `limite_diario` na tabela (env só semeia), `limite_por_contato_dia` default NULL (sem limite), `aguardando_decisao` detectado **e** resolvível por API (`reenviar`/`cancelar`), reagenda→próximo início/adia→dia seguinte, colunas inertes de recorrência já na migração.
- **Implementado (tasks 1–6):** ADR 0008; modelos `Agendamento` (CHECK contato xor grupo) + `Configuracao`; FK `envios.agendamento_id→agendamentos` + migração `5d75fec0aa05` (downgrade ok, seed da config); `config.limite_diario_default`; API `/agendamentos` (criar/listar/cancelar/reenviar). Recorrência e anexos ficaram **fora** (specs seguintes).
- **PR #21 aberto** (branch `docs/fase0-webhook-callback-e-test-number` → `develop`): corrige a callback do webhook para **`/webhook/meta`** (RAILWAY.md estava com `/api/...` → daria 404) e documenta `WHATSAPP_TEST_NUMBER` + `GRAPH_API_VERSION=v26.0`. `/revisar` limpo; PR só de doc.

## Bloqueios / pendências
- **Fase 0 — validação do envio REAL ADIADA (decisão 2026-11-04).** Cronologia: (1) erro `131031` "Business Account locked" **RESOLVIDO** preenchendo Informações da empresa no `business.facebook.com`. (2) Surgiu `130497` "restricted from messaging users in this country": o **número de teste da Meta é americano (+1)** e **não entrega no Brasil (+55)** — cross-country p/ Brasil é bloqueado **sem workaround conhecido** (ver [[meta-numero-teste-nao-entrega-brasil]]). **Conclusão: o número de teste é beco sem saída para este projeto** (uso = enviar p/ +55). Validação real exige **número +55 real** numa WABA (caminho de produção: número do cliente, ou um +55 dedicado + verificação). **Decisão: adiar** a validação de envio real para o go-live com o cliente; seguir com o código (já testado por mocks + write path validado em staging).
  - **Valores já coletados** (app de teste do responsável): `PHONE_NUMBER_ID=1457634440766192`, `WABA_ID=1679341853598307`, número de teste `+1 555-148-9020`. (App id `2093735544592019`.)
  - Projeto é **para terceiro**: número real pertence ao cliente → produção exige o cliente dar acesso admin ao Business Manager dele (ou Embedded Signup). Decisão/§4 para depois.
- **Gap p/ validação real:** **não há CRUD de `Modelo`** — a tela/endpoint só existe para `enviar-teste`. Para o worker ter o que enviar, hoje precisa **insert manual** de `Modelo` (nome idêntico ao template aprovado; webhook casa por `Modelo.nome`). Considerar um endpoint de modelos numa spec futura.
- **Validar Fase 2 em staging** (DoD 0002): import com `validar_fase2.csv` (scratchpad), esperado total=3/criados=2/erros=1.
- Pendência de segurança herdada: **cifrar `totp_secret` em repouso**.

## Estado do git
- Branch atual: **`develop`** = `4ce95dd` (+ commit de STATE desta sessão), limpo. **Sem PR aberta** (o #26 foi mergeado).
- `main` = `8b1d43f` (release #26, spec 0006 — PWA telas em produção). **`develop` = `main` em conteúdo** (0 commits à frente; o merge commit vive só em `main`).
- **Higiene feita (2026-11-05):** apagadas remotas mergeadas `feat/0003` (local+remota), `feat/0004`/`feat/0005` já tinham sido podadas. Remotas vivas: só `develop` e `main`. `main` local atualizado p/ `8b1d43f`.
- Head Alembic: `4ff11dacdb87` (único) — a 0006 não mexeu em schema.
- Locais não mergeadas (mantidas): `docs/codebase-map` (`6f03cdc`), `chore/railway-procfile` (`879c09a`, trabalho não integrado).

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07`)
- **staging** 🟢 segue `develop`; **produção** segue `main`. Dev/testes locais: `docker compose up -d db` (container `mensageiro-ia-db-1`, Postgres 17, porta 5434) — **está de pé** (healthy).
- Webhook staging (quando a Fase 0 liberar): `https://menssageiro-ia-backend-staging.up.railway.app/webhook/meta`.

## Fase 3 — entregue (PR #20; specs/0003-whatsapp-cloud-api)
- `whatsapp_client` (enviar_template c/ retry, upload_midia, componente_documento), webhook `/webhook/meta` (verify, HMAC corpo-cru, statuses→envios por wamid, template_status_update→modelos), `POST /modelos/{id}/enviar-teste` restrito ao nº de teste. 102 passed. Pendente p/ "pronto": validação real (depende da Fase 0).
