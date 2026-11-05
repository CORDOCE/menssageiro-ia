# Tasks — 0008 Token em cookie HttpOnly (S2, Opção A)

Gate backend: `ruff`+`mypy` 0; `pytest` verde; cobertura ≥90%. Frontend: `eslint`+`tsc`+`build`. Fluxo cookie: **staging**.

| # | Task | AC | Gate (prova) | Status |
|---|------|----|--------------|--------|
| 1 | ADR 0012 + artefatos da spec | — | arquivos presentes | done |
| 2 | `core/auth_deps.py`: ler token do cookie `sessao` **ou** `Authorization: Bearer` (cookie precede) | AC-2,3 | testes: /me via cookie; via Bearer; cookie precede | done |
| 3 | `api/auth.py`: `login` seta cookie seguro; `logout`/`logout-todos` expiram o cookie | AC-1,4 | testes: Set-Cookie c/ flags; logout Max-Age=0 | done |
| 4 | Frontend `next.config`: rewrites `/api/:path*` → backend (`BACKEND_URL`), repassa Set-Cookie | AC-6 | build ok; validação do proxy em staging | done |
| 5 | Frontend `lib/api.ts`: base same-origin `/api`, `credentials:"include"`, sem `Authorization`; `lib/auth.ts`: remover `localStorage`; `GuardaAuth` via `/api/auth/me` | AC-5 | `tsc`+`eslint`+`build` 0; smoke staging | done |
| 6 | Suíte backend + cobertura ≥90%; `ruff`/`mypy` 0 | AC-1..4 | `pytest --cov` verde | done |

## Pós-implementação (fora do código)
- [ ] Setar `BACKEND_URL` no serviço de frontend (Railway, staging e prod) apontando ao backend.
- [ ] **Validar em staging**: login real (cookie setado, sem token no localStorage), navegação, logout. (toca auth, §9)
- [ ] `/revisar` + `/seguranca` + `/validar` + CI antes do PR.
- [ ] Follow-up: remover o fallback `Authorization: Bearer`.
