# Spec — 0021 Tela "Saúde do sistema" + `GET /admin/health/deep` (dívida A2 / BRIEFING §12)

> Tier **Pequeno** (spec + tasks). Endpoint de **leitura** + 1 tela; **sem migração** (lê dados que já
> existem: `saude`, `envios`, `agendamentos`). Não toca regra de envio nem IA. Fecha o gap deixado
> consciente na Fase 1 (`specs/0001` listou `/admin/health/deep` como "fase posterior" — `main.py:3`).

## Contexto / por que
O §12 do BRIEFING prevê a tela "Saúde do sistema" e o endpoint `/admin/health/deep`. A observabilidade
foi atendida por outro caminho (0017 Sentry + 0019 alertas de agregação), mas a **visão operacional no
app** nunca foi entregue — o operador não tem como, pela UI, ver se o worker está vivo, como foram os
envios do dia e quanto gastou no mês. Esta spec entrega essa visão com o que já há no banco.

## Escopo (v1) — decisão de escopo aprovada por Jefferson (2026-11-12)
`GET /admin/health/deep` (autenticado) devolve um retrato de saúde, e a tela `(app)/saude` o exibe:
1. **banco** — `SELECT 1` → `ok`/`erro` (não derruba o endpoint).
2. **worker** — lê `saude.ultimo_ciclo_em`: `vivo` se o último ciclo foi há **≤ 5 min**; `parado` se
   mais velho; `desconhecido` se a tabela `saude` está vazia (worker nunca rodou). Inclui `ultimo_ciclo_em`
   e os segundos desde o último ciclo.
3. **envios_hoje** — contagem por status (dicionário `status → n`) dos `envios` do **dia** (America/Sao_Paulo).
4. **taxa_falha_hoje** — `falhas/tentativas` do dia com a definição da 0019 (`falhas = falhou + aguardando_decisao`;
   `tentativas = enviado + entregue + lido + aguardando_retry + falhas`), com `percentual`.
5. **fila** — `COUNT` de `agendamentos` com `status = 'aprovado'` e `executar_em <= now` (vencidos à espera do worker).
6. **gasto_mes_estimado** — **estimativa** (não há coluna de custo; só `pricing` JSONB): nº de envios
   com status ∈ {`enviado`,`entregue`,`lido`} no **mês** (SP) × tarifa UTILITY (`R$ 0,035`, §4.4),
   em `BRL`, com o rótulo de que é **estimado** e a base do cálculo.

## Suposições (explícitas, reversíveis)
- **S1** — "dia"/"mês" = calendário **America/Sao_Paulo** (exibição §8); fronteira calculada no backend.
- **S2** — tarifa UTILITY fixa `R$ 0,035` como constante (`core/config.py`), reversível; a precisão real
  (via objeto `pricing` da Meta) fica para a Fase 0.
- **S3** — limiar "worker parado" = **5 min** (BRIEFING §12), constante no código.

## Critérios de aceite (Given/When/Then)
- **AC-1 (authz)** — Dado nenhuma sessão, Quando `GET /admin/health/deep`, Então **401** (dependência de auth do router).
- **AC-2 (retrato)** — Dada uma sessão válida, Quando `GET /admin/health/deep`, Então **200** com as 6 seções
  (banco, worker, envios_hoje, taxa_falha_hoje, fila, gasto_mes_estimado).
- **AC-3 (checagem de banco degradável)** — Dado que o `SELECT 1` da checagem lança, Quando `_checar_banco` roda,
  Então devolve `banco = "erro"` (com `rollback`) **sem propagar** — a verificação de banco não derruba o endpoint
  por si. (Banco totalmente indisponível ainda falha a sessão/queries, como em qualquer endpoint autenticado;
  provado no nível da função, não exercitando um Postgres morto.)
- **AC-4 (worker vivo/parado)** — Dado `ultimo_ciclo_em` há ≤ 5 min, Então `worker.status = "vivo"`; dado há > 5 min,
  Então `"parado"`.
- **AC-5 (worker desconhecido)** — Dada a tabela `saude` vazia, Então `worker.status = "desconhecido"` (sem erro).
- **AC-6 (envios do dia por status)** — Dados 1 `entregue`, 1 `falhou`, 1 `enviado` hoje (SP) e 1 `entregue` **ontem**,
  Então `envios_hoje = {entregue:1, falhou:1, enviado:1}` (ontem não entra).
- **AC-7 (taxa de falha do dia)** — Dados 4 tentativas do dia sendo 1 `falhou` e 1 `aguardando_decisao`,
  Então `taxa_falha_hoje.percentual = 50.0`; sem envios no dia, Então `0.0` (sem divisão por zero).
- **AC-8 (fila)** — Dados 2 agendamentos `aprovado` vencidos e 1 `aprovado` futuro e 1 `cancelado` vencido,
  Então `fila = 2`.
- **AC-9 (gasto do mês estimado)** — Dados 3 envios `entregue`/`lido`/`enviado` no mês (SP) e 1 `falhou` no mês,
  Então `gasto_mes_estimado.valor = 0.105` (3 × 0,035), `moeda = "BRL"`, `estimado = true` (o `falhou` não conta).
- **AC-10 (tela)** — Dada a sessão, Quando abro `(app)/saude`, Então vejo os cartões das 6 seções com rótulos
  legíveis; se o deep falha, mensagem legível (sem stack/PII); `401 → login`; item "Saúde" no `AppShell`.

## Fora de escopo (vinculante)
- **Token Meta válido** e **qualidade do número** (§12) → dependem de credenciais Meta / Fase 0 → follow-up.
- Gasto **real** por `pricing` da Meta; histórico/gráficos temporais; auto-refresh/polling; alertas (já na 0017/0019).
- Qualquer escrita; `/admin/health/deep` é só leitura.

## Arquivos (previsto)
- Backend: `api/admin_health.py` (router `GET /admin/health/deep`, `dependencies=[Depends(usuario_atual)]`),
  `schemas/saude.py` (modelos de resposta), registro em `main.py`, `core/config.py` (`tarifa_utility_brl`).
  Testes: `tests/test_admin_health.py` (AC-1..AC-9).
- Frontend: `app/(app)/saude/page.tsx` (+ teste), `lib/api.ts` (`obterSaude` + tipos), `components/AppShell.tsx`
  (item "Saúde"), `components/icones.tsx` (`IconeSaude`). Teste de componente (AC-10).
