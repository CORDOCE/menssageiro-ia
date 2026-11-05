---
name: spec-pwa-telas
description: Spec da spec 0006 — PWA telas v1 (Fundação + Hoje + Contatos). Os AC são o contrato, verificados por eslint+tsc+build e smoke de navegador. Decide ADR 0010.
---

# Spec: PWA — telas v1 (spec 0006)

## Contexto
Primeiras telas reais do PWA (Fase 5), sobre os endpoints já existentes (auth, contatos, agendamentos) e o
DESIGN-DASHBOARD.md (aprovado 29/10/2026). Entrega a **fundação** do frontend (tokens claro/escuro, troca de
tema, shell responsivo, guarda de auth) + as telas **Hoje** e **Contatos**. Detalhes em `product.md`/`design.md`.
**Pronto quando**: o operador autenticado abre o app, vê os envios programados em **Hoje**, gerencia a base em
**Contatos** (incl. importar), troca o tema sem flash, tudo responsivo — e os AC abaixo passam.

**Dependências:** nenhum endpoint novo no backend; **sem npm novo** (CSS+tokens, `next/font`, SVG). Verificação
sem test runner: `eslint` + `tsc --noEmit` + `build` + **smoke de navegador** (webapp-testing).

## Decisões do gate (confirmadas no plano aprovado por Jefferson, 2026-11-04)
1. **Import CSV/XLSX** entra no v1 de Contatos (endpoint `POST /contatos/importar` pronto).
2. Indicadores do **Hoje** no v1 = só **"Programadas"**; os demais como **"—" / em breve** (sem endpoint).
3. Selo de **saúde** no Hoje = **estático "Sistema ok"** até existir endpoint de saúde.

## Critérios de aceite (o contrato)

**Fundação / tema (DESIGN §2, §4, §10)**
- **AC-1** — Dado o app carregando, Quando a preferência de tema é "escuro" (ou "sistema" com SO escuro), Então
  o tema escuro já está aplicado **na 1ª pintura** (sem flash claro→escuro). O seletor oferece **Claro / Escuro /
  Seguir o sistema**; trocar aplica na hora e **persiste** (recarregar mantém).
- **AC-2** — Dado qualquer tela, Então todas as cores vêm de **tokens** (claro e escuro definidos); nenhum valor
  de cor fixo fora dos tokens; selos de status aparecem **com cor + texto** (nunca só cor).
- **AC-3 (responsivo)** — Em ≥1024px há **menu lateral**; em <640px há **barra inferior**; Hoje e Contatos são
  navegáveis em ambos; itens ainda não implementados aparecem **desabilitados ("em breve")**.
- **AC-4 (guarda de auth)** — Dado acesso a uma rota do app **sem token válido**, Então o usuário é redirecionado
  para `/login`; com token válido (via `/auth/me`), a tela carrega. "Sair" limpa o token e volta ao login.

**Tela Hoje (DESIGN §5)**
- **AC-5** — Dado agendamentos futuros `status=aprovado`, Quando abro **Hoje**, Então vejo a lista **Envios
  programados** em ordem cronológica, cada linha com **data `dd/mm` sobre `HH:mm`**, **contato** (nome resolvido;
  grupo quando for grupo), **selo de status** e **ícone de recorrência** quando o agendamento tem `recorrencia`;
  no máximo **8 linhas**.
- **AC-6** — Dado **nenhum** envio programado, Quando abro Hoje, Então vejo o **estado vazio** ("Nenhum envio
  programado…") em vez da lista. Durante o carregamento, **esqueletos** (sem spinner de tela cheia).
- **AC-7** — O indicador **"Programadas"** mostra a **contagem** de agendamentos futuros; o cabeçalho mostra a
  **data por extenso** (America/Sao_Paulo) e o selo "Sistema ok".

**Tela Contatos (DESIGN §6)**
- **AC-8** — Dado contatos cadastrados, Quando abro **Contatos**, Então vejo a lista (**tabela** ≥640px /
  **cartões** <640px) com nome, telefone, **selo de consentimento** e **selo de descadastro**.
- **AC-9** — Posso **criar** um contato (`POST /contatos`) e **editar** (`PATCH /contatos/{id}`); erro de
  validação do backend (ex.: telefone inválido) é mostrado de forma legível (não quebra a tela).
- **AC-10** — Posso **registrar consentimento** (`POST /{id}/consentimento`) e **descadastrar**
  (`POST /{id}/descadastrar`), com confirmação; a lista reflete a mudança.
- **AC-11 (import)** — Posso **importar** um CSV/XLSX (`POST /contatos/importar`) e ver o **relatório**
  (total / criados / erros).

**Qualidade (gate executável)**
- **AC-12** — `npm run lint`, `npx tsc --noEmit` e `npm run build` passam (tipos estritos, sem erro).

## Tabela de bordas (oráculo do smoke)
| Caso | Esperado |
|---|---|
| Tema escuro no 1º load | sem flash claro; `data-theme="dark"` antes de pintar |
| "Seguir o sistema" + SO troca p/ escuro | tema reage em tempo real |
| Hoje sem agendamentos | estado vazio, não lista vazia |
| Agendamento com recorrência | ícone de recorrência na linha |
| Agendamento de grupo | mostra o grupo (não "contato") |
| Mais de 8 futuros | lista corta em 8 + "Ver todos (N)" |
| Contato sem consentimento | selo "sem consentimento" visível |
| Import com 1 linha inválida | relatório total/criados/erros ≠ 0 |
| Rota do app sem token | redireciona a /login |
| <640px | barra inferior; cartões em Contatos |

## Fora de escopo (vinculante — ver product.md)
Nova mensagem (0007); Agenda, Sugestões, Modelos, Histórico, Conversas, Base de respostas, Regras, Saúde,
Configurações completas; indicadores de gasto/entregues/não-enviadas; persistência de tema no backend;
auto-refresh (30s); notificações push; test runner de frontend (Vitest/Playwright).
