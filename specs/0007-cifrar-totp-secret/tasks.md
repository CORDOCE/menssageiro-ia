# Tasks — 0007 Cifrar `totp_secret` em repouso

Gate da stack: `ruff` + `mypy` 0; `pytest` (afetados) verde; ciclo Alembic ok. Suíte completa + `pip-audit` antes do PR.
Cobertura ≥90% nas regras tocadas (auth/2FA — §8).

| # | Task | AC | Dep | Gate (prova) | Status |
|---|------|----|-----|--------------|--------|
| 1 | ADR 0011 em `docs/decisoes/` + artefatos da spec | — | — | arquivos presentes e linkados | done |
| 2 | Dep `cryptography` (versão fixada) em `backend/pyproject.toml`; `uv lock` | — | 1 | `pip-audit` 0; import ok | todo |
| 3 | `core/config.py`: `totp_enc_key: str \| None` | AC-5 | 1 | `mypy` 0; teste de settings | todo |
| 4 | `core/security.py`: `cifrar_segredo`/`decifrar_segredo` via `MultiFernet` **construído lazy** (chave lida no uso, não no import); chave ausente no uso → exceção; tolerância legado c/ WARN | AC-1, AC-5, AC-6 | 2,3 | testes (c/ chave de teste por fixture): round-trip; chave ausente levanta; rotação 2 chaves; legado em claro c/ WARN | todo |
| 5 | `models/usuario.py`: `totp_secret` → `String(255)` | AC-4 | 1 | `mypy` 0 | todo |
| 6 | `/migracao` aditiva: alarga coluna + cifra existentes (upgrade) / decifra + estreita (downgrade); **chave exigida só quando há linhas** — tabela vazia = no-op sem chave | AC-4, AC-7 | 4,5 | ciclo `alembic upgrade head && downgrade base` **em banco vazio sem `TOTP_ENC_KEY`** → 0 (cenário CI); com chave + linha semeada → cifrado após upgrade, claro após downgrade | todo |
| 7 | `app/criar_admin.py`: cifrar antes do INSERT | AC-1 | 4 | teste: segredo gravado é token Fernet, decifrável | todo |
| 8 | `api/auth.py` `_totp_confere`: decifrar antes de `pyotp.verify` | AC-2, AC-3 | 4 | testes: login 2FA ok (cifrado); código errado → 401 | todo |
| 9 | Garantir sem PII/segredo/chave em log e Sentry (§6) nos caminhos tocados | AC-1 | 7,8 | teste/inspeção: log sem claro/chave | todo |
| 10 | Suíte completa + cobertura ≥90% das regras de auth/2FA; `ruff`/`mypy` 0 | AC-1..AC-6 | 1–9 | `pytest --cov` verde | todo |

## Pós-implementação (fora do código)
- [ ] `TOTP_ENC_KEY` gerada (`Fernet.generate_key()`) e setada na Railway **staging e produção** (infra, aprovação §4).
- [ ] Deploy em staging → **validar login 2FA real** (toca auth) + conferir `totp_secret` cifrado no banco.
- [ ] `/revisar` + `/seguranca` + `/validar` sem P0/P1 antes do PR.
- [ ] Follow-up registrado: remover tolerância de claro (tornar `decifrar_segredo` estrito) após produção cifrada.
