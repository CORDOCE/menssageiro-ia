# Tasks — 0010 Listagem de Modelos (GET /modelos)

Gate: `ruff`+`mypy` 0; `pytest` verde; cobertura ≥90%.

| # | Task | AC | Gate (prova) | Status |
|---|------|----|--------------|--------|
| 1 | `api/modelos.py`: `GET /modelos` (schema `ModeloRead`; filtro opcional `status` validado por Enum/Literal; ordena por `nome`; `Depends(usuario_atual)`) | AC-1,2,3 | testes: lista; filtro; 401 sem sessão; status inválido→422; vazio→[] | todo |
| 2 | Suíte + cobertura ≥90%; `ruff`/`mypy` 0 | AC-1..3 | `pytest --cov` verde | todo |

## Pendente (fora do código desta spec)
- [ ] **Decisão de escopo do povoamento** (sync Meta vs criação) → parte/spec seguinte, com `/meta-whatsapp`.
- [ ] `/revisar` + `/seguranca` + `/validar` + CI antes do PR.
