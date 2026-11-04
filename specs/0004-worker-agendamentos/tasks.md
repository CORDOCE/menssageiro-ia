---
name: tasks-worker-agendamentos
description: Quebra de tasks da Fase 4 — núcleo do disparo (0004-worker-agendamentos). Cada task mapeia 1+ AC e aponta o gate (comando de teste) que a prova. Ordem TDD (teste que falha primeiro).
---

# Tasks: Worker de disparo + agendamentos — núcleo (Fase 4)

**Pré-condições (não são tasks desta feature):**
- Fases 2–3 mergeadas em `develop`: fornecem `Contato`, `Modelo`, `Envio`, `Saude`, `services/whatsapp_client.enviar_template`
  (aceita `client` injetável — usado no mock), `core/audit.registrar_auditoria`, `core/telefone.mascarar_telefone`,
  `core/auth_deps.usuario_atual`, o loop de heartbeat do worker.
- **Fase 0 (responsável):** credenciais Meta para **validação real** em staging (hoje bloqueada, 131031). **Não
  bloqueia os AC** — todos passam com **mock** de `enviar_template` e PostgreSQL real em container.
- **Regras de envio** = ADR 0005 (já aprovado, §4). Esta feature **implementa**, não cria regra nova.

| # | Task | Cobre AC | Depende de | Gate (comando de teste) | Status |
|---|------|----------|------------|--------------------------|--------|
| 1 | `[P]` **ADR 0008** em `docs/decisoes/` (configuracoes = fonte runtime + `limite_diario`; idempotência reserva-antes-de-enviar **at-most-once**; `janela_envio` JSONB em America/Sao_Paulo) | — | — | arquivo presente e linkado no `design.md` | todo |
| 2 | `models/agendamento.py` (+ `CHECK` xor `contato_id`/`grupo`, FKs, colunas inertes `agendamento_pai_id`/`recorrencia`) + `models/configuracao.py` (linha única) + `schemas/agendamento.py` | AC-1 | pré | `ruff`+`mypy` 0; teste instancia + CHECK xor rejeita ambos/nenhum | todo |
| 3 | Migration Alembic (via **/migracao**): cria `agendamentos` + `configuracoes` (semeada c/ defaults) + **FK** `envios.agendamento_id→agendamentos` (mantém índice único parcial) | AC-1, AC-2 | 2 | `alembic upgrade head && downgrade base` → 0 | todo |
| 4 | `[P]` `core/config.py`: `limite_diario_default` lendo env `LIMITE_DIARIO` (padrão 200) — **só semente** da linha de `configuracoes` | AC-1 | pré | `mypy` 0; teste de settings | todo |
| 5 | `api/agendamentos.py`: `POST` (criar; valida xor; `status=aprovado`; `criado_por`) + `GET` (listar). **Não** chama a Meta (§5.1) | AC-3, AC-4, AC-5 | 2,3 | testes: 201; ambos/nenhum→422; modelo inexistente→404/422; sem auth→401; nenhum mock de envio é chamado | todo |
| 6 | `api/agendamentos.py`: `POST /{id}/cancelar` e `POST /{id}/reenviar` (transições + 409 em status inválido) | AC-6, AC-7 | 5 | testes: cancelar não-terminal→cancelado; terminal→409; reenviar só de `aguardando_decisao`; outro→409 | todo |
| 7 | `[P]` `services/janela.py`: `dentro_da_janela(agora, janela)`, `proximo_inicio(janela, …)`, `inicio_dia_seguinte(janela, …)` (fuso America/Sao_Paulo, `zoneinfo`; sem dep nova) + helper singleton `configuracoes` | AC-12, AC-13 | 2 | testes unitários de borda: 20:00 exato, domingo fora, próximo início, dia seguinte | todo |
| 8 | Worker `worker/disparo.py` — **decisão por agendamento**: `SELECT … FOR UPDATE SKIP LOCKED` vencidos; pausa→nada; fora janela→reagenda; modelo≠aprovado→falhou; limite_diario→adia; senão→enviar | AC-11, AC-12, AC-13, AC-14, AC-22 | 3,7 | integração (PostgreSQL): matriz por agendamento; 2 sessões concorrentes não pegam o mesmo (SKIP LOCKED) | todo |
| 9 | Worker — **expansão de grupo + por contato**: materializa `envios` (reserva `ON CONFLICT DO NOTHING`); checa descadastro/consentimento/limite-por-contato; chama `enviar_template` (mock) → `wamid`/`enviado`; erro definitivo→`falhou`; auditoria mascarada (`correlation_id=agendamento_id`) | AC-8, AC-9, AC-10, AC-15, AC-16, AC-17, AC-20, AC-21 | 8 | integração: matriz por contato; reinício no meio **não duplica** (AC-10); erro definitivo isola 1 contato; auditoria sem PII | todo |
| 10 | Worker — **`aguardando_decisao`**: lê heartbeat anterior; atraso >2h **com** gap→`aguardando_decisao`; **sem** gap→dispara | AC-18, AC-19 | 8 | testes: gap simulado move; sem gap dispara (contraexemplo) | todo |
| 11 | Suíte completa + **cobertura ≥90%** das regras de envio/checagens; `ruff`/`mypy` 0; **nenhum** teste chama a API real da Meta | gate §8 | 1–10 | `pytest --cov` → 0 e cobertura ≥90% nos módulos do worker/regras | todo |

> `[P]` = paralelizável (ADR, config e `services/janela` não dependem entre si). **Sem dependência nova**
> (`zoneinfo`/`datetime` stdlib; `httpx` já existe). Recorrência/anexos ficam fora (specs seguintes).
> CI: reaproveita `.github/workflows/ci.yml` (PostgreSQL em container) — nenhum workflow novo.

## Definition of Done (resumo — detalhe no CLAUDE.md §9)
- [ ] Todo AC verde pelo **gate executável** (não por inspeção); matrizes cobertas linha a linha.
- [ ] Cobertura ≥90% nas regras de envio (relatório anexado ao PR).
- [ ] `/revisar` sem P0/P1 e `/seguranca` sem Crítico/Alto (zero segredo).
- [ ] Migração com `downgrade` funcional (/migracao); sem migração destrutiva.
- [ ] Sem `SPEC_DEVIATION` aberto; logs/auditoria sem PII; `correlation_id` presente.
- [ ] Commit limpo (zero co-autoria de IA, zero segredo); PR com objetivo/risco/plano de teste.
- [ ] Validação real em staging quando a Fase 0 (credenciais) for desbloqueada — registrada como pendência no PR/`STATE.md`.
