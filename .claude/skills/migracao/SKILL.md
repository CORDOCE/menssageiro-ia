---
name: migracao
description: Cria e valida mudanças de esquema do PostgreSQL com Alembic de forma segura — upgrade e downgrade testados, estratégia expandir/contrair para mudanças com dados, sem travar tabelas em produção. Migração destrutiva exige aprovação explícita. Acione com /migracao.
---

# Skill: Migração (Alembic)

## Processo
1. Altere o modelo SQLAlchemy e gere: `alembic revision --autogenerate -m "<descrição>"`.
2. **Revise o arquivo gerado linha a linha** (autogenerate erra: renomes viram drop+add, tipos e índices).
3. Mudanças com dados existentes seguem **expandir → migrar → contrair**, em PRs separados:
   adicionar coluna nullable → preencher → passar código a usar → tornar NOT NULL → remover o antigo.
4. Índices em tabelas grandes: `CREATE INDEX CONCURRENTLY` (fora de transação).
5. Teste em banco limpo: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`.
6. Teste com dados: rode a migração sobre uma cópia/fixture representativa e verifique contagens.

## Bloqueios
- Drop/rename de coluna ou tabela, ou delete de dados → **parar e pedir aprovação**, com plano de backup e rollback.
- Nunca editar uma migração já aplicada em staging/produção; crie outra.
- `create_all()` não é usado fora de testes.

## Saída no PR
Descrição da mudança, comandos rodados e resultado do ciclo upgrade/downgrade/upgrade.
