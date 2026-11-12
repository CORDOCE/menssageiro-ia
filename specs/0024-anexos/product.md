# Product — 0024 Anexos (PDF/boleto no cabeçalho DOCUMENT) — dívida A4

## Problema
O caso de uso central do sistema é **cobrança** (BRIEFING §1), e a cobrança por WhatsApp normalmente leva
um **boleto em PDF** no cabeçalho do template (DOCUMENT) e o **código Pix** no texto. O `whatsapp_client`
já sabe subir mídia e montar o cabeçalho DOCUMENT, mas **não há fluxo fim-a-fim**: o operador não consegue
anexar um PDF a um agendamento, e o worker não inclui o documento no envio. A Fase 4 fechou **sem anexos**
(débito A4). Sem isso, as cobranças saem sem boleto.

## Para quem
O **operador** (1 admin), ao criar um agendamento de cobrança com boleto.

## Métrica de sucesso
Um agendamento com PDF anexado dispara, no horário, uma mensagem de template **com o boleto no cabeçalho
DOCUMENT** (validação real depende da Fase 0 / número +55).

## Goals
- Upload de **PDF** pelo operador (com validação de tipo/tamanho/conteúdo — §6), guardado até o disparo.
- Vincular o anexo a um agendamento cujo **modelo tem cabeçalho DOCUMENT**.
- O **worker**, no disparo, sobe o PDF à Meta (`upload_midia`) e inclui `componente_documento` no envio.
- **Pix**: já suportado — vai como **variável de texto** do template (sem código novo; é uso, não feature).

## Non-goals (fora do v1)
- Outros tipos de mídia (imagem, vídeo, áudio) — só **PDF** no v1.
- Edição/preview do PDF; múltiplos anexos por agendamento; biblioteca de anexos reutilizáveis.
- **Validação de envio real** com anexo (depende da Fase 0 — número +55; código testado por mock).
- Retenção/limpeza automática dos bytes (follow-up); storage em bucket (decisão: bytea no banco).
