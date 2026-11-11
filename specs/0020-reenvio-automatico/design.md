---
name: design-reenvio-automatico
description: Design doc da feature 0020 Reenvio automático (Tier Arquitetural). Solução, alternativas, trade-offs. Decisão irreversível → ADR 0014.
---

# Design: Reenvio automático de envios (falha transitória)

> Decisões de escopo em `clarificar.md` (Q1–Q7). Respeita a arquitetura atual do worker/disparo (ADR 0008).

## Solução proposta

### 1. Esquema (migração aditiva — sem destrutivo)
Em `envios` (reusa a linha — **Q3**; mantém 1 linha por `(agendamento, contato)`, §5.2):
- `tentativas INT NOT NULL DEFAULT 0` — nº de **reenvios** já feitos (0 = só o envio original).
- `proxima_tentativa_em TIMESTAMPTZ NULL` — quando o worker deve retentar.
- Dois valores novos de status (coluna já é `String(20)`; só atualizar o enum em `schemas/envio.py:17-22`):
  `aguardando_retry` (retentar depois) e `aguardando_decisao` (esgotou → humano).

### 2. Classificar a falha (Q4 + Q7 at-most-once)
Só é **retentável** a falha com **certeza de não-entrega**:
- **HTTP 429** (limite) — a Meta rejeitou antes de processar.
- **Falha de conexão ANTES de enviar o request** (ex.: connect/DNS error, nenhum byte enviado).
- **Allowlist curta** de códigos Meta comprovadamente temporários **e** de não-entrega — montada com
  **/meta-whatsapp** + doc oficial (§1: não inventar código; fica na task de implementação).

**Não retentável** (fica `falhou` como hoje): `5xx`/timeout **após** o request (ambíguo — a Meta pode ter
processado → risco de entrega dupla, vedado pela §5.2/Q7) e todo erro definitivo (número inválido, não-usuário,
descadastrado, template rejeitado).

Mecânica: o `whatsapp_client` passa a sinalizar na falha se ela é **certamente-não-entregue** (ex.: campo
`retentavel: bool` em `WhatsappError`, derivado do status HTTP / exceção de conexão). Hoje `WhatsappError` só
carrega `codigo`/`motivo` (`whatsapp_client.py:22`); conexão pré-request hoje nem é capturada como `WhatsappError`
(propaga) — a task inclui capturá-la.

### 3. Agendar o reenvio (Q2 — até 3x, backoff curto)
No ponto de falha do disparo (`disparo.py:357-367`), quando `retentavel`:
- se `tentativas < 3`: status → `aguardando_retry`, `tentativas += 1`,
  `proxima_tentativa_em = agora + BACKOFF[tentativas]` com `BACKOFF = {1: 5min, 2: 15min, 3: 1h}`;
  auditoria `envio.retry_agendado` (sem PII).
- se `tentativas == 3` (esgotou): status → `aguardando_decisao` + auditoria/alerta `envio.retry_esgotado`
  (`alertar_evento`, warning). **Q5/Q5b.**
Falha **não** retentável → `falhou` + alerta (comportamento atual).

### 4. Executar o reenvio (novo passo do worker)
A cada ciclo (`__main__.py` `executar()`), um novo passo seleciona
`status='aguardando_retry' AND proxima_tentativa_em <= agora` com **`FOR UPDATE SKIP LOCKED`** (padrão §5.2/ADR
0008). Para cada envio: **reavaliar elegibilidade** (consentimento/descadastro/janela — reusa `_motivo_inelegivel`,
`disparo.py:323`); se inelegível agora → `falhou` com motivo (descadastro respeitado, §5.4); se elegível → reenvia
pelo mesmo caminho de envio e aplica o desfecho (sucesso→`enviado`; falha→volta ao passo 3). Refatorar o
"enviar-1-contato + aplicar desfecho" (`disparo.py:331-367`) num helper reusável (o reenvio **não** re-reserva —
a linha já existe).

### 5. Decisão humana por envio (Q5b)
Novo endpoint autenticado `POST /envios/{id}/reenviar`: exige `status == 'aguardando_decisao'` (409 senão), zera
`tentativas`, status → `aguardando_retry`, `proxima_tentativa_em = agora`, auditoria `envio.reenvio_manual` com
`ator_email`. Botão "Reenviar" na tela **Histórico** (só quando `aguardando_decisao`). Molde: o
`POST /agendamentos/{id}/reenviar` existente (`agendamentos.py:112-131`).

### 6. Limites e observabilidade
- `aguardando_retry` entra em **`_CONTAM_LIMITE`** (`disparo.py:46`): conta para os tetos (0016) — é um envio
  reservado/pretendido — **e** para o denominador de "tentativas" da 0019 (**Q6**), sem contar como falha.
- **Dependência 0019:** a 0019 vai a produção antes; task da 0020 **atualiza a definição de tentativa da 0019**
  para incluir `aguardando_retry`. Proposta (confirmar no gate): `aguardando_decisao` (esgotado) **conta como
  falha** na taxa (não-entrega real, resolvida) — extensão natural da Q6.

## Alternativas consideradas
| opção | prós | contras | veredito |
|---|---|---|---|
| A (escolhida) reusar linha + at-most-once estrito | §5.2 intacta (nunca entrega 2x), migração aditiva, menos código | recupera menos blips (5xx/timeout não reenvia) | **escolhida (Q3+Q7)** |
| Tabela de tentativas separada | histórico rico por tentativa | duplica estado, complica locking/idempotência | rejeitada (Q3) |
| At-least-once (reenvia 5xx) | recupera o máximo | entrega dupla possível → enfraquece §5.2 | rejeitada (Q7) |
| Fila/broker externo (retry infra) | robusto, desacoplado | nova dependência/infra, § exagero p/ o volume | fora de escopo |

## Trade-offs e riscos
- **Recupera menos** (5xx/timeout viram `falhou`+decisão humana) — preço do at-most-once. Aceito (Q7).
- **Risco de órfão `enviando`**: hoje conexão pré-request não vira `falhou` (propaga) — a task precisa capturá-la,
  senão o reenvio nunca é agendado. Teste de borda explícito.
- **Reavaliar elegibilidade no reenvio** é obrigatório (§5.4/§5.9): contato que saiu entre o 1º envio e o reenvio
  não pode receber. Caso de ataque/borda → teste.
- **Interação com teto 0016**: cada reenvio conta; não pode ultrapassar o teto por-agendamento/contato.
- **Janela/template (§5.3)**: reenvio continua template UTILITY aprovado; backoff máx ~1h20 não estoura validade.

## Decisões irreversíveis (→ ADR 0014)
- Evoluir a invariante **§5.2**: falha transitória **com certeza de não-entrega** deixa de ser terminal e entra
  em ciclo de reenvio limitado na **mesma linha**; at-most-once preservado. (ADR 0014, aprovação §4 dada.)
