# Spec — 0007 Cifrar `totp_secret` em repouso

Ref.: `product.md`, `design.md`, ADR 0011. Tier Arquitetural.

## Critérios de aceite (Given/When/Then)

**AC-1 — Segredo nunca em claro no banco.**
Given um admin criado via `criar_admin`,
When inspeciona-se `usuario.totp_secret` no banco,
Then o valor é um **token Fernet** (≠ o segredo base32 original) e `decifrar_segredo(valor)` recupera o original.

**AC-2 — Login 2FA funciona com segredo cifrado.**
Given um admin cujo `totp_secret` está cifrado,
When ele faz login com e-mail, senha e o código TOTP corrente,
Then o login retorna 200 (sessão emitida).

**AC-3 — Código TOTP errado continua sendo rejeitado.**
Given o mesmo admin,
When o código TOTP está errado (fora da janela ±1),
Then o login retorna 401 genérico (sem revelar qual fator falhou).

**AC-4 — Migração cifra os dados existentes e é reversível.**
Given um banco com `totp_secret` em claro,
When roda `alembic upgrade head`,
Then a coluna passa a guardar ciphertext (decifrável para o claro original) e `alembic downgrade` restaura o claro;
ambos sem erro.

**AC-5 — Chave ausente falha de forma explícita (nunca silenciosa em claro).**
Given `TOTP_ENC_KEY` não configurada,
When o código tenta cifrar ou decifrar um segredo,
Then ocorre erro explícito (exceção clara) — jamais grava/valida o segredo em texto puro.

**AC-6 — Rotação de chave (MultiFernet).**
Given `TOTP_ENC_KEY` com duas chaves `nova,velha` e um segredo cifrado com a **velha**,
When `decifrar_segredo` roda,
Then decifra com sucesso; e um novo `cifrar_segredo` usa a **nova** (primeira).

**AC-7 — Migração em banco vazio sem chave é no-op (cenário do CI).**
Given um banco **sem usuários** e `TOTP_ENC_KEY` **não** configurada,
When roda `alembic upgrade head` e `downgrade base`,
Then completa sem erro e **sem exigir a chave** (a cifra só ocorre quando há linhas).

## Casos de borda
- Valor **legado em claro** na janela de corte → `decifrar_segredo` aceita uma vez com `WARN` (tolerância do design; removida em follow-up).
- Token Fernet corrompido/adulterado (HMAC inválido) → erro (não autentica).
- Segredo vazio/`None` → tratado sem exceção silenciosa (comportamento idêntico ao atual: `_totp_confere` retorna False).
- Nenhum segredo/claro aparece em log ou Sentry (§6).

## Fora de escopo
- Cifrar outros campos (telefone, etc.).
- KMS/HSM externo.
- Executar a rotação de chave de fato (só habilitar o mecanismo).
- Remover a tolerância de claro (follow-up pós-produção-cifrada).

## Definition of Ready
- [x] AC testáveis e não-ambíguos (um teste por AC). Testes que exercitam cifra setam uma **chave de teste** por fixture (sem alterar o `ci.yml`).
- [x] Decisão de abordagem fechada (`/clarificar`: Fernet app-level) e registrada em ADR 0011.
- [x] Non-goals explícitos. Design aprovado (gate de design).
