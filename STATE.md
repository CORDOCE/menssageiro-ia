# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-03_

## Em andamento
- **Fase 2 (`specs/0002-contatos-importacao/`) EM IMPLEMENTAÇÃO.** Branch `feat/0002-contatos`.
- Tasks 1–7 feitas e **commitadas** (TDD, verde). Task 8 implementada mas **não commitada** — bloqueada por decisão §4 (dependência nova).

## Próximo passo
1. **Resolver o gate §4 da task 8** (ver bloqueios): aprovar `python-multipart` OU trocar o endpoint para corpo bruto. Só então commitar a task 8.
2. Seguir: **task 9** (auditoria do import sem PII — contagens, telefone mascarado), **task 10** (cobertura ≥90% das regras), **task 12** (ADR 0006 já existe — conferir/adendar se aprovar multipart).
3. Antes do PR: `/revisar` → `/seguranca` (atenção a upload/arquivo e PII) → `/validar` + suíte de CI no host via Docker.

## Fase 2 — progresso (branch `feat/0002-contatos`, a partir da develop atual)
- **Commitado e verde (65 passed, ruff+mypy limpos):**
  - `9aa990c` tasks 1/2/3/11: modelo `Contato` (telefone_e164 único, consentimento=false, descadastro soft); migração Alembic aditiva `60e87808c17a` (round-trip OK, AC-19); `core/telefone.py` (E.164 + máscara); deps `phonenumbers`/`openpyxl`.
  - `3efc02c` tasks 4/5/6: CRUD protegido (`api/contatos.py`), descadastrar, consentimento; schemas com normalização E.164 (inválido→422) e dedup (409). Fixture `auth_headers` no conftest.
  - `402a9de` task 7: `services/contatos_import.py` — matriz de decisão completa (upsert, não-ressuscita descadastrado, parcial por linha, relatório com telefone mascarado). CSV+XLSX.
- **Uncommitted (task 8):** endpoint `POST /contatos/importar` (multipart) + limites `import_max_bytes`/`import_max_linhas` no `config.py` e `max_linhas` no serviço. Código correto; 4 testes em `test_contatos_import_endpoint.py` ficam vermelhos **só** por falta de `python-multipart`.
- ACs provados por teste até aqui: AC-1..AC-16, AC-18, AC-19. Faltam AC-17 (depende do endpoint) e AC-20 (cobertura).

## Bloqueios/pendências
- **§4 — dependência nova `python-multipart`** (task 8): não coberta pelo ADR 0006 (só `phonenumbers`/`openpyxl`). FastAPI exige para `UploadFile`/form-data; alternativa nativa = receber corpo bruto (desvia do design "multipart"). **Aguarda aprovação do responsável.** Não instalada.
- Ambiente de teste: Postgres de dev via `docker compose up -d db` (container `mensageiro-ia-db-1`, porta 5434).
- (Fase 1, não bloqueiam) **Repoint `production → main`** manual na Railway; endurecimentos: cifrar `totp_secret`, alerta `login_bloqueado`, cookie HttpOnly, contraste WCAG no CI.
- Mapa do codebase em `docs/CODEBASE_MAP.md` (Cartographer) ficou na branch `docs/codebase-map` (commit, sem PR).

## Infra (Railway — projeto `406f04bb-7659-4366-aea0-f9489dbf0b07` "intuitive-emotion")
- **staging** 🟢 `api`, `worker`, `frontend`, `Postgres`. Deploy: push em `develop` → staging. (produção ainda segue `develop`.)

## Estado do git
- Branch atual: **`feat/0002-contatos`** (criada da `develop`=`8ee144b`), 3 commits à frente: `9aa990c`, `3efc02c`, `402a9de`.
- **Não commitado:** task 8 (`config.py`, `services/contatos_import.py`, `api/contatos.py`, `tests/test_contatos_import_endpoint.py`). Suíte vermelha só por causa da dep ausente.
- Branch antiga `feat/0002-contatos-importacao` (local) estava 33 commits atrás e foi **apagada**; a remota `origin/feat/0002-contatos-importacao` segue obsoleta (sem PR). **Sem PRs abertos.**
- `docs/codebase-map`: 1 commit (`6f03cdc`, CODEBASE_MAP + ponteiro no CLAUDE.md), sem PR.
