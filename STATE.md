# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-04_

## Em andamento (PAUSADO — /handoff)
- **Spec 0005 — recorrência** (branch **`feat/0005-recorrencia`**, de `develop`; **pushada para `origin`**). Esteira SDD: **`product.md` + `design.md` escritos e commitados**; tier **Arquitetural**. Implementa ADR 0005 (ocorrência = nova linha; `agendamento_pai_id`; dedup por `UNIQUE(agendamento_pai_id, executar_em)`).
- ✅ **Decisão §4 tomada:** usar **`python-dateutil`** (RRULE) — aprovado por Jefferson 2026-11-04. (Fase 4 mergeada/em staging; envio real adiado — ver Bloqueios.)

## Próximo passo (retomar aqui — spec 0005)
1. **`/clarificar`** as 3 questões do design (opções de RRULE na v1; `cancelar-serie` = só futuras pendentes; confirmar criação lazy) → escrever **`spec.md`** (AC + tabela/bordas).
2. **`tasks.md`** (TDD) → implementar: add `python-dateutil` ao `pyproject` (`uv sync`); `services/recorrencia.py` (`proxima_ocorrencia`/`validar_regra`); migração do índice parcial `UNIQUE(agendamento_pai_id, executar_em) WHERE agendamento_pai_id IS NOT NULL`; worker cria próxima ocorrência (ON CONFLICT); API (`recorrencia` no criar + `cancelar-serie`). **ADR 0009**.
3. Gates (/revisar→/seguranca→/validar + CI local IPv4) → PR para `develop`.
1. ✅ **Deploy da Fase 4 em staging CONFIRMADO + write path validado** (2026-11-04): backend+worker `SUCCESS` no commit `c46bc89`; migração `5d75fec0aa05` aplicada (visto no log do deploy). **Smoke E2E autenticado** (via `railway ssh` no container, hitando o uvicorn deployado): seed Modelo `teste_fase4` → `POST /agendamentos` **201** → `GET` 200. Sessão+agendamento de teste limpos; **Modelo `teste_fase4` (aprovado) mantido** em staging p/ futuros testes. *(O erro "Railpack/start.sh" do painel era log antigo de 01/11, já resolvido.)* **Falta só o envio REAL (worker→Meta), que depende da Fase 0.**
2. **Validação REAL do envio: ADIADA para o go-live** (precisa de número +55 real — ver Bloqueios). Não é frente ativa. Próxima frente de implementação a escolher: **recorrência (spec 0005)**, **anexos (DOCUMENT)**, ou **telas do PWA (Fase 5)**. Follow-ups P2/§12 do PR #22 também abertos. Gap: sem CRUD de `Modelo`.
3. **Promover `develop`→`main`** só após staging validado de verdade (§4.2) — hoje `develop` à frente de `main` (Fases 3 e 4 não promovidas).
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
- Branch atual: **`feat/0005-recorrencia`** (de `develop`), **pushada e sincronizada** com `origin` (só spec 0005 product+design; sem código ainda).
- `develop` = `c46bc89` (merge do PR #22, Fase 4). PR #22 (Fase 4) **mergeado**; branch `feat/0004` apagada.
- ⚠️ **PR #21 ABERTO, pendente de merge** (doc Fase 0, `docs/fase0-webhook-callback-e-test-number` → `develop`): corrige callback do webhook p/ `/webhook/meta` + documenta `WHATSAPP_TEST_NUMBER`/`GRAPH_API_VERSION`. `/revisar` limpo. **Ação: revisar e mergear** (independente da 0005).
- `develop` está **à frente de `origin/main`** (Fases 3 e 4 não promovidas — promover só após validação real/Fase 0).
- Locais não mergeadas: `docs/codebase-map` (`6f03cdc`), `chore/railway-procfile` (`879c09a`), `feat/0003` (mergeada, pode apagar).

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07`)
- **staging** 🟢 segue `develop`; **produção** segue `main`. Dev/testes locais: `docker compose up -d db` (container `mensageiro-ia-db-1`, Postgres 17, porta 5434) — **está de pé** (healthy).
- Webhook staging (quando a Fase 0 liberar): `https://menssageiro-ia-backend-staging.up.railway.app/webhook/meta`.

## Fase 3 — entregue (PR #20; specs/0003-whatsapp-cloud-api)
- `whatsapp_client` (enviar_template c/ retry, upload_midia, componente_documento), webhook `/webhook/meta` (verify, HMAC corpo-cru, statuses→envios por wamid, template_status_update→modelos), `POST /modelos/{id}/enviar-teste` restrito ao nº de teste. 102 passed. Pendente p/ "pronto": validação real (depende da Fase 0).
