# Spec — 0008 Token de sessão em cookie HttpOnly (S2)

Ref.: `product.md`, `design.md` (Opção A), ADR 0012. Tier Arquitetural.

## Critérios de aceite (Given/When/Then)

**AC-1 — Login emite cookie seguro.**
Given credenciais válidas (e-mail+senha+TOTP),
When `POST /auth/login`,
Then a resposta traz `Set-Cookie` `sessao=<token>` com `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`.

**AC-2 — Rota protegida autentica pelo cookie (sem Authorization).**
Given uma sessão válida no cookie `sessao`,
When uma rota protegida é chamada **sem** header `Authorization`,
Then responde 200 (autenticado pelo cookie).

**AC-3 — Transição: Bearer ainda funciona.**
Given uma sessão válida,
When a rota protegida é chamada com `Authorization: Bearer <token>` (sem cookie),
Then responde 200 (compatibilidade durante a migração).

**AC-4 — Logout limpa o cookie.**
Given uma sessão ativa,
When `POST /auth/logout` (ou `/logout-todos`),
Then a resposta expira o cookie `sessao` (`Max-Age=0`) e revoga a sessão no banco.

**AC-5 — Frontend não guarda token em `localStorage`.**
Given o fluxo de login no PWA,
When o usuário autentica,
Then **nada de token** é escrito em `localStorage`; as chamadas vão a `/api/*` (same-origin) com `credentials: "include"`.

**AC-6 — Proxy same-origin.**
Given o frontend,
When chama `/api/<rota>`,
Then o Next faz proxy ao backend preservando método/corpo e **repassando `Set-Cookie`** ao browser.

## Casos de borda
- Cookie **e** Bearer presentes → cookie tem precedência.
- Sessão expirada/revogada via cookie → 401 (frontend redireciona ao login).
- `Secure` não impede o backend de **ler** o cookie em teste (Secure afeta só o envio pelo browser).

## Fora de escopo
- Remover o fallback Bearer (follow-up pós-migração do front).
- CSRF por double-submit (SameSite=Strict cobre o v1).
- Domínio customizado.

## Definition of Ready
- [x] Topologia decidida (Opção A, ADR 0012). AC testáveis (backend: pytest; frontend: tsc/eslint/build + smoke em staging).
- [x] Transição sem lockout (cookie OU Bearer).
