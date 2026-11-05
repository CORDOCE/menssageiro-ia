# Dívida técnica e pendências — plano de remediação

> Levantado em 2026-11-05. Cada item tem evidência, prioridade e **plano passo a passo**.
> Marcação: `[verificado]` = conferido no código nesta sessão; `[registro]` = vem de review/STATE anterior, ainda não re-verificado.
> Fluxo obrigatório de cada correção (CLAUDE.md §4): branch a partir de `develop` → `/revisar` → `/seguranca` → `/validar` → CI → PR. Mudança de schema → `/migracao`. Decisão difícil de reverter → ADR. Dep nova / infra / regra de envio/IA → **aprovação do Jefferson**.

Ordem recomendada de ataque: **Segurança (S1–S3)** → gaps que destravam produto (F1) → robustez (R1) → resto.

---

## 🔴 SEGURANÇA (prioridade máxima)

### S1 — Cifrar `totp_secret` em repouso
> **✅ FEITO e EM PRODUÇÃO** (2026-11-05, spec 0007 / ADR 0011, PRs #27→develop e #28→main). Follow-up (remover tolerância de claro → `decifrar_segredo` estrito) **também concluído** (branch `fix/0007-decifrar-estrito`).
- **Problema:** `backend/app/models/usuario.py:25` guarda o segredo TOTP em **texto puro** (`String(64)`). Quem acessar o banco clona o 2FA. [verificado]
- **Decisão prévia (ADR):** escolher mecanismo. Duas opções:
  - **(A) pgcrypto** (extensão nativa do Postgres) — **sem dep nova**; cifra/decifra em SQL com chave passada pela aplicação.
  - **(B) `cryptography`/Fernet** na aplicação — **dep nova** (precisa aprovação §4); mais portável, chave só no app.
  - Recomendação: **(A) pgcrypto** para evitar dep nova; registrar em ADR (gestão e rotação da chave).
- **Passos:**
  1. `/nova-feature` com AC: "segredo nunca trafega/repousa em claro; login 2FA continua funcionando; rotação de chave documentada". Escrever **ADR** da abordagem + gestão da chave.
  2. Adicionar `TOTP_ENC_KEY` ao `core/config.py` e às variáveis da Railway (**staging e produção** — infra, aprovação §4).
  3. Implementar helpers `cifrar_totp`/`decifrar_totp` (em `core/security.py`).
  4. `/migracao` aditiva: cifrar o(s) segredo(s) existente(s) no `upgrade` (hoje só 1 admin) e decifrar no `downgrade`; a chave precisa estar no ambiente da migração.
  5. Ajustar escrita (`app/criar_admin.py`) e leitura (`_totp_confere` em `api/auth.py`) para cifrar/decifrar.
  6. **Testes:** round-trip cifra/decifra; login 2FA verde; `alembic upgrade head && downgrade base` ok.
  7. Validar em **staging** (toca auth) antes do PR. Rodar `/seguranca`.

### S2 — Endurecer o armazenamento do token (cookie HttpOnly)
> **✅ FEITO e EM PRODUÇÃO** (2026-11-05, spec 0008 / ADR 0012, proxy same-origin; PRs #31→develop, #32→main). Login validado em staging. Follow-up: remover fallback Bearer.
- **Problema:** token de sessão em `localStorage` (`frontend/lib/auth.ts:1-27`) → exposto a **XSS**. ADR 0010 já marcou como adiado. [verificado]
- **Natureza:** mexe em autenticação/sessão → **ADR** (estende ADR 0001/0004) e **validação em staging** obrigatórias.
- **Passos:**
  1. `/nova-feature` + **ADR**: cookie `HttpOnly; Secure; SameSite=Strict`; decidir estratégia **CSRF** (com `SameSite=Strict` e sem formulários cross-site pode bastar; senão, token anti-CSRF) e a mudança de CORS.
  2. **Backend:** no `POST /auth/login`, emitir `Set-Cookie` com o token (HttpOnly/Secure/SameSite); `core/auth_deps.py` passa a ler a sessão do **cookie** (além de, ou no lugar de, `Authorization`); `logout`/`logout-todos` limpam o cookie.
  3. **CORS** (`main.py:24-30`): com cookie, `allow_credentials=True` + origem exata (já é `FRONTEND_URL`). Revisar cabeçalhos.
  4. **Frontend:** remover `salvarToken/lerToken/limparToken` do `localStorage` (`lib/auth.ts`); `fetch` com `credentials: "include"` (`lib/api.ts`); `GuardaAuth` passa a depender do `GET /auth/me` via cookie.
  5. **Testes:** login grava cookie; rota protegida autentica por cookie; logout limpa; caso CSRF coberto.
  6. Validar em **staging** (login real + 2FA) antes do PR. `/seguranca`.

### S3 — Inicializar o Sentry (erros não estão sendo enviados)
> **✅ FEITO e EM PRODUÇÃO** (2026-11-05, spec 0009; PRs #30→develop, #32→main). Inerte até setar `SENTRY_DSN` na Railway.
- **Problema:** existe `sentry_dsn` (`core/config.py:42`) mas **nenhum `sentry_sdk.init()`** no backend nem no worker → o §7 do CLAUDE.md ("todo erro vai ao Sentry") **não está cumprido**. `sentry-sdk` **não é dependência**. [verificado]
- **Passos:**
  1. Aprovar a dep `sentry-sdk` (§4: necessidade = observabilidade exigida pelo §7; manutenção ativa; licença MIT). Fixar versão em `backend/pyproject.toml`.
  2. `sentry_sdk.init(dsn=settings.sentry_dsn, ...)` **condicional** (`if settings.sentry_dsn`) no startup da **API** (`main.py`) e do **worker** (entrypoint do worker).
  3. **Scrubbing de PII** (§6): `before_send` mascara telefone/token e remove corpo de mensagem — nenhum PII vai ao Sentry. Anexar `correlation_id` ao escopo.
  4. Definir `SENTRY_DSN` na Railway (**staging e produção** — infra, aprovação §4).
  5. **Teste/validação:** exceção forçada em staging aparece no Sentry **sem PII**, com `correlation_id`.

---

## 🟠 GAPS FUNCIONAIS

### F1 — CRUD de `Modelo` (`GET/POST /modelos`)
> **✅ FEITO (GET + sincronizar)** — spec 0010, PR #33 → develop (2026-11-05). `GET /modelos` + `POST /modelos/sincronizar` (lê templates da Meta, upsert). Validar sync em staging. Criar/submeter template na Meta = spec futura.
- **Problema:** `api/modelos.py` só tem `POST /{id}/enviar-teste`; sem listar/criar modelo. Bloqueia **spec 0007 (Nova mensagem)** e exige insert manual para o worker enviar. [verificado]
- **Passos:** `/nova-feature` → `GET /modelos` (lista; usado pela UI de Nova mensagem) e `POST /modelos` (criar/sincronizar com a Meta — usar `/meta-whatsapp`); authz em todo endpoint; testes de contrato; cobertura. Pré-requisito explícito da spec 0007.

### F2 — Telas do PWA restantes
- **Pendente:** Agenda, Modelos, Histórico; **Nova mensagem** (= spec 0007, depende de F1); indicadores de gasto/saúde/histórico na tela Hoje são **stub** (sem endpoint — ADR 0010). [verificado/ADR]
- **Passos:** uma `/nova-feature` por tela (tier da 0006 como referência); cada indicador stub vira real só quando o endpoint existir (criar o endpoint antes). `frontend-design` + smoke `webapp-testing`.

### F3 — Anexos (DOCUMENT) fim-a-fim
- **Pendente:** colunas inertes no schema; `whatsapp_client` já tem `upload_midia`/`componente_documento`, mas não há fluxo de upload→agendamento→envio. [registro/STATE]
- **Passos:** `/nova-feature` com **revisão de superfície de ataque** (upload: tamanho/tipo/conteúdo não confiável — §6); `/meta-whatsapp`; `/migracao` se precisar ativar colunas; testes de borda do upload.

### F4 — Persistência de tema no backend & auto-refresh do Hoje (30s)
- **Pendente:** ADR 0010 adiou ambos. [verificado via ADR]
- **Passos:** endpoint de preferências (tema) + sincronização no `lib/tema.ts`; auto-refresh do Hoje por polling/revalidação a cada 30s (DESIGN §5). Baixa prioridade.

---

## 🟡 ROBUSTEZ / PERFORMANCE

### R1 — Hardening da API de agendamentos (lote dos follow-ups do PR #22) [registro]
- **Itens:** (a) `contato_id` inexistente → **500** (deveria ser 4xx); (b) **N+1** na listagem; (c) sem **cap em `variaveis`**; (d) **limite diário por-agendamento** não implementado (só o global).
- **Passos:** um `/nova-feature` "hardening de agendamentos" cobrindo os quatro: validar FK de contato (→404/422); eager-load na listagem (corrigir N+1) com teste de nº de queries; `max_items`/tamanho em `variaveis` (Pydantic); coluna/regra de limite por-agendamento (**toca regra de envio → aprovação §4**, `/migracao` se precisar de coluna). Re-verificar cada um no código antes de corrigir (hoje são `[registro]`).

### R2 — Recorrência: recuperação de série atrasada [registro/STATE]
- **Problema:** worker usa `apos=executar_em` → série atrasada recupera **1 ocorrência por ciclo**.
- **Passos:** decidir política (pular as perdidas vs. recuperar em lote respeitando idempotência §5.2) — **toca regra de envio → aprovação §4**; teste que simula série atrasada; ajustar `worker/disparo.py`.

---

## 🟡 OBSERVABILIDADE

### O1 — Alerta/métrica do fluxo de disparo (BRIEFING §12) [registro, PR #22]
- **Problema:** `correlation_id` e auditoria existem, mas falta o **alerta/métrica** do §12 no fluxo de disparo. [verificado parcial]
- **Passos:** definir a métrica/alerta (BRIEFING §12) e incluí-la no mesmo PR da próxima mudança do fluxo de disparo (§7 exige). S3 (Sentry) é pré-requisito natural.

---

## 🟢 INFRA / CONFIG

### I1 — Paridade de variáveis staging × produção (backend)
- **Problema:** produção sem `OPENAI_MODEL` (cai no default `gpt-6-luna`) e `TZ`. [verificado nesta sessão]
- **Passos:** ao ligar IA/envios em produção, reconciliar as env vars (aprovação §4); conferir `OPENAI_MODEL` desejado e `TZ`. Ver [[producao-login-exige-frontend-url-e-criar-admin]].

### I2 — Validação do envio REAL (Fase 0) — bloqueio de go-live [STATE/memória]
- **Problema:** depende de número **+55** real; o nº de teste (+1) não entrega no Brasil (erro 130497). [memória]
- **Passos:** obter número +55 (do cliente via Business Manager, ou +55 dedicado + verificação); então smoke E2E de envio real em staging. Não é dívida de código.

---

## 🟢 QUALIDADE DE TESTE

### Q1 — Testes automatizados de frontend + contraste WCAG no CI
- **Problema:** frontend sem test runner (Vitest/Playwright = dep nova §4); AC validados por `eslint`+`tsc`+`build`+smoke manual. Contraste AA só manual. [verificado via ADR 0010]
- **Passos:** ADR + aprovação de dep para Vitest/Playwright; smoke virando teste versionado; job de contraste no CI. Baixa prioridade enquanto o frontend for pequeno.

---

## 🟢 DOCUMENTAÇÃO / HIGIENE DE REPO

### D1 — `tasks.md` desatualizados
- **Problema:** specs 0002/0003/0004 mostram tudo "todo" apesar de entregues e em produção. [verificado]
- **Passos:** marcar as tasks como `done` (ou arquivar as specs encerradas). PR só de doc (dispensa Docker, mas não `/revisar`).

### D2 — Branches órfãs
- **Problema:** `chore/railway-procfile` é **cruft** (10894 linhas atrás de develop — apagaria specs; o multi-dispositivo que o nome sugere **já está em develop**). `docs/codebase-map` tem o `CODEBASE_MAP.md` **não mergeado**. [verificado]
- **Passos:** apagar `chore/railway-procfile` (local); decidir sobre `docs/codebase-map` — se o `CODEBASE_MAP.md` é desejável (CLAUDE.md global sugere), finalizar e mergear via PR; senão, apagar.

### D3 — Validação da Fase 2 em staging (DoD 0002) [STATE]
- **Problema:** import de `validar_fase2.csv` não validado em staging (esperado total=3/criados=2/erros=1).
- **Passos:** rodar o import em staging e conferir o resultado; fechar o DoD da 0002.
