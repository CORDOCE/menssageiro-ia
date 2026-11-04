# ADR 0008 — Disparo do worker: configuração runtime, idempotência at-most-once e janela de envio

- **Status:** aceito
- **Data:** 2026-11-04
- **Contexto da feature:** Fase 4 — núcleo do disparo (spec `0004-worker-agendamentos`); decisões fechadas na
  sabatina `/clarificar` de 2026-11-04.
- **Aprovação:** as **regras de envio** já foram aprovadas no **ADR 0005** (CLAUDE.md §4). Este ADR registra as
  decisões de **implementação/schema** da Fase 4 — aprovadas por Jefferson no `/clarificar` (2026-11-04).

## Contexto
A Fase 4 implementa o caminho de produção de envio (ADR 0005 + BRIEFING §9/§10.3). Três pontos precisavam ser
fechados antes das migrations, por serem caros de reverter:
1. **Onde moram os controles de envio** (janela, `limite_diario`, `limite_por_contato_dia`, pausa): o BRIEFING
   tem um conflito — §4.5 fala em env `LIMITE_DIARIO`; §9 coloca `limite_diario` na tabela `configuracoes`.
2. **Qual a garantia de idempotência** concreta do worker ao expandir grupo em envios (a ADR 0005 fixou a trava
   `UNIQUE(agendamento_id, contato_id)`, mas não a ordem reservar/enviar nem o comportamento após crash).
3. **Como representar e comparar a janela de horário** (formato e fuso).

## Decisão
1. **`configuracoes` (linha única) é a fonte runtime.** Janela, `limite_diario`, `limite_por_contato_dia` e
   `envios_pausados` vivem no banco e são lidos **a cada ciclo** do worker (§5.6), para o operador mudar **sem
   redeploy**. A env `LIMITE_DIARIO` (padrão 200) vira, no máximo, **semente** do default na criação da linha.
   Resolve o conflito BRIEFING §4.5 × §9 **a favor da tabela**. `limite_por_contato_dia` nasce `NULL` = **sem
   limite** (o worker só aplica se o operador configurar).
2. **Idempotência at-most-once por `(agendamento, contato)`.** O worker **reserva antes de enviar**:
   `INSERT INTO envios(agendamento_id, contato_id) … ON CONFLICT DO NOTHING` (apoiado no índice único
   `UNIQUE(agendamento_id, contato_id)` da ADR 0005) e só então chama a Meta. Linha já existente após reinício
   **nunca** é reenviada — `§5.2` (nunca enviar duas vezes ao mesmo contato) **tem precedência sobre a entrega**.
   Consequência consciente: uma linha `enviando` sem `wamid` após crash entre reservar e enviar fica **ambígua
   e não é reenviada**, ficando **visível ao operador** (em vez de arriscar duplicar).
3. **`janela_envio` como JSONB** `{"dias":[…],"inicio":"HH:MM","fim":"HH:MM"}` (`dias` em `weekday()`, 0=seg),
   comparado sempre em **America/Sao_Paulo** (`zoneinfo`), com `timestamptz` no banco (§8). **reagenda** (fora da
   janela) → próximo início de janela válida; **adia** (limite diário batido) → início da janela do **dia
   seguinte**. Ambos mantêm `aprovado` e só mexem em `executar_em` (ADR 0005 §4).
4. **Colunas inertes de recorrência** (`agendamento_pai_id`, `recorrencia`) entram **já** na migração 0004, sem
   lógica — seguindo o princípio da ADR 0005 ("definir antes das migrations → sem retrabalho"); a expansão e o
   `UNIQUE(agendamento_pai_id, executar_em)` vêm na spec 0005.

## Consequências
- **Schema (migração 0004):** nova tabela `configuracoes` (linha única, semeada); `agendamentos` com o schema do
  ADR 0005 + colunas inertes; **FK** `envios.agendamento_id → agendamentos` (preservando o índice único parcial).
- **Operabilidade:** pausar envios / ajustar janela e limites é mudança de dado (sem deploy); o env vira só default.
- **Confiabilidade:** zero duplicata por contato por agendamento, mesmo com reinício no meio do lote; o preço é a
  rara mensagem não enviada (linha órfã), que é exposta ao operador — não silenciada.
- **Fora deste ADR:** recorrência (RRULE / `python-dateutil`) e anexos (cabeçalho DOCUMENT) → specs seguintes;
  resolução fina do `aguardando_decisao` por tela do PWA → Fase 5.
