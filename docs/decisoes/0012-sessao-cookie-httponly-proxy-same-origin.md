# ADR 0012 — Sessão em cookie HttpOnly via proxy same-origin

Status: aceito · Data: 2026-11-05 · Estende ADR 0001/0004 · Spec 0008 (dívida S2)

## Contexto
O token de sessão vivia em `localStorage` (exposto a XSS). Front e back estão em **domínios diferentes**
sob `up.railway.app`, que está na **Public Suffix List** → o browser os trata como **sites distintos**,
e um cookie `SameSite=Lax/Strict` do backend não é enviado nas chamadas do frontend (cross-site).

## Decisão
1. **Topologia: proxy same-origin no Next** (Opção A, escolhida por Jefferson). O frontend expõe `/api/*`
   e faz proxy ao backend (rewrites). O browser só fala com a origem do frontend → cookie **first-party**.
2. **Cookie de sessão** `sessao`: `HttpOnly; Secure; SameSite=Strict; Path=/`, `Max-Age` = teto absoluto da
   sessão (`session_max_dias`). O token **não** é mais lido/guardado por JavaScript.
3. **CSRF**: `SameSite=Strict` já impede o envio do cookie em requisições cross-site → mitiga CSRF clássico.
   Double-submit/headers extras ficam como endurecimento futuro.
4. **Transição sem lockout**: o backend aceitou o token por **cookie OU `Authorization: Bearer`** durante a
   migração do frontend. **Fallback Bearer removido em 2026-11-05** (frontend já migrado) → auth **só por cookie**.
5. **CORS**: com proxy same-origin o browser não faz cross-origin para a API → CORS deixa de ser o caminho
   de auth (mantido `FRONTEND_URL` para eventuais acessos diretos).

## Alternativas rejeitadas
- **Domínio customizado (mesmo site)**: válido, mas exige infra de domínio agora.
- **`SameSite=None; Secure` cross-site**: cookie de 3ª parte, bloqueado por padrão em Safari/Firefox → frágil.
- **Manter localStorage + CSP**: não resolve a dívida.

## Consequências
- Validação do fluxo cookie (proxy + Set-Cookie + SameSite) é **em staging** (toca auth; sem test runner no front).
- Latência: +1 hop (browser→Next→backend) nas chamadas de API.
- Follow-up: remover o fallback Bearer após o frontend migrar.
