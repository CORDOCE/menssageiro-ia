# Clarificar — 0020 Reenvio automático de envios que falharam

> Resumo de entendimento (/clarificar). **Ainda NÃO é spec.** Feature aberta a partir da 0019
> (que deixou "reenvio no nível da mensagem" fora de escopo). Alimenta `product.md`/`design.md`/
> `spec.md` quando o escopo fechar e a aprovação §4 for dada.

## Motivação
Hoje um `envio` que vira `falhou` é **terminal** — o worker não o reprocessa (invariante §5.2;
`disparo.py:345,357-367`). Se a falha foi um **blip de conexão** nosso→Meta (internet/API), a mensagem
agendada simplesmente não sai. Esta feature faz o worker **retentar** esse tipo de falha.

## Tier e governança
- **Tier Arquitetural** — altera a invariante **§5.2** (falha deixa de ser sempre terminal) → exige **ADR**.
- Mexe em **regra de envio** → **§4 exige aprovação explícita do Jefferson** da regra final antes de implementar.
- Migração (aditiva) → **/migracao** com downgrade.
- Toca a Cloud API / códigos de erro da Meta → **/meta-whatsapp** no design.

## Restrições fixas (invariantes — não são perguntas)
- **Idempotência §5.2 preservada:** continua 1 envio por `(agendamento, contato)`; reenvio é re-tentar a
  mesma unidade, nunca criar envio duplicado.
- **Reavaliar elegibilidade no reenvio:** consentimento + descadastro (§5.4/§5.9) e janela/template UTILITY
  (§5.3) checados **no momento de cada tentativa** — contato que saiu nesse meio-tempo não recebe.
- **Não furar o teto por agendamento (0016)** nem limites por contato/dia: retry conta como envio.
- **Instrumentação não derruba o fluxo** (§5.8).

## Decisões /clarificar (2026-11-11, Jefferson)
- **Q1 — escopo:** reenviar **só falhas transitórias de envio** (erro temporário/limite 429/5xx que não se
  recuperou nos 3 tiros HTTP do `whatsapp_client`). **NÃO** reenviar: erro definitivo (número inválido, não é
  usuário WhatsApp, descadastrado, template rejeitado) nem falha de **entrega** reportada pela Meta via webhook
  (a Meta já retenta a entrega).
- **Q2 — cadência:** **até 3 reenvios** com intervalo crescente curto (ex.: +5min, +15min, +1h); esgotou →
  marca falha **definitiva** + alerta. Total ~1h20 (mensagem agendada é sensível ao tempo — sem retry de horas).
- **Q3 — modelo de dados [CONFIRMADO]:** reusar a **mesma linha** em `envios` — adicionar `tentativas`
  (contador), `proxima_tentativa_em` (timestamptz) e status novo `aguardando_retry`. Mantém 1 linha por
  `(agendamento, contato)` (§5.2 intacta); migração só adiciona colunas (downgrade trivial).
- **Q4 — classificar transitória vs definitiva [CONFIRMADO]:** reenvia quando foi **exaustão de transporte
  429/5xx** (sem resposta aplicacional da Meta) **OU** código em **allowlist curta** de erros Meta conhecidos
  como temporários (montada com **/meta-whatsapp** + doc oficial; §1 — sem inventar código). Todo o resto =
  definitivo (nunca reenvia número inválido/descadastrado/template rejeitado).
- **Q5 — ao esgotar as 3 tentativas [CONFIRMADO]:** vai para **decisão humana** (não só `falhou`+alerta).
- **Q5b — onde o humano decide [CONFIRMADO]:** estado/ação **por envio** — o envio que esgotou vira
  `aguardando_decisao` **na própria linha do envio** + ação manual nova "reenviar este envio" (reabre a mesma
  linha p/ nova tentativa; coerente com Q3). Custo: endpoint + botão novos (tasks da spec). Descartada a opção de
  reusar o `aguardando_decisao` do agendamento (idempotência `(agendamento, contato)` bloquearia re-disparar só o
  contato que falhou — `disparo.py:331-346` — e em grupo pausaria o agendamento todo).
- **Q6 — `aguardando_retry` na taxa de falha da 0019 [CONFIRMADO]:** conta como **tentativa em trânsito** — entra
  no **denominador** (tentativas), **não** no numerador (falhas); só vira falha se esgotar (`falhou`). Exige
  incluir `aguardando_retry` na definição de "tentativa" da 0019 (`_CONTAM_LIMITE`).
- **Q7 — at-most-once [CONFIRMADO]:** at-most-once estrito (só reenvia certeza de não-entrega). ADR 0014.
- **Q8 — `aguardando_decisao` na taxa da 0019 [CONFIRMADO]:** **conta como falha** (não-entrega real aguardando
  humano).
- **Q9 — falha ambígua (5xx/timeout/órfão) [CONFIRMADO]:** → `aguardando_decisao` (humano decide reenviar ciente
  do risco), **sem** auto-retry.
- **Ataque ao órfão `enviando` [design]:** (a) client captura `ConnectError`→retentável e `TimeoutException`→
  ambíguo; (b) **sweep** no worker recolhe `enviando` sem `wamid` preso >15min (configurável) → `aguardando_decisao`
  + alerta. Fecha bug pré-existente (hoje essas exceções propagam e deixam órfão; `grep` confirmou sem reaper).

## A resolver no design.md (consequências técnicas, não perguntas de produto)
1. **Como distinguir "transitória" de "definitiva" no momento da falha.** Hoje `WhatsappError` agrupa as duas
   (exaustão de 429/5xx **e** 4xx aplicacional) e grava só `erro_codigo` string (`disparo.py:360`). Precisa
   marcar na falha se foi transporte-esgotado (retentável) vs aplicacional (definitivo). Construir a regra com
   **/meta-whatsapp** + doc oficial da Meta (anti-alucinação §1: não inventar códigos).
2. **Mecânica no worker:** a cada ciclo, selecionar `status='aguardando_retry' AND proxima_tentativa_em<=agora`
   com `FOR UPDATE SKIP LOCKED` (padrão §5.2), reavaliar elegibilidade e reenviar; incrementar `tentativas`;
   no teto de tentativas → `falhou` + auditoria/alerta.
3. **Interação com a 0019 (alertas de agregação) — DEPENDÊNCIA (Q6):** `aguardando_retry` conta como **tentativa
   em trânsito** (denominador), **não** como falha. Como a 0019 entra em produção **antes** da 0020 (e o status
   `aguardando_retry` só nasce aqui), **uma task da 0020 é atualizar a definição de "tentativa" da 0019** —
   incluir `aguardando_retry` em `_CONTAM_LIMITE`. Não altera a 0019 agora; é follow-up gravado quando a 0020 for
   implementada.
4. **Interação com teto 0016 / limites:** cada reenvio conta no teto; retry não pode ultrapassar.

## ❓ Perguntas em aberto (/clarificar) — responder uma por vez, na ordem
> Retomar com **/clarificar**. Cada pergunta traz a resposta **recomendada** e por quê. Ao responder,
> mover a decisão para a seção "Decisões /clarificar" acima e seguir para a próxima.

- ~~**Q3 — Modelo de dados (ADR).**~~ ✅ **RESOLVIDA:** reusar a linha de `envios`. (ver Decisões acima)
- ~~**Q4 — Classificar transitória vs definitiva.**~~ ✅ **RESOLVIDA:** transporte 429/5xx + allowlist curta.
- ~~**Q5 — Ao esgotar as 3 tentativas.**~~ ✅ **RESOLVIDA:** vai para decisão humana (não só `falhou`+alerta).

- ~~**Q5b — Onde o humano decide?**~~ ✅ **RESOLVIDA:** estado/ação por envio. (ver Decisões acima)
- ~~**Q6 — `aguardando_retry` na taxa da 0019.**~~ ✅ **RESOLVIDA:** tentativa em trânsito, não falha.

- ~~**Q7 — Entrega dupla / at-most-once (ADR).**~~ ✅ **RESOLVIDA:** at-most-once estrito — só reenvia com certeza
  de não-entrega (429/limite + conexão pré-request + allowlist curta); `5xx`/timeout fica `falhou`. Formalizada no
  **ADR 0014** e no `design.md`.

### Gates/processo
- **G1 — Aprovação §4** do Jefferson da regra de envio — ✅ **DADA** ("ok", 2026-11-11). Registrar no ADR.
- **G2 — Ordem de git:** ✅ **FEITO** — spec 0019 commitada em `feat/0019-alertas-agregacao` (`f83cac5`);
  scaffold da 0020 em branch própria `feat/0020-reenvio-automatico` (`d70c9b7`) a partir de `develop`.

## Fora de escopo (vinculante)
- Reenvio de **falha de entrega** (webhook) e de **erro definitivo** — Q1.
- Retry de longa duração (horas/dias) — Q2.
- Mudar o retry HTTP nosso→Meta (3x/backoff no `whatsapp_client`) — já existe, continua.

## Próximos passos
1. ✅ Q1–Q7+Q5b respondidas · ✅ G1 (§4) · ✅ G2 (branches) · ✅ `product.md` · ✅ `design.md` + **ADR 0014**.
2. **Gate de design:** Jefferson revisa `design.md` + ADR 0014 (parada atual).
3. Aprovado → escrever `spec.md` (AC em Given/When/Then) + `tasks.md` + `/migracao` + `/meta-whatsapp` (allowlist).
