# ADR 0010 — Frontend: tema (claro/escuro/sistema), sistema de tokens e shell de navegação

- **Status:** aceito
- **Data:** 2026-11-04
- **Contexto da feature:** spec `0006-pwa-telas` (Fase 5 — primeiras telas do PWA). Escopo v1 (Fundação + Hoje +
  Contatos) e tier Arquitetural aprovados por Jefferson (2026-11-04).
- **Aprovação:** mudança de frontend (não toca regras de envio/IA). O **layout** foi aprovado pelo cliente em
  29/10/2026 (DESIGN-DASHBOARD.md). Esta ADR fixa as decisões de **arquitetura do frontend**, que todas as telas
  seguintes vão herdar — por isso são caras de reverter.

## Contexto
O frontend era só login + painel placeholder. A Fase 5 começa a construí-lo e precisa fixar, antes das telas,
três fundações caras de trocar depois:
1. **Como estilizar** (sistema de cores/tema) — o DESIGN §2/§10 exige claro, escuro e "seguir o sistema",
   sem "piscar" o tema errado.
2. **Como navegar** (shell responsivo) — menu lateral no computador, barra inferior no celular (DESIGN §4).
3. **Com quais dependências** — o repo evita libs novas sem aprovação (§4).

## Decisão
1. **Estilo = CSS puro com tokens** (mantém o padrão já em `app/globals.css`), **sem Tailwind/UI lib**. Todas as
   cores saem de **tokens** (DESIGN §2), incluindo os **selos de status**; nenhuma cor fixa no código. Isso deixa
   uma futura identidade do cliente trocar só `--cor-primaria` (e o ícone) sem mexer no resto.
2. **Tema por `data-theme`**: atributo `data-theme="light|dark"` no `<html>`; **"seguir o sistema" remove o
   atributo** e usa `@media (prefers-color-scheme)`, reagindo em tempo real à troca do aparelho. A escolha é
   persistida em **localStorage** e aplicada por um **script inline no `<head>`** antes da primeira pintura
   (evita o flash de tema errado). O `theme_color` do PWA acompanha o tema ativo. **Persistir no perfil do
   backend fica adiado** (não há endpoint hoje) — decisão consciente, reversível (é só adicionar a sincronização
   depois).
3. **Fonte Inter via `next/font/google`** (self-hosted no build): sem `<link>` externo em runtime, compatível
   com PWA/CSP. **Ícones em SVG inline** (traço), sem biblioteca de ícones.
4. **Shell responsivo** reutilizável: menu lateral fixo ≥1024px / barra inferior <640px; itens do DESIGN §4,
   com **Hoje** e **Contatos** ativos e os demais **desabilitados ("em breve")**. **Guarda de autenticação**
   extraída para um componente/hook reutilizável (token → `/auth/me` → redireciona), usada por um grupo de rotas
   `app/(app)/*`.

## Consequências
- **Sem dependência nova** no frontend (§4 respeitado) — só CSS, `next/font` (nativo do Next) e SVG.
- **Todas as telas seguintes** (Agenda, Nova mensagem, Modelos, Conversas, Configurações…) herdam tokens, tema,
  shell e guarda — consistência e menos retrabalho.
- **Acessibilidade**: contraste dos pares usados deve passar WCAG AA (DESIGN §2); no v1 ao menos checagem manual
  (automação no CI fica como follow-up).
- **Verificação**: sem test runner no frontend; AC validados por `eslint` + `tsc --noEmit` + `build` + **smoke de
  navegador** (skill `webapp-testing`). Adotar Vitest/Playwright seria dep nova (§4) → outra spec.
- **Fora desta ADR / adiado:** persistência de tema no backend; auto-refresh do Hoje (30s, DESIGN §5); endurecer
  o armazenamento do token (cookie HttpOnly); indicadores que dependem de gasto/saúde/histórico (sem endpoint).
