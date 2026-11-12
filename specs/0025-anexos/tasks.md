# Tasks — 0025 Anexos (PDF/boleto no cabeçalho DOCUMENT)

| # | Task | AC | Gate (teste) | Status |
|---|---|---|---|---|
| 1 | `models/anexo.py` (bytea + metadados) + `agendamentos.anexo_id` FK + migração | AC-2,5 | `alembic upgrade/downgrade` ok | todo |
| 2 | `core/config.py`: `anexo_max_bytes` (5 MB) | AC-4 | referência nos testes | todo |
| 3 | `schemas/anexo.py` + `api/anexos.py` (`POST /anexos` multipart: mime+magic+cap) + registro `main.py` | AC-1..AC-4 | `test_anexos_api.py`: 401; PDF ok; não-PDF 422; grande 422 | todo |
| 4 | `schemas/agendamento.py` + `api/agendamentos.py`: `anexo_id` opcional + regra de coerência DOCUMENT↔anexo | AC-5..AC-8 | `test_agendamentos_api.py`: tabela-verdade (4 linhas) | todo |
| 5 | `worker/disparo.py`: no disparo com anexo, `upload_midia` 1×/lote + `componente_documento` nos componentes; falha→`falhou`+alerta | AC-9,10,11 | `test_worker_disparo.py`: upload chamado 1×; media_id nos N envios; falha degrada | todo |
| 6 | Frontend `lib/api.ts` (`enviarAnexo`) + `NovaMensagemForm.tsx` (input PDF condicional ao DOCUMENT) | AC-12 | `NovaMensagemForm.test.tsx` | todo |

## Gates finais (antes do PR)
- Backend: `ruff` + `mypy` + `pytest` (cobertura 90%+ nos módulos novos + regra de envio) + migração up/down + `pip-audit`.
- Frontend: `eslint` + `tsc` + `vitest` + `build` + `npm audit`.
- `/meta-whatsapp` (confere limites de documento/mime da Meta) · `/revisar` · `/seguranca` (upload = superfície §6:
  tipo/tamanho/conteúdo, SSRF/zip-bomba) · `/validar` (AC-1..AC-12) · CI Docker. PR `feat/0025` → `develop`.

## Notas
- Upload **nunca executa/parseia** o PDF — só valida header + repassa à Meta no disparo (mock nos testes).
- `upload_midia` já existe (`services/whatsapp_client.py:88`); o worker injeta `enviar`/upload via parâmetro p/ mock (como hoje).
- Validação real (enviar boleto de verdade) **adiada à Fase 0** (número +55).
