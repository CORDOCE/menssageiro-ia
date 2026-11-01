---
name: design-contatos-importacao
description: Design doc da feature 0002-contatos-importacao (tier arquitetural). Modelo de contatos, importação CSV/XLSX, normalização E.164, consentimento e descadastro — respeitando a arquitetura da Fase 1.
---

# Design: Contatos + importação (Fase 2 do Mensageiro)

## Solucao proposta
Seguir a arquitetura do BRIEFING §5/§6 e os padrões já estabelecidos na Fase 1 (task 5): SQLAlchemy 2
(`Mapped`/`mapped_column`, PK `String(36)` uuid, `server_default=func.now()`), routers em `app/api`,
schemas Pydantic v2 em `app/schemas`, rota protegida via `usuario_atual` (`core/auth_deps`), auditoria via
`core/audit.registrar_auditoria`, migrações Alembic com downgrade. **Não** inventar padrão novo.

**Dependência de ordem (vinculante):** a Fase 2 pressupõe a **task 5 (auth) mergeada em `develop`** — usa
`usuario_atual` (rota protegida), `core/audit`, os diretórios `models/`/`schemas/` e **encadeia a migration
após `ab30d72b78e4`**. Enquanto a task 5 não entra em `develop`, esta spec fica aprovada mas **não
implementável**.

**Componentes (novos, salvo indicação):**
- `app/models/contato.py` — modelo `Contato` (BRIEFING §9): `id` (str36 uuid PK), `nome`, `telefone_e164`
  (String, **unique+index**), `grupo` (String, nullable), `tags` (JSONB lista de strings), `consentimento`
  (bool, default **False**), `consentimento_data` (timestamptz, nullable), `consentimento_origem` (String,
  nullable), `descadastrado_em` (timestamptz, nullable), `ultima_mensagem_recebida_em` (timestamptz, nullable),
  `observacoes` (Text, nullable), `criado_em`/`atualizado_em`. Mesmo estilo de `models/usuario.py`.
- `app/schemas/contato.py` — `ContatoCreate`, `ContatoUpdate`, `ContatoRead`, `RegistrarConsentimento`, e os do
  import (`ResultadoLinha`, `RelatorioImportacao`).
- `app/api/contatos.py` — router **protegido** (`Depends(usuario_atual)`): `POST /contatos`, `GET /contatos`
  (paginado + filtros status/grupo/tag), `GET /contatos/{id}`, `PATCH /contatos/{id}`,
  `POST /contatos/{id}/descadastrar`, `POST /contatos/{id}/consentimento`, `POST /contatos/importar` (multipart).
- `app/services/contatos_import.py` — parse CSV (stdlib `csv`) e XLSX (`openpyxl`, `read_only`), validação por
  linha, normalização E.164, upsert idempotente por telefone, montagem do relatório. **Não persiste o arquivo**
  (dados mínimos, §11).
- `app/core/telefone.py` (novo) — `normalizar_e164(raw, regiao="BR")` e `mascarar_telefone(e164)` →
  `+55119****0000`, reutilizado em logs/auditoria (§6; util de mascaramento ainda não existe no repo).
- Migration Alembic **aditiva**: cria `contatos` (índice único em `telefone_e164`); downgrade dropa.

**Fluxo de importação (síncrono — escala dezenas–centenas, BRIEFING §1):**
1. Upload multipart → detecta formato (extensão + content-type); valida tamanho e nº de linhas (limite configurável).
2. Parse → linhas; mapeia colunas canônicas: `nome`, `telefone`, `grupo`, `tags`, `consentimento_origem`,
   `consentimento_data`, `observacoes` (cabeçalho obrigatório; colunas extras ignoradas).
3. Por linha: normaliza telefone para **E.164 canônico**; valida obrigatórios. Inválida → entra no relatório
   (`linha`, `erro`, `motivo`), **não persiste**.
4. **Consentimento (§5.9 / ADR 0005):** `consentimento_origem` + `consentimento_data` presentes e válidas →
   `consentimento=true` com esses valores; senão `consentimento=false` ("sem consentimento", bloqueado para envio).
   A importação **nunca** auto-consente.
5. **Upsert por `telefone_e164` canônico:** novo → cria; existente → atualiza campos. **Nunca ressuscita
   descadastrado** (se `descadastrado_em` != null → não reativa; relatório = "ignorado: descadastrado"). Invariante §5.4.
6. Resultado: relatório por linha (`criado`/`atualizado`/`ignorado`/`erro` + motivo) + totais; auditoria do import
   **sem PII** (contagens, não a lista de telefones).

**Descadastro:** soft — `descadastrado_em = now`; o contato permanece (prova LGPD/auditoria) e fica bloqueado para
qualquer envio futuro (§5.4). Reimportar não reativa.

## Alternativas consideradas
| opcao | pros | contras | veredito |
|---|---|---|---|
| **E.164: `phonenumbers`** | normalização/validação robusta (DDD, 9º dígito), dedup confiável | dependência nova | **Escolhida** |
| E.164: regex BR na mão | sem dependência | frágil p/ variações; dedup furada | Descartada |
| **XLSX: `openpyxl` (`read_only`)** | lê .xlsx de forma leve e segura | dependência nova | **Escolhida** |
| XLSX: `pandas` | poderoso | peso/overkill p/ a escala | Descartada |
| só CSV | zero dep | viola BRIEFING §3 ("CSV/XLSX") | Descartada |
| **Import síncrono in-request** | simples; escala pequena | trava request em arquivo grande | **Escolhida** (+ limite de tamanho) |
| Job assíncrono | não trava | sem fila nesta fase; overkill | Descartada |
| **Descadastro soft (`descadastrado_em`)** | prova LGPD; auditável; §5.4 | linha permanece | **Escolhida** |
| Hard delete | "limpo" | perde rastro; risca §5.8 | Descartada |
| **Reimport upsert parcial por linha** | relatório de erros; linhas boas entram | — | **Escolhida** |
| Tudo-ou-nada transacional | atômico | 1 erro aborta o lote; UX pior | Descartada |
| **`tags` JSONB lista** | simples; filtro por tag | — | **Escolhida** |
| tabela N:N de tags | normalizado | overkill v1 | Descartada |

## Trade-offs e riscos
- **Duas dependências novas** (`phonenumbers`, `openpyxl`) → exigem aprovação do responsável (CLAUDE.md §4):
  justificativa = correção de E.164 (nativo é inviável/frágil) e leitura de XLSX (sem alternativa nativa); libs
  maduras, mantidas, licença permissiva. Versões fixadas; entram no `pip-audit` do CI.
- Import síncrono trava a request em arquivos grandes → mitigado pela escala + **limite de tamanho/linhas** configurável.
- **Upload é superfície de ataque:** validar content-type/tamanho/nº de linhas; `openpyxl` em `read_only`/`data_only`
  (não executa fórmula); tratar conteúdo da planilha como **não confiável**; nada de arquivo persistido em disco.
- Telefone em log → sempre `mascarar_telefone` (§6). Texto de erro do import não vaza PII.

## Decisoes irreversiveis (-> ADR)
- **ADR 0006 (pendente de aprovação §4)** — Normalização de telefone **E.164 via `phonenumbers`** como formato
  canônico de armazenamento e **chave de deduplicação**; **`openpyxl`** para leitura de XLSX. É difícil de reverter
  porque define o formato gravado e a identidade de contato (reverter exige reprocessar toda a base).
