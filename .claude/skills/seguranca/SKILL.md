---
name: seguranca
description: Security review do diff ANTES da PR — caca injecao (SQL/cmd/XSS), authz/authn quebrada, segredo no codigo, input nao-validado, dado sensivel em log, SSRF/path traversal, dependencia/deserializacao insegura. Veredito bloqueante: vulnerabilidade exploravel trava o PR. Foca no que MUDOU e prova o vetor. Roda em par com /revisar. Acione com /seguranca.
---

# Skill: Seguranca (security review)

Olha o **diff** com olhar de atacante, antes da PR. Complementa o hook `guard-secrets` (que ja barra
segredo no commit) — aqui o foco e **vulnerabilidade de logica/design** que nenhuma trava deterministica pega.
Nao e auditoria do repo todo: revise **o que mudou** e a superficie que isso abre.

## Pegue o diff
`git diff` (nao-commitado) ou `git diff <base>...HEAD`. Sem diff -> pergunte o que revisar.

## Checklist (priorize o que o diff toca)
- **Injecao**: SQL/NoSQL por concatenacao (faltou parametrizar?), command injection (`exec`/`spawn` com input),
  XSS (HTML/atributo sem escape, `dangerouslySetInnerHTML`, `v-html`), template injection, LDAP/regex-DoS.
- **AuthN/AuthZ**: endpoint/acao novo **sem checagem de permissao**? IDOR (acessa recurso de outro usuario por id?)
  Checa dono do recurso? Boundary de tenant respeitado? Faltou rate-limit em rota sensivel (login, OTP)?
- **Segredo & dado sensivel**: credencial/chave hardcoded (mesmo que o hook tambem pegue), segredo ou PII
  **em log**, token em URL/query, `.env` referenciado errado, secret default em codigo.
- **Validacao de input**: entrada externa (body/query/header/arquivo/webhook) validada e com tipo/limite?
  Mass-assignment (bind do request inteiro no model)? Upload sem checar tipo/tamanho?
- **SSRF / path traversal**: URL ou caminho derivado de input sem allowlist/normalizacao (`../`, `file://`, IP interno).
- **Cripto & sessao**: hash de senha fraco (md5/sha1/sem salt — use bcrypt/argon2), `Math.random` pra token,
  cookie sem `HttpOnly`/`Secure`/`SameSite`, JWT sem verificar assinatura/exp, comparacao de segredo nao-constante.
- **Deps & config**: dependencia nova conhecida-vulneravel, `eval`/deserializacao insegura de dado nao-confiavel,
  CORS `*` com credenciais, debug/stacktrace exposto, TLS desabilitado (`rejectUnauthorized:false`).

## Como conduzir
- Para cada achado, **mostre o vetor**: como um atacante chega ate ali e o que consegue. Sem vetor plausivel,
  rebaixe pra "endurecimento", nao "vulnerabilidade".
- **Severidade**: **CRITICO** (explora remoto / vaza dado / contorna auth) · **ALTO** (explora com pre-condicao)
  · **MEDIO** (endurecimento / defesa em profundidade). Prefira poucos achados reais a muitos teoricos.
- Prove no codigo (siga o fluxo do input ate o sink). Nao confirmou? -> "a verificar".

## Saida
Por severidade, cada item com **arquivo:linha + vetor + correcao**:

```
CRITICO  api/user.ts:31  — query monta SQL com `req.params.id` por string -> SQLi. Parametrizar/usar ORM.
ALTO     ...
MEDIO    ...
```

Veredito: `SEM VULNERABILIDADE BLOQUEANTE` **ou** `BLOQUEADO` + lista. Qualquer CRITICO/ALTO **trava a PR**
ate corrigir (ou virar decisao consciente registrada). Vazou segredo de verdade? **ROTACIONE a credencial**,
nao basta remover do diff. Em seguida rode **`/validar`** pra fechar o DoD.
