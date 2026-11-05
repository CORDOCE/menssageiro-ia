---
name: tasks-pwa-telas
description: Quebra de tarefas da spec 0006 — fundação + Hoje + Contatos. Mapeia cada task aos AC; gate = eslint + tsc --noEmit + build + smoke de navegador.
---

# Tasks: PWA — telas v1 (spec 0006)

Gate por task: `npm run lint` + `npx tsc --noEmit` + `npm run build` verdes; fluxo exercido no smoke de
navegador (webapp-testing) contra `npm run dev` + backend local.

## 1. ADR 0010 (fundação — decisão irreversível) ✅ escrito
- `docs/decisoes/0010-frontend-tema-tokens-shell.md`.

## 2. Tokens + tema (AC-1, AC-2)
- `app/globals.css`: conjunto de tokens **escuro** sob `[data-theme="dark"]` + `@media (prefers-color-scheme:dark)`
  sem atributo; classes de **selo** por status (DESIGN §2). Tudo via tokens.
- `lib/tema.ts`: ler/gravar preferência (localStorage), aplicar `data-theme`.
- `app/layout.tsx`: **script inline no `<head>`** (pré-pintura) + `next/font` Inter + `theme_color` por tema.
- `components/SeletorTema.tsx`: Claro / Escuro / Seguir o sistema.

## 3. Shell + guarda de auth (AC-3, AC-4)
- `components/GuardaAuth.tsx` (ou hook): extrai a lógica de `app/painel/page.tsx` (token → `/auth/me` → redireciona).
- `components/AppShell.tsx`: menu lateral ≥1024px / barra inferior <640px; itens Hoje/Contatos ativos, demais
  "em breve"; topo com conta, Sair, seletor de tema.
- Grupo de rotas `app/(app)/layout.tsx` aplicando GuardaAuth + AppShell. (Reaproveitar/retirar o `painel` antigo.)

## 4. Cliente de dados (suporta 5–7)
- `lib/api.ts`: `listarAgendamentos`, `listarContatos`, `obterContato`, `criarContato`, `atualizarContato`,
  `descadastrarContato`, `registrarConsentimento`, `importarContatos` — tipos espelhando os schemas do backend.

## 5. Componentes base
- `components/{Selo,EstadoVazio,Esqueleto,Cartao}.tsx`; ícones SVG inline (incl. recorrência).

## 6. Tela Hoje (AC-5, AC-6, AC-7)
- `app/(app)/hoje/page.tsx`: cabeçalho (data por extenso + "Sistema ok"); indicador Programadas (contagem de
  futuros) + stubs "—"; lista de envios programados (ordem cronológica, data/hora empilhada, contato resolvido
  via `listarContatos`, ícone de recorrência, selo, limite 8, "Ver todos (N)"); estado vazio; esqueletos.

## 7. Tela Contatos (AC-8..AC-11)
- `app/(app)/contatos/page.tsx`: lista tabela/cartões + selos consentimento/descadastro.
- criar/editar (form) `POST`/`PATCH`; consentimento/descadastro com confirmação; import CSV/XLSX + relatório.

## 8. Gates + PR (AC-12; DoD §9)
- `npm run lint` + `npx tsc --noEmit` + `npm run build` verdes; smoke de navegador cobrindo a tabela de bordas.
- `/revisar` → `/seguranca` → `/validar`; CI (`frontend` job) verde; PR p/ `develop`. STATE.md (/handoff).
