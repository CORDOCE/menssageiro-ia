# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-03_

## Em andamento
- **Fase 3 (`specs/0003-whatsapp-cloud-api/`) CODE-COMPLETE na branch `feat/0003-whatsapp-cloud-api`** (13/13 tasks, TDD). Produção/staging no ar; login staging restaurado (ver incidente 2FA).

## Próximo passo
1. **Pré-PR da Fase 3:** `/revisar` → `/seguranca` (atenção: webhook público, corpo cru/assinatura, segredos, PII) → `/validar` + CI Docker. Depois abrir PR `feat/0003-whatsapp-cloud-api` → `develop`.
2. **Fase 0 (responsável) p/ validar a Fase 3 em staging:** configurar credenciais Meta (`WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`, `WABA_ID`, `APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`, `WHATSAPP_TEST_NUMBER`) + template UTILITY aprovado + webhook no painel da Meta. Só então: enviar template ao número de teste e conferir entregue/lido via webhook.
3. **Validar a Fase 2 em staging** (DoD 0002): rodar o import com o token de sessão (comando pronto no scratchpad `validar_fase2.csv`); esperado total=3/criados=2/erros=1. Desbloqueado (login staging voltou).
4. `docs/codebase-map` (local) → PR; avaliar descarte da local `chore/railway-procfile`.

## Fase 3 — entregue (branch `feat/0003-whatsapp-cloud-api`, a partir da develop)
- 13 tasks (TDD): ADR 0007; modelos `Modelo`/`Envio` + migração (índice único parcial); `whatsapp_client` (enviar_template+retry, upload_midia, componente_documento); webhook `/webhook/meta` (GET verify, assinatura HMAC corpo-cru, statuses→envios por wamid com monotonicidade, template_status_update→modelos, recebida=200-ack); `POST /modelos/{id}/enviar-teste` restrito ao número de teste; auditoria sem PII.
- **101 passed, cobertura 96.71%**, ruff+mypy 0, Alembic round-trip EXIT=0, pip-audit limpo. **Sem dependência nova** (httpx + hmac/hashlib). Fontes Meta citadas (v26.0) no design/ADR.
- Pendente p/ "pronto": validação real em staging (depende da Fase 0).

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
- Branch atual: **`develop`** = `86b203a` (publicada em `origin/develop`). `origin/main` = `9ab9cbd` (merge #19) — `main` e `develop` em sincronia (0 à frente).
- `origin` só com `develop` e `main`.
- Locais preservadas com commit **não** mergeado: `docs/codebase-map` (`6f03cdc`, CODEBASE_MAP) e `chore/railway-procfile` (`879c09a`, conteúdo já na develop por outro SHA). `main` local também existe.
