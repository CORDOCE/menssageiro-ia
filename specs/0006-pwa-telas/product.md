---
name: product-pwa-telas
description: Product brief da spec 0006 — primeiras telas do PWA (Fase 5). Fundação do frontend (tokens, tema, shell) + telas Hoje e Contatos, sobre os endpoints já existentes. Nova mensagem e demais telas ficam para specs seguintes.
---

# Product: PWA — telas v1 (Fase 5, spec 0006)

## Problema
O backend e o worker funcionam (Fases 1–5, em produção), mas o **frontend é só login + um painel
placeholder** (`app/painel`: "As telas chegam nas próximas fases"). O operador **não tem interface** para ver
o que está programado nem para gerenciar contatos — tudo depende de chamada de API. A Fase 5 começa a
construir o PWA conforme o **DESIGN-DASHBOARD.md** (layout aprovado pelo cliente em 29/10/2026).

Para quem: o **operador** (ex.: Pedro), que precisa ver os envios programados e manter a base de contatos pela
tela — no computador (trabalho longo) e no celular (ações rápidas).

## Métrica de sucesso
Observável por smoke de navegador (frontend rodando contra o backend) + build/tipos verdes:
1. O operador autenticado abre o app e vê a tela **Hoje** com os **envios programados** reais (de
   `GET /agendamentos`), com data/hora, contato, status e marca de recorrência.
2. O operador **gerencia contatos** pela tela **Contatos**: lista, cria, edita, registra consentimento,
   descadastra e **importa** uma planilha — tudo sobre os endpoints já existentes.
3. A **troca de tema** (claro/escuro/sistema) funciona e **não pisca** (tema certo antes da 1ª pintura).
4. O app é **responsivo**: menu lateral no computador, barra inferior no celular.

## Goals
- **Fundação do frontend**: sistema de **tokens** (claro + escuro) conforme DESIGN §2; **troca de tema**
  (claro/escuro/sistema) com persistência local e sem flash; **shell de navegação** responsivo; fonte **Inter**;
  biblioteca mínima de componentes (selo de status, cartão, estado vazio, esqueleto); guarda de autenticação
  reutilizável. Tudo com os padrões já no repo (CSS com tokens, `lib/api.ts`), **sem dependência nova**.
- **Tela Hoje** (tela inicial — DESIGN §5): cabeçalho, indicador "Programadas", lista de **envios programados**
  (futuros, cronológica) e estado vazio.
- **Tela Contatos** (DESIGN §6): lista (tabela/cartões), criar/editar, consentimento/descadastro e importação.

## Non-goals (vinculante)
- **Nova mensagem** (assistente de criar agendamento) → **spec 0007** (depende de um `GET /modelos` que ainda
  não existe).
- **Agenda, Sugestões, Modelos, Histórico, Conversas, Base de respostas, Regras, Saúde do sistema,
  Configurações completas** → specs/fases seguintes.
- **Indicadores que dependem de dados inexistentes** (Gasto no mês, Entregues no mês, Não enviadas, selo de
  saúde real) → ficam **stub/adiados** até haver endpoint (gasto/saúde/histórico de envios).
- **Persistir o tema no perfil do backend** → adiado (sem endpoint); v1 usa localStorage.
- **Notificações push** (DESIGN §9) → fora.

## Dependências / restrições
- Reusa os endpoints existentes (auth, contatos, agendamentos). **Nenhum endpoint novo** no backend nesta spec.
- **Sem npm novo** (qualquer dependência exigiria aprovação §4): CSS puro com tokens, `next/font` para Inter,
  ícones em SVG inline.

## Questões para /clarificar (gate da spec)
1. **Import CSV/XLSX** entra no v1 de Contatos? (proposta: sim — endpoint `POST /contatos/importar` pronto.)
2. Indicadores do **Hoje** no v1 = só **"Programadas"** (os outros como "—"/stub até haver endpoint)? (proposta: sim.)
3. Selo de **saúde** no Hoje = estático "Sistema ok" até existir endpoint de saúde? (proposta: sim.)
