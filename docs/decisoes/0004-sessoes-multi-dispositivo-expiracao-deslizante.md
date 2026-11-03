# ADR 0004 — Sessões multi-dispositivo e expiração deslizante

- **Status:** aceito
- **Data:** 2026-11-01
- **Contexto da feature:** refino de especificações pré-fases 2–4 (sabatina `/clarificar`)
- **Supersede parcialmente:** ADR 0001 (ponto "1 sessão ativa por usuário")

## Contexto
O ADR 0001 e o código da task 5 (`backend/app/api/auth.py:46-48`) revogam todas as sessões ativas no login,
impondo **1 sessão por usuário**. Isso conflita com o BRIEFING §1: o operador usa o PWA em **celular e computador**.
Decisão do responsável (2026-11-01): **1 operador multi-dispositivo agora; multiusuário é evolução futura**.
O schema `sessoes_usuario` já é 1-N (sem unique por usuário), então a mudança é aditiva.

## Decisão
1. **Múltiplas sessões simultâneas por usuário, sem teto.** Remover o revoke-all do login (`auth.py:46-48`).
2. **Logout revoga só a sessão do token atual.** Ação separada **"Sair de todos os dispositivos"** revoga todas as
   sessões do usuário (reaproveita o update atual de `auth.py:69-71`, agora exposto como ação explícita).
3. **Expiração deslizante por inatividade** (~7 dias sem uso) com **teto absoluto** (~30 dias). `expira_em` e
   `ultimo_uso_em` renovam a cada requisição autenticada, com **throttle** (só grava se passou >5 min).
4. **Novas colunas** em `sessoes_usuario`: `ultimo_uso_em` (timestamptz) e `user_agent`/rótulo (text). **Sem IP**
   (minimização LGPD). Migração **aditiva**.
5. **Multiusuário:** não construir agora. `usuario_id` (FK) e `email` (único) já deixam a porta aberta; evolução
   futura aditiva (coluna `papel` + abrir `criar_admin` + checagens de autorização).

## Consequências
- Altera código já commitado na task 5 (login/logout) + migração aditiva nas colunas de sessão. Sugestão: dobrar
  junto da task 6 (TOTP) ou task 7 (rate limit), que já tocam o login, ou uma task 5b dedicada. **Não** há retrabalho
  imediato — fica agendado dentro da Fase 1.
- Janela de sessão mais longa aumenta a superfície se um token vazar; mitigado por 2FA no login, revogação por
  dispositivo ("Sair de todos") e teto absoluto.
- A tela "Dispositivos conectados" fica possível sem migração futura, mas **não** entra na v1 (só o botão
  "Sair de todos os dispositivos"); BRIEFING §10.6 inalterado.
- Os valores exatos (7 dias / 30 dias / throttle 5 min) são padrões configuráveis; ajustáveis sem novo ADR.
