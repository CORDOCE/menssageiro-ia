# ADR 0016 — Anexos PDF (DOCUMENT): bytea no banco + upload no disparo

Data: 2026-11-12 · Status: proposto (spec 0024 / dívida A4) · Responsável: Jefferson

## Contexto
Cobranças precisam levar o boleto em PDF no cabeçalho DOCUMENT do template. O `whatsapp_client` já sobe
mídia e monta o header, mas falta o fluxo fim-a-fim. A Fase 4 fechou sem anexos (débito A4). Não há schema
de anexo (verificado — a dívida F3 estava desatualizada).

## Decisão
1. **Guardar o PDF no banco** — tabela `anexos` com coluna `conteudo` **bytea** + metadados; `agendamentos.anexo_id`
   FK nullable. Sem bucket/infra nova (volume baixo, boletos pequenos).
2. **Upload à Meta no disparo** — o worker faz `upload_midia` no momento do envio (o `media_id` é efêmero e o
   agendamento pode ser futuro), **1× por disparo** (reusa o `media_id` no lote do grupo).
3. **Só PDF no v1** — validação no upload: mime `application/pdf` + magic bytes `%PDF-` + cap de tamanho
   (`ANEXO_MAX_BYTES`, 5 MB). O backend nunca executa/parseia o PDF (§6).
4. **Coerência modelo × anexo** — modelo `DOCUMENT` exige `anexo_id`; modelo sem DOCUMENT recusa anexo (422).
5. **Pix** = variável de texto do template (sem código novo).

## Alternativas rejeitadas
- **Bucket de objetos** (Railway/S3): infra + credenciais; over-engineering para o volume atual. Reavaliar se crescer.
- **Upload na criação do agendamento**: `media_id` pode expirar antes de um envio futuro.

## Consequências
- **+** Cobranças com boleto fim-a-fim; reusa o cliente Meta existente; sem dep nova.
- **−** `bytea` pode inchar o banco (mitigado por volume baixo + follow-up de retenção). 1 upload extra à Meta
  por disparo. Validação real adiada à Fase 0.
- **Reversível**: migração aditiva com `downgrade`; sem anexo, o envio segue como hoje (só texto).
