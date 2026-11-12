# Spec — 0019 Alertas de agregação (worker parado + taxa de falha)

Tier Pequeno. Observabilidade (§7/§12). A 0017 levou os eventos **pontuais** de fluxo crítico ao Sentry,
mas deixou de fora (`specs/0017-alerta-observabilidade/spec.md:67`) os alertas de **agregação/ausência**:
**worker parado >5min** e **falhas de envio >5%/dia** (BRIEFING §12, `BRIEFING.md:299`). Esta spec cobre
esses dois. Sem migração (reusa `saude.ultimo_ciclo_em` e `alertar_evento`/auditoria da 0017).

## Resumo de entendimento (decisões, 2026-11-10 e 2026-11-11, Jefferson)
- **Escopo:** dois alertas. **(A)** worker parado >5min via **Sentry Cron Monitor + check-in** por ciclo
  (observador externo detecta a ausência — cobre worker morto, que não se auto-alerta). **(B)** taxa de falha
  de envio >5% nas últimas 24h via **lógica no código** + `alertar_evento`.
- **Thresholds oficiais (§12):** worker parado **>5min**; falhas **>5%/dia**.
- **Piso de volume (B):** **20 tentativas** em 24h — abaixo disso não alerta (anti-ruído).
- **Config do monitor (A):** **upsert inline** via `monitor_config` no `capture_checkin` (schedule/margem no
  código, auto-cria o monitor). Roteamento de e-mail/push é config de painel (§4), documentada à parte — não
  entra no código desta spec.
- **Idempotência diária (B):** no máximo **1 alerta/dia**, checando a auditoria antes de emitir.
- **Mecanismo (A):** `sentry_sdk.crons.capture_checkin` (`sentry-sdk 2.74.0`); no-op sem `SENTRY_DSN`.

## Âncoras de código (evidência — grep do worker/core)
| O quê | Onde | Papel na 0019 |
|---|---|---|
| Loop do worker + `import sentry_sdk` | `backend/app/worker/__main__.py:49-66` (loop); `:11` (import); `:60` (`capture_exception`) | ponto do check-in (A) |
| Heartbeat `saude.ultimo_ciclo_em` | `backend/app/models/saude.py:16-22`; grava em `__main__.py:33-46` (chamado `:62`) | contexto (A) |
| `alertar_evento(operacao, status, correlation_id, metadados)` | `backend/app/core/observabilidade.py:59-79` (só error/warning; no-op sem Sentry) | emite (B) |
| `registrar_auditoria(..., alertar=False)` | `backend/app/core/audit.py:17-59` | rastro + idempotência (B) |
| Idempotência por auditoria+janela (precedente) | `backend/app/api/auth.py:68-77` | molde "1 alerta/dia" (B) |
| Status de `envios` (enum) | `backend/app/models/envio.py:40`; valores em `backend/app/schemas/envio.py:17-22` (`…`/`falhou`) | numerador/denominador (B) |
| Janela 24h sobre `envios` + `_CONTAM_LIMITE` | `backend/app/worker/disparo.py:142`; `disparo.py:46` | molde falhas/tentativas 24h (B) |

Definições para a taxa (B), nas últimas 24h por `Envio.criado_em`, lendo o **status atual** do envio:
- **tentativas** = status ∈ `_CONTAM_LIMITE` (`enviando`/`enviado`/`entregue`/`lido`) **mais** `falhou`.
- **falhas** = envios com `status == "falhou"`.
- **Transitório de conexão não infla a taxa.** O cliente já faz **retry HTTP** nosso→Meta — 3 tentativas com backoff exponencial, só para `429/5xx` (`whatsapp_client.py:17,123`); se o blip passa, o envio nunca vira `falhou`. Só vira `falhou` quando os 3 tiros se esgotam (`disparo.py:357-367`) **ou** quando a Meta reporta entrega `failed` depois, via webhook (`webhook_meta.py:120-121`) — essa é a não-entrega **real** (operadora/telefone do destinatário) que o §12 quer alertar.
- Envio ainda **em trânsito** (`enviando`/`enviado`, sem confirmação da Meta) conta como **tentativa, não falha**. Como a métrica lê status atual, um `enviado` que a Meta depois marca `failed` passa a contar como falha enquanto estiver na janela de 24h.
- **Não há reenvio no nível da mensagem** (§5.2: um envio por `(agendamento, contato)`; `disparo.py:345`). O "retry por minutos/horas" de entrega é da **própria Meta** durante a validade do template, não do nosso worker. (A regra exata de contagem vira teste — ver matriz.)

## Critérios de aceite (Given/When/Then)

**AC-1 — Check-in por ciclo.**
Given Sentry inicializado e o worker executando um ciclo,
When o ciclo termina,
Then emite `sentry_sdk.crons.capture_checkin` com o **slug do monitor** e status **ok** (e `monitor_config` com o schedule/margem no upsert).

**AC-2 — Taxa alta alerta uma vez.**
Given nas últimas 24h há `tentativas ≥ 20` e `falhas/tentativas > 5%`, sem alerta de taxa hoje,
When o ciclo roda a checagem,
Then emite **um** `alertar_evento` (operação `envios.taxa_falha_alta`, nível warning/error) com os números agregados.

**AC-3 — Piso de volume.**
Given `falhas/tentativas > 5%` mas `tentativas < 20` nas últimas 24h,
When a checagem roda,
Then **não** emite alerta (anti-ruído).

**AC-4 — Taxa dentro do limite.**
Given `tentativas ≥ 20` mas `falhas/tentativas ≤ 5%`,
When a checagem roda,
Then **não** emite alerta.

**AC-5 — Idempotência diária.**
Given as condições de AC-2 **e** já existe na auditoria um alerta `envios.taxa_falha_alta` **hoje**,
When a checagem roda de novo no mesmo dia,
Then **não** emite segundo alerta (máx. 1/dia).

**AC-6 — Sentry inerte não quebra.**
Given **sem** `SENTRY_DSN` (Sentry não inicializado),
When o ciclo emite check-in (A) ou a taxa dispara (B),
Then ambos são **no-op** (não levantam); o ciclo e a auditoria seguem normais (instrumentação nunca derruba o fluxo, §5.8).

**AC-7 — Sem PII.**
Given o alerta de taxa (B) emitido,
When chega ao Sentry,
Then o conteúdo contém **só números agregados** (tentativas, falhas, percentual) — sem telefone nem texto de mensagem.

## Matriz de decisão — Alerta B (cada linha vira um teste)
| tentativas (24h) | falhas/tentativas | já alertou hoje | resultado |
|---|---|---|---|
| ≥ 20 | > 5% | não | **emite** (AC-2) |
| ≥ 20 | > 5% | sim | não emite (AC-5) |
| < 20 | > 5% | não | não emite (AC-3) |
| ≥ 20 | ≤ 5% | não | não emite (AC-4) |
| 0 | — (sem divisão) | não | não emite (borda) |

## Casos de borda
- `tentativas = 0` nas 24h → sem divisão por zero, sem alerta.
- Falha em `capture_checkin`/`capture_message` não propaga (try não-bloqueante, como na 0017).
- Virada de dia na janela de idempotência: "hoje" é dia-calendário em **America/Sao_Paulo** (exibição/§8), computado sobre `criado_em` (timestamptz).
- Check-in (A) e checagem de taxa (B) rodam a cada ciclo; só o alerta de B é limitado a 1/dia — o check-in é por ciclo por design.
- **Transitório recuperado no retry HTTP** (`whatsapp_client`, 3x/backoff) termina em `enviado` → conta como tentativa, **não** como falha (não dispara alerta por blip de conexão).
- **Envio `enviando` órfão** (processo caiu entre a reserva e o resultado) conta como tentativa, nunca como falha — não gera falso-positivo de taxa.
- **`enviado` que a Meta marca `failed` depois** (webhook) passa a contar como falha enquanto o `criado_em` estiver na janela de 24h.

## Fora de escopo (vinculante)
- **Qualidade do número caindo** (depende de sinal da Meta) — Fase 0.
- **Modelo pausado/rejeitado** — já coberto pela 0017.
- **Config de painel Sentry**: roteamento de e-mail/push do monitor e das issues (§4, exige aprovação; passo manual documentado, fora do código).
- Indicadores/alertas de **respostas da IA** (§12) — IA não ativa.
- Nenhuma mudança em **regra de envio** (janela, limites, idempotência de envio, recorrência): esta spec só observa.
- **Reenvio automático no nível da mensagem** (worker retentar um envio `falhou` após minutos/horas): seria **regra de envio nova** (§4, altera a invariante §5.2) — feature à parte, não entra aqui. O retry de conexão nosso→Meta (3x/backoff) já existe no `whatsapp_client`; o retry de entrega por minutos/horas é da própria Meta.

## Definition of Ready
- [x] AC testáveis (pytest com mock de `capture_checkin`/`capture_message`; tempo e contagem controlados por fixtures). Non-goals explícitos. Sem migração. Sem alteração de regra de envio/IA (§4).
