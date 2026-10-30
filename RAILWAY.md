# RAILWAY — Infraestrutura do Mensageiro

> Instruções para criar o ambiente na Railway e desativar o ambiente antigo.
> Executar na ordem. Itens marcados [MANUAL] são feitos pelo responsável no painel da Railway.

## 1. Visão geral

| Serviço | Projeto antigo (document-ai-system) | Projeto novo (Mensageiro) |
|---|---|---|
| Backend FastAPI de recibos | **Sai** (desligar após o novo estar estável) | — |
| PostgreSQL antigo | **Sai** (após backup) | — |
| Redis | **Sai** | Não é necessário |
| Evolution API (`evolution-api-production-…up.railway.app`) e serviços que ela usa | **Sai** | Substituída pela Cloud API oficial |
| Frontend antigo (se estiver hospedado lá) | **Sai** | — |
| `api` — FastAPI (pasta `backend/`) | — | **Entra** |
| `worker` — mesmo código, outro comando | — | **Entra** |
| `frontend` — Next.js PWA (pasta `frontend/`) | — | **Entra** |
| `Postgres` — banco novo | — | **Entra** |

A Railway não migra serviços entre projetos: o projeto novo é criado do zero. **Nada do projeto antigo é alterado** até o novo estar em produção.

## 2. Pré-requisitos
- Repositório `mensageiro-whatsapp` no GitHub com `backend/` e `frontend/` (pode começar só com o esqueleto).
- Acesso da Railway ao GitHub autorizado para esse repositório.
- Dados da Meta em mãos (token, IDs, app secret) — podem ser preenchidos depois.

## 3. Criar o projeto [MANUAL]
1. Railway → **New Project** → **Deploy from GitHub repo** → selecionar `mensageiro-whatsapp`.
2. Renomear o projeto para **Mensageiro**.
3. O primeiro serviço criado será o `api` (configurado no passo 4).

## 4. Serviço `api` [MANUAL]
Settings:
- **Service name:** `api`
- **Root Directory:** `/backend`
- **Watch Paths:** `/backend/**`
- **Start Command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Healthcheck Path:** `/health`
- **Networking:** *Generate Domain* (a Meta precisa da URL pública para o webhook)

## 5. Serviço `worker` [MANUAL]
1. No projeto: **New → GitHub Repo →** mesmo repositório.
2. Settings:
   - **Service name:** `worker`
   - **Root Directory:** `/backend`
   - **Watch Paths:** `/backend/**`
   - **Start Command:** `python -m app.worker`
   - **Networking:** **sem domínio público**
   - **Replicas:** 1 (o código é seguro com mais, mas não há necessidade)
   - O worker roda dois laços: envios agendados (a cada 60 s) e **fila de respostas** (a cada ~5 s). Não é preciso
     outro serviço; se o volume de conversas crescer, separar a fila de respostas em um serviço `worker-respostas`.
3. Migrações rodam só no `api` (evita duas execuções simultâneas).

## 6. Serviço `frontend` [MANUAL]
1. **New → GitHub Repo →** mesmo repositório.
2. Settings:
   - **Service name:** `frontend`
   - **Root Directory:** `/frontend`
   - **Watch Paths:** `/frontend/**`
   - **Build/Start:** padrão do Next.js (`npm run build` / `npm run start`)
   - **Networking:** *Generate Domain* (ou domínio próprio, ex.: `app.dominiodocliente.com.br`)

## 7. Banco de dados [MANUAL]
1. **New → Database → PostgreSQL**. Nome: `Postgres`.
2. Em `api` e `worker`, criar a variável `DATABASE_URL` com a **referência** `${{Postgres.DATABASE_URL}}` (não colar a senha).
3. Ativar backups do banco (Settings do Postgres → Backups), se disponível no plano. Caso contrário, criar rotina de `pg_dump` diária.

## 8. Variáveis [MANUAL]

**Compartilhadas (Project → Variables → Shared), usadas por `api` e `worker`:**
`WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`, `WABA_ID`, `APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`, `GRAPH_API_VERSION`,
`ADMIN_WHATSAPP_NUMBERS`, `OPENAI_API_KEY` (copiar o valor do projeto antigo), `OPENAI_MODEL=gpt-6-luna`,
`RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_ALERTAS`, `SENTRY_DSN`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `TZ=America/Sao_Paulo`.

**Só no `api`:** `FRONTEND_URL=https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (remover após o primeiro acesso).

**Só no `frontend`:** `NEXT_PUBLIC_API_URL=https://${{api.RAILWAY_PUBLIC_DOMAIN}}`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY`, `NEXT_PUBLIC_SENTRY_DSN`.

Regras: nunca colar segredos em código, issues ou PRs; nunca copiar o `.env` do projeto antigo.

## 9. Ambientes [MANUAL]
1. **production** (padrão): número real da Meta, branch `main`.
2. **staging**: Project → Environments → **New Environment** → duplicar `production`.
   - Ligar à branch `develop` (ou à de testes).
   - Usar o **número de teste da Meta** e um token/app de teste.
   - Banco próprio (o duplicado já cria um Postgres separado).
3. Fluxo: PR → merge em `develop` → valida em staging → merge em `main` → produção.

## 10. Conectar a Meta ao webhook [MANUAL]
No app da Meta (developers.facebook.com) → WhatsApp → Configuration:
- **Callback URL:** `https://<domínio do api>/api/webhook/meta`
- **Verify token:** o mesmo valor de `WEBHOOK_VERIFY_TOKEN`
- **Campos assinados:** `messages`, `message_template_status_update`, `account_update`
Repetir para staging com o app/número de teste.

## 11. Verificação
- [ ] `api` responde em `/health` e o painel abre no domínio do `frontend`.
- [ ] Logs do `worker` mostram um ciclo por minuto.
- [ ] Webhook verificado pela Meta (selo verde no painel da Meta).
- [ ] Envio de template para o número de teste chega e o status "entregue" aparece no banco.

## 12. Desativar o projeto antigo [MANUAL — só após o piloto aprovado]
1. Backup do banco antigo: `pg_dump` usando a URL pública do Postgres antigo; guardar o arquivo fora do repositório.
2. Remover a instância da Evolution API e os serviços que só ela usa.
3. Remover Redis.
4. Remover o backend e o frontend antigos.
5. Remover o Postgres antigo (após conferir o backup) ou excluir o projeto inteiro.
6. Conferir em **Usage** que o consumo do projeto antigo zerou.

## 13. Custos esperados (Railway)
Plano Hobby (US$ 5/mês com US$ 5 de uso incluso) + consumo. Para api + worker + frontend + Postgres com uso leve,
esperar **US$ 5 a 15/mês** por ambiente. O staging pode ficar **desligado** (scale to zero / remover deploy) quando não estiver em uso para economizar.
