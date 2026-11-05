# Tasks — 0010 Listagem de Modelos (GET /modelos)

Gate: `ruff`+`mypy` 0; `pytest` verde; cobertura ≥90%.

| # | Task | AC | Gate (prova) | Status |
|---|------|----|--------------|--------|
| 1 | `api/modelos.py`: `GET /modelos` (schema `ModeloRead`; filtro `status` via `Literal`; ordena por `nome`; `Depends(usuario_atual)`) | AC-1,2,3 | testes: lista; filtro; 401; status inválido→422; vazio→[] | done |
| 2 | `whatsapp_client.listar_templates()`: GET `/{WABA_ID}/message_templates` (só leitura, paginação `paging.next`, versão via `GRAPH_API_VERSION`) | AC-4 | teste mock httpx: parse + paginação (2 páginas) | done |
| 3 | `api/modelos.py`: `POST /modelos/sincronizar` (upsert por nome+idioma; mapa status Meta→nosso; extrai corpo/header/variáveis; auditoria) | AC-3,4,5 | testes mock `listar_templates`: cria+atualiza; mapa de status; 401 | done |
| 4 | Suíte + cobertura ≥90%; `ruff`/`mypy` 0 | AC-1..5 | `pytest --cov` verde | done |

## Pós-implementação (fora do código)
- [ ] `/revisar` + `/seguranca` + `/validar` + CI antes do PR.
- [ ] Validar a sincronização em **staging** (com a WABA real, só leitura) — toca Cloud API.
- [ ] Spec futura: criar/submeter template UTILITY na Meta.
