---
name: design-pwa-telas
description: Design da spec 0006 — fundação do frontend (tokens, tema claro/escuro/sistema, shell responsivo) + telas Hoje e Contatos, sobre a stack existente (Next.js 16, CSS com tokens, lib/api.ts). Alternativas, trade-offs, riscos; decide ADR 0010.
---

# Design: PWA — telas v1 (spec 0006)

> **Contrato visual:** DESIGN-DASHBOARD.md (aprovado pelo cliente 29/10/2026). **Stack a respeitar:** Next.js 16
> app router + React 19, **CSS puro com tokens** (`app/globals.css`), `lib/api.ts` (fetch+Bearer), guarda via
> `/auth/me`, PWA (`manifest.webmanifest`+`sw.js`). **Sem dependência nova** (§4).

## Solução proposta

### Fundação (a base de tudo)
- **Tokens (claro + escuro)** em `app/globals.css` conforme DESIGN §2: cores de superfície/texto/borda +
  **selos de status** (Agendada, Entregue, Aguardando, Não enviada, Cancelada). Hoje só há tokens claros;
  acrescentar o conjunto escuro sob `[data-theme="dark"]` e as classes de selo. Nenhuma cor fixa fora dos tokens.
- **Tema claro/escuro/sistema** (DESIGN §10): atributo `data-theme="light|dark"` no `<html>`; "sistema" **remove**
  o atributo e cai no `@media (prefers-color-scheme)`. Persistência em **localStorage** (`lib/tema.ts`) + **script
  inline no `<head>`** (via `app/layout.tsx`) que aplica o tema **antes da 1ª pintura** (sem flash). `theme_color`
  do PWA acompanha o tema (meta com `media`). Persistir no backend fica adiado (sem endpoint).
- **Fonte Inter** via `next/font/google` (self-hosted no build — sem fetch externo em runtime, ok p/ PWA/CSP).
- **Shell responsivo** (`components/AppShell`): **menu lateral** fixo ≥1024px / **barra inferior** <640px, com
  **Hoje** e **Contatos** ativos e os demais itens do DESIGN §4 visíveis porém **desabilitados ("em breve")**.
  Topo com conta + "Sair" + seletor de tema (ícone sol/lua).
- **Guarda de auth** reutilizável (`components/GuardaAuth` ou hook): extrai a lógica de `painel/page.tsx`
  (checa token → `/auth/me` → redireciona a `/login`). As telas ficam em um grupo `app/(app)/*` guardado.
- **Componentes mínimos**: `Selo` (status com cor+texto — DESIGN §2/§8), `EstadoVazio`, `Esqueleto` (loading
  sem spinner de tela cheia), `Cartao`. Ícones em **SVG inline** (traço), sem lib.
- **Dados**: estender `lib/api.ts` com funções tipadas por recurso reusando o fetch+Bearer:
  `listarAgendamentos({status,limit})`, `listarContatos(...)`, `criarContato`, `atualizarContato`,
  `descadastrarContato`, `registrarConsentimento`, `importarContatos`. Tipos espelham os schemas do backend.

### Tela Hoje (`app/(app)/hoje`, DESIGN §5)
- **Cabeçalho**: "Hoje", data por extenso (America/Sao_Paulo) + selo de saúde **estático "Sistema ok"** (v1 —
  sem endpoint).
- **Indicadores**: só **"Programadas"** (contagem de agendamentos futuros `status=aprovado`); os outros
  (Entregues no mês, Não enviadas, Gasto) renderizados como **"—" / em breve**.
- **Envios programados**: `GET /agendamentos?status=aprovado`, filtra `executar_em` futuro, ordena cronológico,
  **limite 8** (+ "Ver todos (N)" inerte por ora). Colunas: **data `dd/mm` (peso 500) sobre `HH:mm`**
  (secundário; `dd/mm/aa` se outro ano); **contato** (resolvido via `listarContatos` → mapa `id→nome`; grupo
  quando for grupo) com **ícone de recorrência** quando `recorrencia` != null; **modelo** (por ora o `modelo_id`
  ou "modelo" — sem GET /modelos); **selo de status**. Estado vazio (DESIGN §5) + ação "Nova mensagem"
  **desabilitada ("em breve")**.
- Carregamento com **esqueletos**; sem auto-refresh no v1 (DESIGN pede 30s → adiar, anotar).

### Tela Contatos (`app/(app)/contatos`, DESIGN §6)
- **Lista** (`GET /contatos`): **tabela** ≥640px / **cartões** no celular; colunas nome, telefone (mascarado a
  exibir conforme padrão), **selo de consentimento** e **selo de descadastro**; busca/paginação simples (o
  endpoint tem `limit/offset`).
- **Criar/editar**: formulário (`POST` / `PATCH /{id}`), validação espelhando o backend (telefone E.164).
- **Consentimento / descadastro**: ações `POST /{id}/consentimento` e `POST /{id}/descadastrar` com confirmação.
- **Importar**: upload de CSV/XLSX (`POST /contatos/importar`) com **relatório total/criados/erros**.

## Alternativas consideradas
| Opção | Prós | Contras | Veredito |
|---|---|---|---|
| **CSS com tokens (atual)** | zero dep; já no repo; controle total | mais CSS à mão | **Escolhida** (§4/consistência) |
| Tailwind / UI lib | rápido | dep nova (§4); troca de padrão | Descartada |
| **Tema via data-theme + script pré-pintura** | sem flash; simples; DESIGN §10 | script inline no head | **Escolhida** |
| Tema só por `prefers-color-scheme` | trivial | não permite forçar claro/escuro | Descartada |
| **next/font (Inter self-hosted)** | sem fetch externo; PWA/CSP ok | — | **Escolhida** |
| `<link>` Google Fonts | fácil | fetch externo em runtime | Descartada |
| **Nova mensagem agora** | ação principal | exige GET /modelos (não existe) | **Adiada (0007)** |

## Trade-offs e riscos
- **Lacunas de backend** (modelos/gasto/saúde/histórico): a UI mostra stubs/"em breve" — risco de parecer
  incompleta; mitigado deixando claro na tela e nos non-goals. Evita inventar endpoints fora de escopo.
- **Contraste (WCAG AA, DESIGN §2)**: validar os pares texto/fundo usados (claro e escuro); no v1 ao menos
  checagem manual (checagem automática no CI fica como follow-up).
- **Token no localStorage** (padrão herdado da Fase 1): mantém-se; endurecimento (cookie HttpOnly) fora de
  escopo, mas **não ampliar a superfície** (não logar token, não expor em URL).
- **Sem test runner no frontend**: AC verificados por `tsc`/`eslint`/`build` + **smoke de navegador**
  (webapp-testing). Adicionar Vitest/Playwright seria dep nova (§4) → decisão para outra spec.
- **PWA/offline**: não mexer no `sw.js` além do necessário; telas são client-side com fetch autenticado.

## Decisões irreversíveis (→ ADR 0010 proposto)
- **ADR 0010 — Frontend: tema (data-theme claro/escuro/sistema, script pré-pintura, persistência local),
  sistema de tokens e shell de navegação, sem dependência nova.** Define como todo o frontend é estilizado e
  navegado daqui pra frente (caro de reverter: todas as telas seguintes herdam esses padrões).

## Questões para /clarificar (gate da spec)
1. Import CSV/XLSX no v1 de Contatos? (proposta: sim.)
2. Indicadores do Hoje = só "Programadas" + stubs? (proposta: sim.)
3. Selo de saúde estático "Sistema ok" até haver endpoint? (proposta: sim.)
