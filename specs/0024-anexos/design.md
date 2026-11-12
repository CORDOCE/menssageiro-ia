# Design — 0024 Anexos (PDF/boleto no cabeçalho DOCUMENT)

## Solução
Guardar o PDF no banco até o disparo; o **worker** sobe à Meta no momento do envio e inclui o cabeçalho
DOCUMENT. Reusa o `whatsapp_client` existente (`upload_midia`, `componente_documento`).

1. **Modelo + migração**:
   - Tabela `anexos`: `id`, `nome_arquivo`, `mime`, `tamanho` (bytes), `conteudo` (**LargeBinary/bytea**), `criado_em`.
   - `agendamentos.anexo_id` — FK → `anexos` (nullable). (A dívida dizia "colunas inertes"; **verificado que não existem** → criadas aqui.)
2. **Upload — `POST /anexos`** (multipart, autenticado): valida **mime `application/pdf`** + **magic bytes `%PDF-`**
   + **tamanho ≤ `ANEXO_MAX_BYTES`** (default 5 MB, §6 anti-DoS). Salva os bytes; devolve `{id, nome_arquivo, tamanho}`.
3. **Vínculo — `POST /agendamentos`** ganha `anexo_id` opcional, com **regra de coerência**:
   - modelo com `cabecalho_tipo == "DOCUMENT"` → `anexo_id` **obrigatório** (o template exige o documento);
   - modelo sem DOCUMENT → `anexo_id` deve ser **ausente** (422 se vier). Anexo inexistente → 404/422.
4. **Disparo (worker)** — se `ag.anexo_id`: lê o anexo, faz `upload_midia(bytes, mime)` **uma vez por disparo**
   (reusa o `media_id` para todos os contatos do grupo), e monta `componentes = [componente_documento(media_id), body]`.
   Toca a **regra de envio** (§4). No-op/erro tratado: upload falha → `envio.falhou` + alerta (como os demais erros).
5. **Pix**: sem código novo — o operador coloca o código Pix numa **variável** do body do template (já suportado).
6. **UI (Nova mensagem, 0011)**: quando o modelo selecionado tem `cabecalho_tipo == "DOCUMENT"`, mostra um
   input de **PDF**; sobe via `POST /anexos` e passa o `anexo_id` ao criar o agendamento.

## Alternativas consideradas
- **Armazenamento bytea (escolhido)** × bucket de objetos: bytea evita infra nova; boletos são pequenos e o
  volume é dezenas/dia. Bucket fica para quando o volume/tamanho crescer (follow-up).
- **Upload no disparo (escolhido)** × upload na criação: o `media_id` da Meta é efêmero e o agendamento pode
  ser futuro → subir no disparo é robusto. Custo: 1 chamada extra à Meta por disparo (aceitável).

## Trade-offs / riscos
- **Superfície de ataque (§6)**: upload de arquivo. Mitigação: cap de tamanho, mime + magic bytes, nome
  sanitizado; o backend **nunca executa/parseia** o PDF — só o repassa à Meta. Caso de ataque (não-PDF, bomba) vira teste.
- **bytea incha o banco**: volume baixo + follow-up de retenção (limpar `conteudo` de anexos de envios concluídos).
- **Validação real** depende da **Fase 0** (número +55). v1 testado por **mock** da Meta.
- **Limites exatos da Meta** (tamanho/mime de documento em template) — confirmar com `/meta-whatsapp` na implementação.

## Impacto / §4
- **Regra de envio** (worker monta DOCUMENT) → aprovação §4. **Migração** (tabela + FK) → `/migracao`. **ADR 0016**.
- Toca a **Cloud API** (upload de mídia já existente) → `/meta-whatsapp` na implementação. Sem dep nova.
