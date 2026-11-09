# Tasks — 0015 Hardening da API de agendamentos (R1)

TDD: teste que falha primeiro, depois implementação. Gate: `pytest backend/tests/test_agendamentos_api.py`.

- [ ] **T1** `tests/test_agendamentos_api.py`: AC-1 (`contato_id` inexistente → 404, nada criado),
      AC-2 (contato válido → 201), AC-3 (>50 itens → 422; item >1000 chars → 422),
      AC-4 (50 itens/1000 chars e lista vazia → 201), borda `grupo` sem contato. — AC-1..AC-4
- [ ] **T2** `api/agendamentos.py` `criar()`: após validar `modelo_id`, se `payload.contato_id` não for
      nulo e `db.get(Contato, payload.contato_id) is None` → `HTTPException(404, "Contato não encontrado")`.
      Importar `Contato`. — AC-1, AC-2
- [ ] **T3** `schemas/agendamento.py` `AgendamentoCriar.variaveis`: cap defensivo — `Field(max_length=50)`
      (nº de itens) + item `Annotated[str, StringConstraints(max_length=1000)]`. — AC-3, AC-4

## Gate final (antes do PR)
- [ ] `/revisar` + `/seguranca` sem P0/P1 · `/validar` AC-1..AC-4 · CI completo via Docker.
- [ ] Cobertura ≥90% nas linhas novas (§8). Sem migração.
