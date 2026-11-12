# Spec — 0022 Job diário de sincronização de modelos (06:00) — dívida A1

> Tier **Pequeno** (spec + tasks). Toca o **worker** (passo novo no loop) e **refatora** a lógica de
> sincronização para um service reusável. **Sem migração.** Não muda regra de envio nem IA (sincronizar
> modelos é leitura da Meta + upsert). Não precisa §4.

## Contexto / por que
O BRIEFING §10.3 prevê o job diário **06:00 sincronizar modelos**. Hoje a sincronização só acontece
**manual** (botão da tela Modelos, spec 0013) — o job automático nunca entrou em spec (débito A1, de
frente fechada). Sem ele, o status dos templates no banco pode ficar defasado em relação à Meta até o
operador clicar. Esta spec adiciona o passo automático ao worker, reusando a mesma lógica do manual.

## Escopo (v1)
1. **Extrair** a lógica de upsert de `api/modelos.py::sincronizar` para `services/modelos_sync.py`:
   `sincronizar_modelos(db, templates, *, ator_email=None) -> SincronizarResultado` — upsert por
   `(nome, idioma)`, mapa de status Meta→nosso, e auditoria `modelos_sincronizados`. O endpoint passa
   a **buscar** `listar_templates()` e **delegar** ao service (comportamento idêntico).
2. **Worker**: novo passo `ciclo_jobs_diarios(agora)` no loop (análogo a `ciclo_alertas`), que às
   **≥ 06:00 America/Sao_Paulo** e **sem o job já tentado hoje** busca `listar_templates()` e chama o
   service com `ator_email=None` (ator "sistema"). Registra `job.sincronizar_modelos` (status `ok`/`error`).
3. **Degradação**: exceção na sincronização (Meta indisponível / sem credenciais na Fase 0) é capturada —
   registra `job.sincronizar_modelos` (`error`) + Sentry, **não derruba o loop**, e **conta como a
   tentativa do dia** (não re-tenta no mesmo dia: evita martelar a Meta a cada ciclo).

## Suposições (explícitas, reversíveis)
- **S1** — horário do job = **06:00 SP**, constante em `core/config.py` (`sync_modelos_hora: int = 6`).
- **S2** — idempotência diária pelo evento de auditoria `job.sincronizar_modelos` no **dia-calendário SP**
  (molde de `alertas.py::_ja_alertou_hoje`). **1 tentativa/dia**; falha → fallback é o botão manual (0013).
- **S3** — a guarda considera só o evento **do job** (não o `modelos_sincronizados` manual): se o operador
  sincronizou manualmente às 05:00, o job às 06:00 ainda roda 1×. Redundância mínima aceitável (upsert idempotente).

## Critérios de aceite (Given/When/Then)
- **AC-1 (roda no horário)** — Dado `agora ≥ 06:00 SP` e nenhum `job.sincronizar_modelos` hoje (SP) e
  `listar_templates` devolvendo N templates, Quando `ciclo_jobs_diarios(agora)` roda, Então sincroniza
  (upsert) e registra `job.sincronizar_modelos` com status `ok`.
- **AC-2 (cedo não roda)** — Dado `agora < 06:00 SP`, Então `ciclo_jobs_diarios` **não** sincroniza nem audita.
- **AC-3 (idempotência diária)** — Dado que já há `job.sincronizar_modelos` hoje (SP), Então uma 2ª chamada
  no mesmo dia **não** sincroniza de novo.
- **AC-4 (falha degrada)** — Dado que `listar_templates`/upsert lança, Quando o job roda, Então registra
  `job.sincronizar_modelos` com status `error`, **não propaga** (loop segue) e conta como tentativa do dia.
- **AC-5 (manual inalterado)** — `POST /modelos/sincronizar` autenticado continua devolvendo
  `{total, criados, atualizados}` e fazendo o upsert (refactor sem mudança de comportamento; guardado pelos
  testes existentes de `test_modelos_api.py`).
- **AC-6 (service idempotente)** — `sincronizar_modelos(db, templates, ator_email=...)` cria o que falta e
  atualiza o existente por `(nome, idioma)`, e registra `modelos_sincronizados` com os contadores.
- **AC-7 (no-op sem credenciais Meta)** — Dado `waba_id`/`whatsapp_token` **ausentes** (produção Fase 0 /
  testes), Quando o job roda em qualquer horário, Então é **no-op** — não faz rede (§5.7), não audita, não
  propaga. (Padrão do repo: caminhos Meta são inertes sem credenciais.)

## Fora de escopo (vinculante)
- Os demais jobs diários: **07:00 sugestões IA** (Fase 6) e **07:30 resumo** (Fase 7).
- Retry intra-dia em falha (1 tentativa/dia; fallback é o manual). Configurar o horário pela UI.
- Criar/submeter template à Meta (spec futura, dívida F1).

## Arquivos (previsto)
- Backend: `services/modelos_sync.py` (novo: `sincronizar_modelos` + `_extrair_componentes` + `_STATUS_META`
  + `SincronizarResultado`); `api/modelos.py` (passa a delegar); `worker/jobs_diarios.py` (novo:
  `ciclo_jobs_diarios` + guarda de idempotência); `worker/__main__.py` (chama no loop); `core/config.py`
  (`sync_modelos_hora`). Testes: `tests/test_jobs_diarios.py` (AC-1..AC-4), `tests/test_modelos_sync.py`
  (AC-6); `test_modelos_api.py` segue verde (AC-5).
