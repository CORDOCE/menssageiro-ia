---
name: spec-contatos-importacao
description: Spec da feature 0002-contatos-importacao. A fonte da verdade — os critérios de aceite são o contrato e o oráculo de teste.
---

# Spec: Contatos + importação (Fase 2 do Mensageiro)

## Contexto
Cadastro de contatos e importação CSV/XLSX com validação, consentimento (§5.9/ADR 0005) e descadastro (§5.4),
para a Fase 2 do BRIEFING §14. Detalhes em `product.md` e `design.md`. Pronto quando "contatos importados de
planilha com validação" e os AC abaixo passam. **Sem nenhum envio, template, Meta ou worker.**

**Dependências:** task 5 (auth) mergeada em `develop`; aprovação §4 das libs `phonenumbers` + `openpyxl` (ADR 0006).

## Criterios de aceite (o contrato)
Cada AC é testável e não-ambíguo (Definition of Ready). Um teste/gate por AC.

**CRUD**
- **AC-1** — Dado um telefone válido e inexistente, Quando `POST /contatos`, Então 201 e o contato é criado com
  `telefone_e164` **normalizado** e `consentimento=false` quando não informado.
- **AC-2** — Dado um telefone inválido, Quando `POST /contatos`, Então 422 e nenhum contato é criado.
- **AC-3** — Dado um telefone cujo E.164 canônico já existe, Quando `POST /contatos`, Então 409 (conflito) e não duplica.
- **AC-4** — Dada a API protegida, Quando acesso `GET /contatos` **sem** credencial → 401; **com** credencial → 200
  com lista paginada.
- **AC-5** — Dado contatos com grupos/tags/status variados, Quando `GET /contatos?grupo=&tag=&status=`, Então retorna
  só os que casam o filtro.
- **AC-6** — Dado um contato, Quando `PATCH /contatos/{id}` altera campos (inclusive telefone, re-normalizado), Então
  os campos mudam; telefone que colida com outro contato → 409.
- **AC-7** — Dado um contato ativo, Quando `POST /contatos/{id}/descadastrar`, Então `descadastrado_em` é setado, o
  contato **permanece** no banco e fica bloqueado (invariante §5.4).
- **AC-8** — Dado um contato sem opt-in, Quando `POST /contatos/{id}/consentimento` com origem+data válidas, Então
  `consentimento=true` com esses valores registrados.

**Importação**
- **AC-9** — Dado um CSV com linhas válidas, Quando `POST /contatos/importar`, Então cada linha vira contato
  (`telefone_e164` único) e o relatório marca `criado`/`atualizado` por linha.
- **AC-10** — Dado um XLSX equivalente, Quando `POST /contatos/importar`, Então o resultado é o mesmo do AC-9.
- **AC-11** — Dada uma planilha com linhas inválidas (telefone/nome), Quando importo, Então as inválidas entram no
  relatório com `erro`+`motivo` e **não persistem**, e as válidas da mesma planilha **persistem** (parcial por linha).
- **AC-12** — Dada uma linha **sem** `consentimento_origem`/`consentimento_data`, Quando importo, Então o contato é
  criado com `consentimento=false` (bloqueado); a importação **não** auto-consente (§5.9).
- **AC-13** — Dada uma linha **com** origem+data válidas, Quando importo, Então `consentimento=true` com esses valores.
- **AC-14** — Dado um telefone já cadastrado, Quando reimporto a mesma planilha, Então o contato é **atualizado** (não
  duplica) e a unicidade de `telefone_e164` é mantida.
- **AC-15** — Dado um telefone **descadastrado**, Quando ele aparece numa importação, Então é **ignorado** (não reativa,
  não altera) e o relatório marca `ignorado: descadastrado` (§5.4).
- **AC-16** — Dado qualquer log/auditoria desta feature, Quando um telefone é registrado, Então aparece **mascarado**
  (`+55119****0000`) e o relatório não vaza PII além do necessário.
- **AC-17** — Dado um arquivo acima do limite de tamanho/linhas, Quando importo, Então é rejeitado (413/422) com mensagem
  e nada é persistido.
- **AC-18** — Dado **qualquer** endpoint desta feature, Quando acesso sem credencial válida → 401.

**Dados / qualidade**
- **AC-19** — Dado um banco limpo, Quando `alembic upgrade head` e `alembic downgrade base`, Então ambos terminam com
  código 0 e o esquema de `contatos` (com índice único em `telefone_e164`) é criado/revertido.
- **AC-20** — Dado o `backend/`, Quando `pytest --cov`, Então a cobertura das **regras** (validação E.164, consentimento,
  dedup/upsert, descadastro) é ≥ 90% (CLAUDE.md §8), além de `ruff`/`mypy` código 0.

## Matriz de decisao — importação de uma linha (telefone T)  (cada linha vira teste)
| contato T existe? | descadastrado? | origem+data válidas na linha? | resultado |
|---|---|---|---|
| não | — | sim | cria; `consentimento=true` |
| não | — | não/ inválida | cria; `consentimento=false` (bloqueado) |
| sim | não | sim | atualiza; `consentimento=true` (origem/data da linha) |
| sim | não | não/ inválida | atualiza demais campos; **mantém** o consentimento existente (não revoga nem rebaixa) |
| sim | **sim** | qualquer | **ignorado: descadastrado** (não reativa, não altera) |

## Casos de borda
- Telefone com formatação variada (espaços, parênteses, com/sem +55) → normaliza para o canônico; dedup pelo canônico.
- Duas linhas na **mesma** planilha com o mesmo telefone → a segunda **atualiza** a primeira (last-wins), marcada no relatório.
- CSV com encoding do Excel → tentar `utf-8-sig`; falha de decodificação → relatório de erro claro, sem quebrar o import.
- XLSX com fórmulas → lido em `read_only`/`data_only` (valor calculado); nunca executa fórmula.
- `consentimento_data` em formato inválido ou no futuro → tratada como ausente → `consentimento=false` + motivo no relatório.
- `nome` vazio → linha inválida (nome é obrigatório).
- Planilha sem a coluna de cabeçalho esperada → erro de importação explicando as colunas aceitas (nada persiste).

## Fora de escopo (vinculante)
- Qualquer envio, template, webhook da Meta, worker ou IA (fases 3+).
- Telas do PWA de contatos (Fase 5).
- Expansão de grupo em envios / idempotência de disparo (Fase 4 / ADR 0005).
- Job de importação assíncrono / fila.
- Integração com fonte externa de contatos; multiusuário/permissões.
- Campos de `contatos` além dos do BRIEFING §9.

## Suposicoes (explícitas — confirmar no gate; CLAUDE §1.4)
1. **Colunas canônicas do arquivo:** `nome`, `telefone`, `grupo`, `tags`, `consentimento_origem`,
   `consentimento_data`, `observacoes`. `tags` separadas por `;`. `consentimento_data` em ISO-8601 (`YYYY-MM-DD`).
2. **Limites default:** arquivo ≤ 5 MB e ≤ 5.000 linhas (configuráveis).
3. `consentimento_origem` é **texto livre** na v1 (não enum).
4. `PATCH` pode alterar o telefone (re-normaliza + checa unicidade).
5. Reimportar **sem** coluna de consentimento **não revoga** um opt-in já existente.
