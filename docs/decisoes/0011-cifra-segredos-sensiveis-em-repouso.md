# ADR 0011 — Cifra de segredos sensíveis em repouso (TOTP)

Status: aceito · Data: 2026-11-05 · Contexto: spec 0007 (dívida S1)

## Contexto
`usuario.totp_secret` (o segredo do 2FA) era gravado em texto puro. Comprometer o banco permitia
forjar o segundo fator. Cifra em repouso é uma decisão difícil de reverter (dados cifrados + gestão
de chave), por isso o ADR.

## Decisão
1. **Cifra na aplicação** com `cryptography` (**Fernet**: AES-128-CBC + HMAC-SHA256). O banco guarda o
   token Fernet; a chave **nunca** entra no banco nem no SQL.
2. **Chave em `TOTP_ENC_KEY`** (variável de ambiente), formato Fernet (base64 url-safe, 32 bytes). Vive só
   na Railway (staging e produção), com o rigor de segredo de produção (§6). Nunca em código/log/PR.
3. **Rotação via `MultiFernet`**: `TOTP_ENC_KEY` aceita lista separada por vírgula; a **primeira** cifra,
   qualquer uma decifra. Rotacionar = pôr a nova chave na frente, re-cifrar, remover a velha depois — sem migração.
4. **Dependência nova `cryptography`** aprovada por Jefferson em 2026-11-05 (§4): biblioteca padrão de
   fato para cripto em Python, mantida (PyCA), licença Apache-2.0/BSD; versão fixada; coberta por `pip-audit`.
5. **Migração de dados** cifra o segredo existente no `upgrade` e decifra no `downgrade` (coluna alargada p/ `String(255)`).
6. **Tolerância de corte** (histórico): `decifrar_segredo` aceitava, na janela de migração, segredo legado
   em claro. **Removida em 2026-11-05** (follow-up) após prod e staging estarem cifrados → agora **estrito**
   (valor não-Fernet levanta `InvalidToken`).

## Alternativas rejeitadas
- **pgcrypto**: a chave trafegaria no SQL (risco de log). Postura inferior.
- **KMS/HSM externo**: overkill para 1 operador; reversível no futuro se o escopo crescer.

## Consequências
- Perder `TOTP_ENC_KEY` inutiliza o 2FA cifrado → recuperação por reset (`criar_admin` apaga+recria).
- Qualquer novo segredo sensível em repouso deve reusar `cifrar_segredo`/`decifrar_segredo`.
- Follow-up **concluído** (2026-11-05): tolerância de claro removida; `decifrar_segredo` é estrito.
