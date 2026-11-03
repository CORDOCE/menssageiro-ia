# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-03_

## Em andamento
- **Nada em implementação.** Fase 2 (contatos + importação) no ar; `main` publicada e promovida; **produção repointada para `main`** (deploy em curso ao fim desta sessão).

## Próximo passo
1. **Validar a Fase 2 em staging** (DoD pendente, spec 0002): importar planilha CSV/XLSX por `POST /contatos/importar` (multipart, campo `arquivo`) e confirmar que **nenhum envio** ocorre. **Bloqueado agora:** 2FA indisponível (telefone do responsável descarregado).
2. Confirmar que os 3 serviços de produção subiram verdes a partir de `main` (deploys disparados 18:12 UTC).
3. `docs/codebase-map` (local) → abrir PR (CODEBASE_MAP útil); avaliar descarte da local `chore/railway-procfile`.

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
- **produção** segue **`main`** (repoint desta sessão): backend `menssageiro-ia-backend-production.up.railway.app` + worker + frontend + Postgres. Deploys de main disparados 18:12 UTC — confirmar verdes.
- Dev/testes locais: `docker compose up -d db` (container `mensageiro-ia-db-1`, Postgres 17, porta 5434).

## Estado do git
- Branch atual: **`develop`** = `86b203a` (publicada em `origin/develop`). `origin/main` = `9ab9cbd` (merge #19) — `main` e `develop` em sincronia (0 à frente).
- `origin` só com `develop` e `main`.
- Locais preservadas com commit **não** mergeado: `docs/codebase-map` (`6f03cdc`, CODEBASE_MAP) e `chore/railway-procfile` (`879c09a`, conteúdo já na develop por outro SHA). `main` local também existe.
