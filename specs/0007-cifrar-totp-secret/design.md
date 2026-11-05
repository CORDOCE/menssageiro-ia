# Design — 0007 Cifrar `totp_secret` em repouso

## Solução
Cifra simétrica **na aplicação** com `cryptography` (Fernet = AES-128-CBC + HMAC-SHA256,
chave url-safe base64 de 32 bytes). O banco guarda só o **token Fernet**; a chave vive em
`TOTP_ENC_KEY` (variável de ambiente), **nunca** no banco nem no SQL.

- **Config:** `totp_enc_key: str | None` em `core/config.py`.
- **Helpers** (`core/security.py`): `cifrar_segredo(claro: str) -> str` e `decifrar_segredo(cifra: str) -> str`,
  usando `MultiFernet` sobre `TOTP_ENC_KEY` (lista separada por vírgula; **primeira** chave cifra, qualquer
  uma decifra) — isso habilita **rotação** sem migração de dados: adiciona-se a nova chave no início,
  re-cifra sob demanda, remove-se a velha depois.
- **Escrita:** `app/criar_admin.py` cifra antes do `INSERT`.
- **Leitura:** `_totp_confere` (`api/auth.py`) decifra antes de `pyotp.TOTP(...).verify`.
- **Coluna:** o token Fernet de um segredo base32 (~32 chars) fica em ~140 chars → **alargar**
  `totp_secret` de `String(64)` para `String(255)` (migração).

## Migração de dados (sem lockout)
- **upgrade:** (1) alarga a coluna; (2) **se houver linhas**, lê cada `totp_secret` em claro e grava o token
  cifrado — a chave `TOTP_ENC_KEY` só é exigida **quando há linha a cifrar** (**falha alto** nesse caso se ausente).
  **Tabela vazia → no-op, sem exigir chave** (é o cenário do CI: ciclo de migração em banco vazio sem a var).
- **downgrade:** (1) se houver linhas, decifra cada valor de volta ao claro (chave exigida só com linhas);
  (2) estreita a coluna para `String(64)`.
- **Ordem de deploy:** na Railway a migração roda **no deploy do backend, antes de servir**
  (ver [[railway-deploy-por-caminho-observado]]) → quando o novo código atende, o dado já está cifrado.

## Compatibilidade na janela de corte
`decifrar_segredo` tolera **uma vez** um valor legado em claro: se não for token Fernet válido e
tiver cara de segredo base32 TOTP, loga `WARN` e retorna como está. Evita lockout se a ordem
deploy↔migração vacilar. **Removida em follow-up** depois que produção estiver cifrada (vira estrito).

## Alternativas consideradas
- **pgcrypto (SQL-side):** sem dep nova, mas a **chave trafega no SQL** → risco de vazar em log de
  query/erro do Postgres. Rejeitada por postura de segurança inferior (decisão de Jefferson, 2026-11-05).
- **Coluna separada + flag "cifrado":** mais complexo; `MultiFernet` já cobre rotação sem isso.
- **KMS/HSM externo:** overkill p/ 1 operador; reversível no futuro.

## Riscos
- **Perda de `TOTP_ENC_KEY`** → ninguém decifra o 2FA. Mitigação: guardar a chave com o mesmo rigor de
  um segredo de produção; recuperação = reset do 2FA via `criar_admin` (apaga+recria).
- **Dep nova** (`cryptography`): reputada, amplamente usada, licença Apache-2.0/BSD; versão fixada; `pip-audit` no CI.
- **Logs:** garantir que nem o claro nem a chave apareçam em log/Sentry (§6).

## Decisão irreversível → ADR
Esquema de cifra + gestão/rotação de chave → **ADR 0011**.
