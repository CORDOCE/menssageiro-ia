# ADR 0003 — Python 3.14 e `uv` como toolchain do backend

- **Status:** aceito
- **Data:** 2026-10-30
- **Decidido por:** Jefferson (responsável)
- **Contexto da feature:** `specs/0001-esqueleto-fase-1/`

## Contexto
O ambiente de desenvolvimento tem Python 3.14.6 (via pyenv); não há 3.12 instalado. O BRIEFING §7 e o
CLAUDE.md §8 originalmente fixavam **3.12**. O responsável pediu usar 3.14 se não houvesse problema. Toolchain
Python molda todos os gates (ruff/mypy/pytest/alembic) e o runtime de produção — decisão difícil de reverter.

## Verificação (sessão 2026-10-30)
Experimento isolado com `uv venv --python 3.14` + `uv pip install` da stack-alvo:
- Instalação limpa, com wheels `cp314` pré-compiladas: `pydantic-core 2.50.2`, `bcrypt 5.0.0`, `psycopg 3.3.6`,
  `fastapi 0.162.0`, `sqlalchemy 2.1.6`, `alembic 1.20.1`, `httpx 0.28.1`, `pyotp 2.10.0`, `uvicorn 0.54.0`,
  `pytest 9.2.0`, `ruff 0.17.3`, `mypy`. Nenhuma compilação a partir do fonte. [verificado]
- Smoke test na 3.14.6: import de todos os módulos, modelo Pydantic, `bcrypt.hashpw` e TOTP de 6 dígitos — OK. [verificado]
- Projeto antigo reaproveitado tinha alvo 3.11.9 (`runtime.txt`); migrar para 3.14 é salto para frente, baixo risco. [verificado]

## Decisão
1. **Alvo Python 3.14** no backend (`requires-python = ">=3.14"` no `pyproject.toml`, `.python-version` = 3.14.x).
2. **`uv`** (0.12.x, já instalado) para provisionar o interpretador e gerenciar venv/dependências — isolado do pyenv global.
3. Atualizar BRIEFING §7 e CLAUDE.md §8 para 3.14 (feito, para não criar nova inconsistência doc).

## Consequências e risco residual
- **Railway (Railpack):** confirmar no build manual do deploy (RAILWAY §4) que a 3.14 é resolvida pelo builder.
  Se não estiver disponível, fixar a maior versão suportada em `.python-version` (troca de 1 linha). [não verificado]
- Versões exatas das libs serão fixadas no lockfile do `uv` (`uv.lock`), versionado.
- Reversão (voltar para 3.12) é possível, mas exigiria novo ADR e ajuste dos docs.
