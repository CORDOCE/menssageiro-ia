---
name: product-contatos-importacao
description: Product brief da feature 0002-contatos-importacao (tier arquitetural). Cadastro, importação CSV/XLSX, consentimento e descadastro de contatos — Fase 2 do BRIEFING §14.
---

# Product: Contatos + importação (Fase 2 do Mensageiro)

> Produto, arquitetura e regras completas no `BRIEFING.md`. Este brief cobre só o recorte da Fase 2
> (BRIEFING §14) e não redefine o produto.

## Problema
Sem uma base de contatos confiável e com **consentimento registrado**, nenhuma fase de envio (3+) pode
começar: não há para quem enviar, nem como provar o opt-in exigido pela Meta e pela LGPD. Hoje o sistema
tem só login/esqueleto (Fase 1). A Fase 2 entrega o **cadastro de contatos** e a **importação em massa de
planilhas**, com validação e trilha de consentimento, para o operador único (cliente).

## Metrica de sucesso
Critério de pronto do BRIEFING §14 fase 2: **contatos importados de planilha com validação**. Observável:
o operador importa um CSV/XLSX; linhas válidas viram contatos (telefone E.164 único), linhas inválidas são
reportadas com o motivo, e o **estado de consentimento** de cada contato fica explícito (com opt-in, ou
bloqueado para envio) — **sem nenhum envio real**.

## Goals
- CRUD de contatos (criar, ler, atualizar, descadastrar) via API protegida (auth da Fase 1).
- Importação CSV/XLSX com **validação por linha** (E.164, campos obrigatórios), **relatório de erros** por
  linha e **deduplicação por telefone** (reimportar o mesmo número atualiza, não duplica).
- **Consentimento** (opt-in: bool + data + origem) conforme invariante CLAUDE.md §5.9 / ADR 0005: a
  importação **não auto-consente** — linha sem origem+data entra "sem consentimento" e fica bloqueada para
  envio até o operador registrar a base.
- **Descadastro** modelado e imediato — contato descadastrado nunca mais recebe (invariante §5.4), já
  previsto aqui mesmo que o envio só exista a partir da Fase 3.
- Mascaramento de telefone em logs e dados mínimos (LGPD, §11); toda ação que muda estado gera auditoria (§5.8).
- Migração Alembic **aditiva** da tabela `contatos` (BRIEFING §9), com `downgrade` funcional.

## Non-goals (vinculante)
- **Nenhum envio, template, webhook da Meta ou worker** (fases 3+). Contatos aqui são só dados.
- **Telas do PWA de contatos** — o frontend completo é a Fase 5 (BRIEFING §14); a Fase 2 entrega backend +
  importação. (Se o design concluir que uma UI mínima de upload é necessária para "importar com validação",
  isso é decidido no `design.md`, não assumido aqui.)
- Expansão de grupo em envios e idempotência de disparo — é a Fase 4 (ADR 0005); aqui `grupo/tags` é só
  rótulo no contato.
- Integração com o sistema de recibos ou qualquer fonte externa de contatos (fora da v1, BRIEFING §3).
- Multiusuário/permissões.
