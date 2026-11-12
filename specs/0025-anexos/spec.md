# Spec — 0025 Anexos (PDF/boleto no cabeçalho DOCUMENT) — dívida A4

> Tier **Arquitetural** (regra de envio §5 + migração + §4 + Cloud API + superfície de upload §6).
> **ADR 0016.** Ver `product.md`/`design.md`. Decisões aprovadas: **mock** (validação real = Fase 0),
> armazenamento **bytea** no banco.

## Escopo (v1)
Anexar um **PDF** a um agendamento cujo modelo tem cabeçalho **DOCUMENT**; o worker sobe à Meta no disparo
e inclui o documento no envio. **Pix** = variável de texto (sem código novo). Só PDF; só anexo individual
por agendamento.

## Critérios de aceite (Given/When/Then)
- **AC-1 (upload authz)** — `POST /anexos` sem sessão → **401**.
- **AC-2 (upload PDF ok)** — `POST /anexos` com um PDF válido (mime `application/pdf`, inicia com `%PDF-`,
  ≤ cap) → **201** `{id, nome_arquivo, tamanho}`; os bytes ficam salvos.
- **AC-3 (rejeita não-PDF)** — arquivo com mime ≠ `application/pdf` **ou** sem o magic `%PDF-` → **422**.
- **AC-4 (rejeita grande)** — arquivo acima de `ANEXO_MAX_BYTES` → **422** (sem guardar).
- **AC-5 (vínculo DOCUMENT)** — `POST /agendamentos` com modelo `cabecalho_tipo=DOCUMENT` + `anexo_id` válido →
  **201**, agendamento com `anexo_id`.
- **AC-6 (DOCUMENT exige anexo)** — modelo `DOCUMENT` **sem** `anexo_id` → **422**.
- **AC-7 (não-DOCUMENT recusa anexo)** — modelo sem cabeçalho DOCUMENT **com** `anexo_id` → **422**.
- **AC-8 (anexo inexistente)** — `anexo_id` que não existe → **422**.
- **AC-9 (disparo inclui DOCUMENT)** — disparo de agendamento com anexo → `upload_midia` é chamado e o envio
  usa `componentes = [componente_documento(media_id), body]`.
- **AC-10 (grupo reusa media_id)** — disparo de grupo (N contatos) com anexo → `upload_midia` chamado **1×**;
  o mesmo `media_id` nos N envios.
- **AC-11 (falha no upload)** — `upload_midia` lança no disparo → o(s) envio(s) vão a `falhou` com alerta,
  **sem derrubar o ciclo** (molde dos demais erros de envio).
- **AC-12 (UI Nova mensagem)** — ao escolher um modelo com cabeçalho DOCUMENT, a Nova mensagem mostra um input
  de **PDF**; sobe via `POST /anexos` e envia o `anexo_id` ao criar. Sem DOCUMENT → sem input de anexo.

## Tabela-verdade do vínculo (AC-5..AC-8) — cada linha vira teste
| modelo DOCUMENT? | anexo_id | resultado |
|---|---|---|
| sim | válido | 201 (com anexo) |
| sim | ausente | 422 |
| não | presente | 422 |
| sim/não | inexistente | 422 |

## Fora de escopo (vinculante)
- Imagem/vídeo/áudio; múltiplos anexos; biblioteca de anexos; preview/edição do PDF.
- **Validação de envio real** com anexo (Fase 0 / +55). Retenção/limpeza automática dos bytes (follow-up).

## Arquivos (previsto)
- Backend: `models/anexo.py` + `agendamentos.anexo_id` + migração; `schemas/anexo.py`; `api/anexos.py`
  (+`main.py`); `api/agendamentos.py`+`schemas/agendamento.py` (regra de coerência); `worker/disparo.py`
  (upload no disparo + componente DOCUMENT); `core/config.py` (`anexo_max_bytes`). Testes: `test_anexos_api.py`,
  `test_agendamentos_api.py` (+coerência), `test_worker_disparo.py` (+anexo).
- Frontend: `NovaMensagemForm.tsx` (input de PDF condicional) + `lib/api.ts` (`enviarAnexo`) + teste.
