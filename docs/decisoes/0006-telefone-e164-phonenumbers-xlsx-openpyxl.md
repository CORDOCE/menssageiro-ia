# ADR 0006 — Telefone E.164 via `phonenumbers` e leitura XLSX via `openpyxl`

- **Status:** aceito
- **Data:** 2026-11-01
- **Contexto da feature:** `specs/0002-contatos-importacao/` (design.md)
- **Aprovação:** dependências novas aprovadas por Jefferson em 2026-11-01 (CLAUDE.md §4)

## Contexto
A Fase 2 cadastra e importa contatos (CSV/XLSX) e precisa **normalizar/validar telefones** e **deduplicar por
número**. Uma normalização nativa na mão (regex) é frágil para as variações brasileiras (DDD, 9º dígito,
formatação) e comprometeria a chave de deduplicação. Ler `.xlsx` não tem alternativa na biblioteca padrão.

## Decisão
1. **`phonenumbers`** (porte do libphonenumber do Google) para normalizar/validar telefones; o **E.164 canônico**
   (região padrão `BR`) é o formato **armazenado** em `contatos.telefone_e164` e a **chave de deduplicação**.
2. **`openpyxl`** em modo `read_only`/`data_only` para ler `.xlsx` (não executa fórmula); CSV via `csv` da stdlib.
3. Versões **fixadas** no `pyproject`; ambas entram no `pip-audit` do CI. Licenças permissivas
   (phonenumbers Apache-2.0; openpyxl MIT).

## Consequências
- O E.164 canônico passa a definir a **identidade** do contato; reverter a estratégia exigiria reprocessar toda a
  base — por isso é um ADR.
- Duas dependências novas a manter e auditar.
- Superfície de ataque do upload mitigada: `openpyxl` `read_only`/`data_only`, limite de tamanho/linhas, conteúdo
  da planilha tratado como não confiável (BRIEFING §6 / spec 0002).
- Implementação dessas tasks (`[dep]` no tasks.md da 0002) fica liberada; permanece a dependência de ordem da
  task 5 (auth) em `develop`.
