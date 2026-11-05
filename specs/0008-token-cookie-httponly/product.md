# Produto — 0008 Token de sessão em cookie HttpOnly (dívida S2)

## Problema
O token de sessão é guardado em `localStorage` (`frontend/lib/auth.ts`), **acessível a JavaScript** →
um XSS no painel exfiltra o token e sequestra a sessão do operador. Dívida de segurança **S2** do
`docs/divida-tecnica.md`.

## Para quem
Operador(es) do Mensageiro (1 admin hoje; ADR 0001/0004). Protege a sessão que dá acesso a envios,
contatos e IA.

## Métrica de sucesso
- Token de sessão **inacessível a JavaScript** (cookie `HttpOnly`); nada sensível em `localStorage`.
- Login/logout/rota protegida continuam funcionando, **sem regressão** (validado em staging).
- Sem abrir vetor de CSRF.

## Goals
- Mover o token para cookie `HttpOnly; Secure; SameSite` (ou equivalente same-origin).
- Proteção CSRF adequada à topologia escolhida.

## Non-goals
- Multiusuário/papéis (segue ADR 0004 — evolução futura).
- Trocar o mecanismo de sessão (segue token opaco no banco, ADR 0001); muda só **onde** o token vive no cliente.
- OAuth/SSO.
