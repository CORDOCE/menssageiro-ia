# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-03_

## Em andamento
- **Nada em implementação.** Fase 2 (contatos + importação) **mergeada em `develop`** (PR #18) e **no ar em staging e produção**. Produção teve os serviços corrigidos nesta sessão (ver Decisões).

## Próximo passo
1. **Validar a Fase 2 em staging** (DoD pendente da spec 0002): importar planilha CSV/XLSX pela API e conferir que **nenhum envio** ocorre. Precisa de credencial admin + TOTP → melhor você rodar; endpoint `POST /contatos/importar` (multipart, campo `arquivo`).
2. **Decidir `main` no remoto:** o `origin` **não tem `main`** — a promoção `develop→main` e o repoint de produção para `main` ficam impossíveis até publicar `main`. Opção: `git push origin main` a partir da develop atual (pede ok §4).
3. `docs/codebase-map` (local) → abrir PR (o CODEBASE_MAP é útil); avaliar descartar a local `chore/railway-procfile`.

## Decisões desta sessão
- **Fase 2 entregue** (12 tasks, TDD): modelo `Contato`/migração, `core/telefone.py`, CRUD+descadastro+consentimento, serviço de importação CSV/XLSX (matriz de decisão), endpoint multipart. **78 passed, cobertura 98.06%**, CI #18 verde. ADR 0006 + **adendo `python-multipart`** (2026-11-03, §4).
- **Produção corrigida na Railway** (§4, autorizado): frontend tinha build FALHO (faltava `rootDirectory=/frontend`, start, healthcheck, var) → config completada + `NEXT_PUBLIC_API_URL=https://menssageiro-ia-backend-production.up.railway.app` → deploy SUCCESS/online. **Worker nunca instanciado em produção** → criado (source `develop`, root `/backend`, `python -m app.worker`, `DATABASE_URL`→Postgres) → SUCCESS/online.
- **Higiene de branches:** apagadas todas as branches mergeadas (0002 local+remota; 12 locais e 13 remotas da Fase 1). `origin` agora só tem `develop`.

## Notas da Fase 2 (P2/MEDIO — não bloqueiam; revisitar)
- Dedup POST/import é SELECT-then-INSERT → corrida viraria 500 em vez de 409 (1 admin → desprezível; índice único garante a invariante).
- Upload: cap `read(max+1)` limita memória mas o ASGI já recebe o corpo (spool em disco) — endurecer com limite de corpo no proxy. openpyxl `read_only`/`data_only` + limites 5 MB/5000 linhas mitigam zip-bomb.
- Futuro: CSV formula-injection quando houver **export**. Comentário `api/contatos.py` sobre o cap pode ser suavizado.

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07`)
- **staging** 🟢 `api`/`worker`/`frontend`/`Postgres` (segue `develop`).
- **produção** 🟢 `menssageiro-ia-backend`/`worker`/`menssageiro-ia-frontend`/`Postgres` — **todos online após o fix desta sessão**. Backend prod: `menssageiro-ia-backend-production.up.railway.app`. Produção **ainda segue `develop`** (deveria ser `main`; ver Próximo passo #2).
- Dev/testes locais: `docker compose up -d db` (container `mensageiro-ia-db-1`, Postgres 17, porta 5434).

## Estado do git
- Branch atual: **`develop`** = `f8e0d41` (merge do PR #18). **Sem PRs abertos.**
- Remoto `origin`: só `develop` (sem `main` — ver Próximo passo #2).
- Locais preservadas com commit **não** mergeado: `docs/codebase-map` (`6f03cdc`, CODEBASE_MAP) e `chore/railway-procfile` (`879c09a`, task 5b — conteúdo já na develop por outro SHA, provável descarte). `main` existe local, não publicada.
