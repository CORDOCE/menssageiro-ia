# STATE — Mensageiro

> Memória volátil do trabalho. Histórico vive no git/ADR. Atualize ao pausar (`/handoff`).

_Atualizado: 2026-11-01_

## Em andamento
- Sessão de **refino de specs (pré-fases 2–4)** + **abertura da Fase 2**. Tudo em doc/spec — **zero código novo**.
- **Specs ativas:** `specs/0001-esqueleto-fase-1/` (Fase 1, com task 5b nova) e `specs/0002-contatos-importacao/` (Fase 2).

## Próximo passo
1. **Revisar e mergear os PRs na ordem `#5 → #6 → #7`** (aguarda Jefferson). A ordem resolve as referências cruzadas aos ADR 0004/0005/0006.
2. Implementar **task 5b + task 6** (sessão multi-dispositivo + 2FA TOTP) — altera `auth.py`/`auth_deps.py`, migration aditiva (`ultimo_uso_em`, `user_agent`) via `/migracao`.
3. **Fase 2** (só após task 5 em `develop`): tasks 1→10 (model/migration/`telefone`/CRUD/import); libs `phonenumbers`+`openpyxl` já aprovadas (ADR 0006).

## Decisões da sessão (duráveis → ADR)
- **ADR 0004** — sessão multi-dispositivo + expiração deslizante (supera o ponto "1 sessão" do ADR 0001).
- **ADR 0005** — regras de envio: expansão de grupo no disparo, `UNIQUE(envios.agendamento_id, contato_id)`, consentimento como invariante (CLAUDE §5.9), estado `aguardando_decisao`.
- **ADR 0006** — E.164 via `phonenumbers` + XLSX via `openpyxl` (dependências **aprovadas**).
- CLAUDE §5.2/§5.9 e §6 (SAST semgrep/codeql no CI + revisão de superfície de ataque). BRIEFING §2/§9/§10.3 refinados; §7 requisito **multiplataforma** (PWA iOS/Android/Win/macOS/Linux) + caveat Web Push iOS (fallback e-mail na Fase 5).
- Fase 2 (0002): tier arquitetural, 20 AC + matriz de decisão, 5 suposições confirmadas.

## Bloqueios/pendências
- Nada implementado nesta sessão (só spec/docs). Implementação da Fase 2 **depende da task 5 em `develop`**.
- STATE.md foi atualizado na branch `docs/refino-specs-fases-2-4` (PR #5, mergeia primeiro). No merge de #6, se houver conflito de STATE.md, **vale esta versão**.

## Estado do git
- Branch atual: `docs/refino-specs-fases-2-4`. `develop` = `d7bee54` (PRs #1–#4 mergeados).
- **3 PRs abertos** contra `develop` em `CORDOCE/menssageiro-ia` (tudo pushado):
  - **#5** `docs/refino-specs-fases-2-4` (`8a61a7b`,`5057a4d`) — doc-only; `/revisar` PRONTO PRA PR.
  - **#6** `feat/0001-task5-usuario-auth` (`8e381b2` código task 5 + `fa8ba2f` spec task 5b) — gates já verdes.
  - **#7** `feat/0002-contatos-importacao` (`96874cf`,`08605bb`) — doc-only; empilhado sobre o refino; mergeia por último.
