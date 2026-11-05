# Design — 0008 Token em cookie HttpOnly (dívida S2)

## 🚧 DECISÃO PENDENTE (gate de clarificação) — bloqueia o resto do design
Front e back estão em **domínios diferentes** sob `up.railway.app`, que **está na Public Suffix List**
(entrada de 3 rótulos) — [verificado 2026-11-05, WebSearch/PSL]. Logo o browser trata
`...-frontend-production.up.railway.app` e `...-backend-production.up.railway.app` como **sites distintos**:
- cookie `SameSite=Lax/Strict` do backend **não é enviado** nas chamadas do frontend (cross-site);
- `SameSite=None; Secure` (cookie de 3ª parte) é bloqueado por padrão em Safari/Firefox e cada vez mais no Chrome → **frágil**.

Portanto o cookie HttpOnly só é viável com uma destas topologias (escolha de Jefferson):

| Opção | Como | Trade-off |
|---|---|---|
| **A. Proxy same-origin no Next** (recomendada) | Frontend expõe `/api/*` e faz proxy ao backend (rewrites/route handler). Browser só fala com a origem do front → cookie **first-party** HttpOnly + `SameSite=Strict`, sem CORS credentials, imune a bloqueio de 3ª parte. | Robusto, independe de domínio. Custo: camada de proxy; frontend chama caminhos locais; latência extra de 1 hop. |
| **B. Domínio customizado (mesmo site)** | `app.X.com` + `api.X.com` (mesmo domínio registrável). | Cookie `SameSite` nativo; alinha com go-live. Exige configurar domínio/DNS/SSL na Railway agora. |
| **C. Repensar S2** | Manter token, endurecer XSS por CSP estrita + TTL curto + sanitização. | Ganho parcial; sem mudança de topologia; revisita cookie com domínio próprio. |

**O design abaixo assume a Opção A (recomendada); muda conforme a escolha.**

## Solução (assumindo Opção A)
- **Proxy:** Next faz proxy de `/api/*` → backend (rewrites em `next.config` ou route handler que repassa
  método/corpo/headers e **propaga `Set-Cookie`**). Frontend passa a chamar `/api/...` (mesma origem).
- **Backend:** `POST /auth/login` emite `Set-Cookie` `sessao=<token>; HttpOnly; Secure; SameSite=Strict; Path=/`
  (além de, por transição, ainda aceitar `Authorization: Bearer`). `auth_deps` lê o token do **cookie**
  (fallback no header durante a migração). `logout`/`logout-todos` limpam o cookie.
- **CSRF:** com same-origin + `SameSite=Strict` e sem formulários cross-site, o risco é baixo; ainda assim
  adotar **double-submit token** ou exigir header custom (`X-Requested-With`) nas rotas que mutam — decidir no ADR.
- **Frontend:** remover `salvarToken/lerToken/limparToken` (localStorage) de `lib/auth.ts`; `lib/api.ts` usa
  `credentials: "include"` e caminhos `/api/...`; `GuardaAuth` passa a depender do `GET /api/auth/me` via cookie.
- **CORS:** com proxy same-origin, o browser não faz cross-origin → CORS deixa de ser o caminho; manter
  `FRONTEND_URL` só para casos diretos (se houver).

## Alternativas e riscos
- Opção B elimina o proxy mas custa infra de domínio; Opção C não resolve a dívida de fato.
- **Risco de regressão de login** (auth) → validação obrigatória em staging antes de prod.
- Transição: aceitar Bearer **e** cookie por uma release evita lockout; remover o Bearer em follow-up.

## Decisão irreversível → ADR
Estende ADR 0001/0004 (onde o token vive no cliente + topologia + CSRF) → **ADR 0012** (a escrever após a decisão A/B/C).
