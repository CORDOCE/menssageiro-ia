---
name: spec-nova-mensagem
description: Spec da feature 0011-nova-mensagem. A fonte da verdade — os critérios de aceite são o contrato e o oráculo de teste.
---

# Spec: Nova mensagem (criar agendamento pela UI)

## Contexto
Hoje o operador consegue ver agendamentos (tela Hoje, spec 0006) e gerir contatos/modelos, mas **não há como
criar um agendamento pela interface** — só por chamada direta ao `POST /agendamentos`. Esta feature entrega a
tela **Nova mensagem**: escolher um modelo aprovado, um contato elegível, preencher as variáveis do template,
definir quando enviar e gravar o agendamento. Backend já pronto: `GET /modelos` (0010) e `POST /agendamentos`
(0004). Tier **Pequeno** (feature de frontend sobre endpoints existentes).

> **Suposições de escopo do v1 (aprovar no gate — reversíveis):**
> - **S1** Destinatário: **só contato individual** (campo `grupo` fica fora — ver Fora de escopo).
> - **S2** **Só envio único** (avulso); recorrência/RRULE fica fora.
> - **S3** Modelos oferecidos: **só `status = aprovado`** (invariante §5.3; `GET /modelos?status=aprovado`).
> - **S4** Contatos oferecidos: **só elegíveis** = `consentimento = true` **e** não descadastrado (invariantes §5.4, §5.9).

## Critérios de aceite (o contrato)
Cada AC é **testável e não-ambíguo** (Definition of Ready). Um teste por AC, com **Vitest + Testing Library**
(infra introduzida nesta feature — o frontend não tinha framework de teste; a 0006 validou por tsc/build +
staging), com o cliente de API mockado — nunca Meta/OpenAI real (§5.7).

- **AC-1** — Dado que existem modelos com `status=aprovado` e outros não aprovados, Quando a tela Nova mensagem
  carrega, Então o seletor de modelo lista **apenas** os aprovados (chamando `GET /modelos?status=aprovado`),
  ordenados por nome.
- **AC-2** — Dado um modelo selecionado com `variaveis = ["1","2"]`, Quando ele é escolhido, Então a tela
  renderiza **exatamente 2** campos de variável rotulados (`{{1}}`, `{{2}}`) e exibe o `corpo` do template como
  prévia; Quando o modelo tem `variaveis = []`, Então **nenhum** campo de variável é exibido.
- **AC-3** — Dado contatos com `consentimento=true` e contatos sem consentimento ou descadastrados, Quando o
  operador abre o seletor de contato, Então só os **elegíveis** (S4) são selecionáveis.
- **AC-4** — Dado o formulário com modelo, contato, todas as variáveis preenchidas e data/hora **futura**,
  Quando o operador envia, Então a tela chama `POST /agendamentos` com `{contato_id, modelo_id, variaveis,
  executar_em}` (`executar_em` em ISO-8601 com offset, convertido do horário local America/Sao_Paulo para UTC),
  e ao receber 201 exibe confirmação de sucesso.
- **AC-5** — Dado o formulário incompleto (sem modelo, sem contato, variável vazia, ou data no passado), Quando
  o operador tenta enviar, Então o envio é **bloqueado no cliente** com mensagem por campo e **nenhuma** chamada
  a `POST /agendamentos` é feita.
- **AC-6** — Dado que o backend responde erro (ex.: 422 de validação, 409/limite diário, 401 sessão expirada),
  Quando o operador envia, Então a tela exibe mensagem de erro legível (sem vazar stack/PII) e **não** apaga o
  que o operador já preencheu; em 401, redireciona para login (padrão da guarda de auth da 0006).
- **AC-7** — Dado um agendamento criado com sucesso, Quando a confirmação é exibida, Então o operador tem um
  caminho claro para **criar outra** (formulário limpo) ou **voltar** para a tela de origem.

## Casos de borda
- Nenhum modelo aprovado disponível → estado vazio orientando a sincronizar/aprovar modelos (não quebra a tela).
- Nenhum contato elegível → estado vazio orientando a registrar consentimento (link para Contatos).
- Troca de modelo depois de preencher variáveis → campos de variável são recriados conforme o novo `variaveis`
  (não mantém valores órfãos de outro template).
- Variável preenchida só com espaços → tratada como vazia (bloqueia, AC-5).
- Data/hora exatamente "agora" ou com poucos segundos no futuro → política de mínimo a definir no gate (ver
  Questões em aberto); por ora, **passado estrito** é bloqueado.
- Texto de variável é **dado não confiável** (§6): enviado como valor de parâmetro, nunca concatenado em
  instrução; sem HTML/markdown interpretado na prévia.

## Fora de escopo (vinculante)
- Envio para **grupo** (campo `grupo` do agendamento) — spec futura.
- **Recorrência** (RRULE) na UI — spec futura (backend já suporta, spec 0005).
- **Anexos / cabeçalho de mídia** (DOCUMENT/IMAGE no header do template) — spec futura.
- Criar/editar/**submeter template** à Meta — spec futura.
- Edição/cancelamento de agendamento pela tela Nova mensagem (cancelar já existe em outro fluxo).
- Envio imediato "disparar agora" fora do mecanismo de agendamento (invariante §5.1: só o worker dispara).

## Questões em aberto — RESOLVIDAS no gate (Jefferson, 2026-11-06, com evidência no código)
1. **Mínimo de antecedência:** **passado estrito** — o cliente bloqueia `executar_em ≤ agora`. O `POST
   /agendamentos` não valida data futura no `criar` (`backend/app/api/agendamentos.py:34-52`), então é só no front.
2. **Seleção de contato:** **filtrar no cliente** — `GET /contatos?status=ativo` (exclui descadastrados;
   `contatos.py:69-70`; não há filtro de `consentimento` no servidor) + filtrar `consentimento === true` no front.
   Limitação aceita: enxerga só a página carregada (ok para a base pequena atual).
3. **Origem:** **não enviar** — o schema já aplica default `origem="operador"` (`schemas/agendamento.py:20`).

## Matriz de decisão — habilitação do botão Enviar (cada linha vira teste)
| modelo escolhido | contato elegível escolhido | todas variáveis preenchidas | data/hora futura | botão Enviar |
|---|---|---|---|---|
| não | — | — | — | desabilitado |
| sim | não | — | — | desabilitado |
| sim | sim | não | — | desabilitado |
| sim | sim | sim | não (passado) | desabilitado |
| sim | sim | sim | sim | habilitado |
