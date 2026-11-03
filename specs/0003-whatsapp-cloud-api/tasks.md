---
name: tasks-whatsapp-cloud-api
description: Quebra de tasks da Fase 3 (0003-whatsapp-cloud-api). Cada task mapeia 1+ AC e aponta o gate (comando de teste) que a prova.
---

# Tasks: Integração WhatsApp Cloud API (Fase 3)

**Pré-condições (não são tasks desta feature):**
- Fase 2 (contatos) mergeada em `develop` — fornece `Contato`, `core/telefone`, `usuario_atual`, `core/audit`.
- **Fase 0 (responsável):** credenciais Meta na Railway + número de teste + template UTILITY aprovado. Sem
  elas, os AC passam por **mock**; a validação real (em staging) fica pendente até existirem.

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 1 | ADR 0007 em `docs/decisoes/` (integração Cloud API: httpx+`GRAPH_API_VERSION`; `envios` por `wamid`; webhook assinatura-primeiro; `envios.agendamento_id` nullable estendendo ADR 0005) | — | — | arquivo presente e linkado no `design.md` | todo |
| 2 | `models/modelo.py` + `models/envio.py` + `schemas/` (modelos `modelos`/`envios`; `wamid` unique; `agendamento_id` nullable; `pricing`/`conversation` JSONB) | AC-12, AC-13 | pré | `ruff`+`mypy` 0; teste que instancia + unicidade parcial | todo |
| 3 | Migration Alembic aditiva: `modelos` + `envios` + **índice único parcial** `(agendamento_id, contato_id) WHERE agendamento_id IS NOT NULL` (via `/migracao`) | AC-12, AC-13 | 2 | `alembic upgrade head && downgrade base` → 0 | todo |
| 4 | `core/config.py`: `graph_api_version` (default `v26.0`) + `whatsapp_test_number` (allowlist do teste) | AC-1, AC-16 | pré | `mypy` 0; teste de settings | todo |
| 5 | `services/whatsapp_client.py`: `enviar_template` + **retry** exp (429/5xx, máx. 3) + erro definitivo | AC-1, AC-2, AC-3 | 4 | testes com **mock httpx** (payloads da doc): corpo correto, wamid, retry, erro | todo |
| 6 | `services/whatsapp_client.py`: `upload_midia` + cabeçalho DOCUMENT *(baixa prioridade)* | AC-4 | 5 | teste mock: media id no componente `document` | todo |
| 7 | `api/webhook_meta.py` `GET`: verificação `hub.*` → `challenge`/403 | AC-5 | pré | teste: 200+challenge; token errado → 403 | todo |
| 8 | `api/webhook_meta.py` `POST`: validação `X-Hub-Signature-256` sobre o **corpo cru** (`compare_digest`), 403 antes de parsear | AC-6 | 7 | teste: assinatura válida vs inválida (nada processa) | todo |
| 9 | Webhook `POST`: `statuses`→`envios` (casa `wamid`; grava `pricing`/`conversation`; `errors`→`falhou`) + **dedup** idempotente | AC-7, AC-8, AC-9 | 8,2 | testes da **matriz** (status/errors/dup/wamid desconhecido) | todo |
| 10 | Webhook `POST`: `message_template_status_update`→`modelos`; mensagem recebida → 200-ack sem persistir | AC-10, AC-11 | 8,2 | testes: modelo atualizado; recebida não persiste | todo |
| 11 | `POST /modelos/{id}/enviar-teste` protegido (`usuario_atual`), allowlist do número de teste, cria `envio` avulso + chama cliente (mock) | AC-14, AC-15, AC-16 | 5,2 | testes: 401 sem auth; teste ok; número ≠ teste → 403/422 | todo |
| 12 | Mascaramento/auditoria sem PII no envio e no webhook (telefone mascarado; sem token/corpo com PII) + rate limit no webhook (§6) | AC-17 | 5,9 | teste: captura log/auditoria e verifica máscara | todo |
| 13 | Suíte + cobertura ≥90% das regras; `ruff`/`mypy` 0; **nenhum** teste chama a API real | AC-18 | 1–12 | `pytest --cov` → 0 e cobertura ≥90% | todo |

> CI: reaproveita `ci.yml`; nenhum workflow novo. **Sem dependência nova** (httpx + hmac/hashlib). Mídia (task 6)
> é baixa prioridade — o gate "pronto" usa template só-texto.

## Ordem sugerida
1 (ADR) → 2 → 3 (migração) → 4 → 5 e (7 → 8 → 9 → 10) em paralelo → 11 → 12 → 13. Task 6 por último.
Antes do PR: `/revisar` → `/seguranca` (atenção: webhook público, corpo cru, segredos, PII) → `/validar` + CI
Docker. **Validação real** (template ao número de teste + status pelo webhook) só em **staging**, após a Fase 0.

## Definition of Done (resumo — detalhe no CLAUDE.md §9)
- [ ] Todo AC verde pelo gate (matriz coberta linha a linha); nenhum teste chama a Meta real.
- [ ] Cobertura ≥90% das regras; `ruff`/`mypy` 0.
- [ ] `/revisar` sem P0/P1 e `/seguranca` sem Crítico/Alto (webhook/segredos/PII); zero segredo no diff.
- [ ] ADR 0007 presente; invariantes §5.1 (API não agenda), §5.3 (template UTILITY), §4 (sem número real) respeitadas.
- [ ] Commit limpo (zero co-autoria); PR com objetivo/risco/plano de teste + fontes da doc Meta (URL+data).
- [ ] Validado em **staging** com o número de teste (template enviado; entregue/lido gravados) — depende da Fase 0.
- [ ] `STATE.md` atualizado.
