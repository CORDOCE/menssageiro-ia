# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-03_

## Em andamento
- **Nada em implementação.** Fase 3 (WhatsApp Cloud API) **mergeada** (PR #20) e **no ar em staging** (deploy 863e229 SUCCESS; migração `modelos`/`envios` aplicada). Próxima fase de implementação: **Fase 4** (worker + agendamentos + recorrência).

## Próximo passo
1. **Fase 0 (responsável) p/ ativar o WhatsApp real:** configurar credenciais Meta na Railway (`WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`, `WABA_ID`, `APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`, `WHATSAPP_TEST_NUMBER`) + template UTILITY aprovado + webhook no painel da Meta. **Validação real da Fase 3** (enviar template ao nº de teste; entregue/lido pelo webhook) só depois disso.
2. **Validar a Fase 2 em staging** (DoD 0002): rodar o import com o token de sessão (comando/CSV prontos no scratchpad `validar_fase2.csv`); esperado total=3/criados=2/erros=1. Desbloqueado (login staging voltou).
3. **Iniciar a Fase 4** (`/nova-feature`): worker de disparo, agendamentos, recorrência, janela de envio, expansão de grupo (ADR 0005), anexos. É aqui que `envios` ganha a FK `agendamento_id` e o caminho de produção de envio.
4. `docs/codebase-map` (local) → PR; avaliar descarte da local `chore/railway-procfile`.

## Fase 3 — entregue (PR #20 em `develop`; specs/0003-whatsapp-cloud-api)
- 13 tasks (TDD): ADR 0007; modelos `Modelo`/`Envio` + migração `a6c885be3f81` (índice único parcial `(agendamento_id, contato_id) WHERE agendamento_id IS NOT NULL`); `whatsapp_client` (enviar_template+retry, upload_midia, componente_documento); webhook `/webhook/meta` (GET verify, assinatura HMAC corpo-cru, statuses→envios por wamid c/ monotonicidade, template_status_update→modelos, recebida=200-ack, **auditoria com telefone mascarado**); `POST /modelos/{id}/enviar-teste` restrito ao nº de teste; sem dependência nova.
- **102 passed, cobertura 96.74%**, CI #20 verde. `/revisar` (P1 §5.8 corrigido) e `/seguranca` (sem bloqueio) rodados. Fontes Meta (v26.0) citadas no design/ADR.
- **Endurecimento anotado (não bloqueia):** rate limit do webhook deve ficar na **borda/Railway** (app-level descartaria rajadas legítimas da Meta) — mitigado pela validação assinatura-primeiro.
- Pendente p/ "pronto" (DoD): validação real em staging (depende da Fase 0).

## Incidente resolvido nesta sessão — login staging "credenciais inválidas"
- Causa (via /hipotese): **dessincronia do TOTP/2FA** no autenticador do responsável, NÃO bug. Código de auth inalterado desde 01/11 (quando funcionava); admin existe/ativo/com TOTP; email correto nas falhas. Resolvido por re-cadastro do mesmo segredo (opção A) — login voltou.
- Reforça a pendência: **cifrar `totp_secret` em repouso** (hoje em texto no banco).

## Decisões desta sessão
- **Fase 2 entregue e mergeada** (PR #18): 12 tasks TDD, 78 passed, cobertura 98.06%, CI verde. ADR 0006 + **adendo `python-multipart`** (§4).
- **Produção corrigida (Railway, §4 autorizado):** frontend tinha build FALHO (faltava `rootDirectory=/frontend`, start, healthcheck, var) → config + `NEXT_PUBLIC_API_URL` → online. **Worker** nunca existira em produção → instanciado (root `/backend`, `python -m app.worker`, `DATABASE_URL`→Postgres) → online.
- **`main` publicada** no `origin` e **promovida `develop`→`main`** via PR #19.
  - **Desvio consciente do §4.2** ("develop→main só após staging validado"): promovido **sem** validação em staging — **autorizado explicitamente por Jefferson** (2FA indisponível). Registrado no PR #19.
- **Produção repointada `develop`→`main`** nos 3 serviços (backend/frontend/worker), via staged + accept-deploy, escopado só à produção (staging segue `develop`). Config/variáveis preservadas (só mudou o branch de origem).
- **Higiene:** apagadas todas as branches mergeadas (0002 + 12 locais e 13 remotas da Fase 1). `origin` tem só `develop` e `main`.

## Notas da Fase 2 (P2/MEDIO — não bloqueiam; revisitar)
- Dedup POST/import SELECT-then-INSERT → corrida viraria 500 em vez de 409 (1 admin → desprezível; índice único garante a invariante).
- Upload: cap de leitura limita memória mas o ASGI já recebe o corpo — endurecer com limite no proxy. openpyxl `read_only`/`data_only` + limites 5 MB/5000 linhas mitigam zip-bomb.
- Futuro: CSV formula-injection quando houver **export**.

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07`)
- **staging** 🟢 segue `develop` (api/worker/frontend/Postgres).
- **produção** segue **`main`** (repoint desta sessão), todos online a partir de `main`: api `menssageiro-ia-backend-production.up.railway.app`, frontend `menssageiro-ia-frontend-production.up.railway.app` (domínio gerado nesta sessão), + worker + Postgres. Smoke test OK (`/health` 200; endpoints Fase 2 → 401 sem auth).
- Dev/testes locais: `docker compose up -d db` (container `mensageiro-ia-db-1`, Postgres 17, porta 5434).

## Estado do git
- Branch atual: **`develop`** = `863e229` (merge do PR #20, Fase 3), limpa e sincronizada com `origin/develop`. **Sem PRs abertos.**
- `origin/main` = `9ab9cbd` (merge #19) — **develop agora está à frente de main** (Fase 3 ainda não promovida; promover só após validar em staging/Fase 0).
- `origin` com `develop` e `main`. Branch `feat/0003-whatsapp-cloud-api` já mergeada (pode apagar local/remota na próxima higiene).
- Locais preservadas com commit **não** mergeado: `docs/codebase-map` (`6f03cdc`, CODEBASE_MAP) e `chore/railway-procfile` (`879c09a`). `main` local também existe.
