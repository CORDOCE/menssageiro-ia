---
name: tasks-recorrencia
description: Quebra de tarefas (TDD) da spec 0005 — recorrência. Teste vermelho antes do código, uma camada por vez. Mapeia cada tarefa aos AC da spec.
---

# Tasks: Recorrência de agendamentos (spec 0005)

Ordem TDD (§2 método científico): escrever o teste que falha (red) → implementar o mínimo (green) → próximo.
Testes locais com `DATABASE_URL=...@127.0.0.1:5434/mensageiro` (flakiness IPv6 — ver STATE).

## 1. ADR 0009 (decisão irreversível antes do código)
- `docs/decisoes/0009-recorrencia-rrule-dateutil-lazy.md`: dep `python-dateutil`; `recorrencia` = string RRULE;
  criação lazy + dedup por índice parcial. (§4.6)

## 2. Dependência
- `python-dateutil>=2.9` em `backend/pyproject.toml` (`dependencies`); `uv sync`. (§4 — aprovada)

## 3. Serviço `services/recorrencia.py` (AC-2..AC-5)
- **Red:** `tests/test_recorrencia.py` — núcleo RRULE (diária/semanal-BYDAY/mensal-BYMONTHDAY/INTERVAL),
  esgotamento → `None` (UNTIL/COUNT), inválida → exceção, borda fuso/DST (dtstart aware + UNTIL).
- **Green:** `validar_regra(regra)` e `proxima_ocorrencia(regra, dtstart, apos)` reusando o padrão tz de
  `services/janela.py` (`ZoneInfo("America/Sao_Paulo")`, devolve aware/UTC).

## 4. Migração — índice único parcial (AC-1)
- **Red:** teste de que a 2ª inserção com mesmo `(agendamento_pai_id, executar_em)` viola unicidade; e que dois
  `agendamento_pai_id IS NULL` com mesmo `executar_em` **não** conflitam.
- **Green:** nova revisão Alembic (`down_revision='5d75fec0aa05'`), `create_index(..., unique=True,
  postgresql_where=text("agendamento_pai_id IS NOT NULL"))`; `downgrade` com `drop_index`. (/migracao)

## 5. Worker cria a próxima ocorrência (AC-6..AC-10)
- **Red:** `tests/test_worker_disparo.py` — mãe com `recorrencia` dispara e cria 1 filha (AC-6); processar 2×
  não duplica (AC-7); filha encadeia na raiz (AC-8); série esgotada não cria (AC-9); avulso não cria (AC-10).
- **Green:** em `_processar_agendamento`, antes/junto do `update(status='enviado')` (mesmo commit): se
  `ag.recorrencia`, `raiz = ag.agendamento_pai_id or ag.id`, `dtstart` = `executar_em` da raiz, `proxima =
  proxima_ocorrencia(...)`; se não-`None`, `pg_insert(Agendamento)...on_conflict_do_nothing` no índice parcial.

## 6. Schema + API (AC-11..AC-13)
- **Red:** `tests/test_agendamentos_api.py` — criar com `recorrencia` válida → 201 raiz (AC-11); inválida → 422
  (AC-12); `cancelar-serie` cancela só futuras pendentes, enviadas intactas (AC-13).
- **Green:** `recorrencia: str | None` em `AgendamentoCriar`/`AgendamentoRead`; `criar` chama `validar_regra`
  (exceção → 422); novo `POST /{id}/cancelar-serie` (raiz = `agendamento_pai_id or id`; update das futuras
  pendentes; auditoria §5.8).

## 7. Gates e PR (DoD §9)
- Suíte afetada verde → `/revisar` → `/seguranca` → `/validar` + CI Docker local (§4.4).
- Migração reversível (`upgrade`→`downgrade -1`→`upgrade`); cobertura ≥90% no serviço e no trecho do worker.
- Atualizar BRIEFING (§9/§10.3 se preciso), `STATE.md` (/handoff); PR p/ `develop`. Sem achado P0/P1.
