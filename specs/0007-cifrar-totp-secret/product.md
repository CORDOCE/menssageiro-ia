# Produto — 0007 Cifrar `totp_secret` em repouso

## Problema
O segredo TOTP do 2FA é gravado em **texto puro** em `usuario.totp_secret`. Quem obtiver acesso de
leitura ao banco (dump, backup vazado, acesso indevido, log) consegue **gerar os códigos 2FA** do
operador e derrotar o segundo fator. É a dívida de segurança **S1** do `docs/divida-tecnica.md`.

## Para quem
Operador(es) do Mensageiro — hoje 1 admin (ADR 0001/0004). Protege o fator de autenticação que
guarda todo o painel (envios, contatos, IA).

## Métrica de sucesso
- Nenhum `totp_secret` em claro no banco (produção e staging).
- Login 2FA continua funcionando sem regressão.
- Comprometer só o banco (sem a chave) **não** permite forjar o TOTP.

## Goals
- Cifrar em repouso o `totp_secret` com chave fora do banco.
- Migrar o segredo existente sem lockout do operador.
- Deixar o caminho de **rotação de chave** documentado.

## Non-goals
- Cifrar outros campos (telefone etc.) — fora de escopo (spec futura se necessário).
- KMS externo / HSM — overkill para 1 operador agora; decisão reversível.
- Rotacionar a chave de fato agora (só habilitar o mecanismo).
