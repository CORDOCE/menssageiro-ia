# Spec — 0017 Alerta de fluxo crítico ao Sentry (dívida O1)

Tier Pequeno. Observabilidade (§7/§12): hoje os eventos de fluxo crítico do disparo são auditados no
banco mas **não** chegam a nenhum canal de alerta (só exceções Python vão ao Sentry). Esta spec faz os
eventos `error`/`warning` do disparo **também** irem ao Sentry, para o §12 poder alertar (e-mail via
rules do painel). Sem migração, sem regra de envio, sem §4.

## Resumo de entendimento (/clarificar, 2026-11-09, Jefferson)
- **Escopo:** eventos **pontuais** de fluxo crítico do disparo ao Sentry (código). Alertas de **agregação/ausência**
  (worker parado >5min, falhas >5%/dia) ficam **fora** — são monitors/metric alerts configurados no painel Sentry (§4), item seguinte.
- **Mecanismo:** flag `alertar=True` em `registrar_auditoria`; quando `status ∈ {error, warning}`, emite
  `sentry_sdk.capture_message` com nível, `operacao`, `correlation_id` e `metadados` (já sem PII; `before_send` mascara).

## Eventos de fluxo crítico (evidência — grep do disparo/webhook)
| Evento (`operacao`) | status | nível Sentry |
|---|---|---|
| `agendamento.erro_ciclo` | error | error |
| `agendamento.falhou` (modelo não aprovado) | error | error |
| `agendamento.limite_por_agendamento` (teto, 0016) | warning | warning |
| `envio.falhou` (Meta rejeitou) | error | error |
| `template_status` pausado/rejeitado (webhook) | warning | warning |

Não alertam: `envio.enviado`/`envio.pulado`/`agendamento.ocorrencia_criada`/`envio_status` (success/skipped).

## Critérios de aceite (Given/When/Then)

**AC-1 — Alerta em `error`.**
Given Sentry inicializado e `registrar_auditoria(..., status="error", alertar=True)`,
When chamado,
Then emite um `capture_message` **nível error** com `operacao` e `correlation_id`; a auditoria é gravada normalmente.

**AC-2 — Alerta em `warning`.**
Given `status="warning", alertar=True`,
When chamado,
Then emite `capture_message` **nível warning**.

**AC-3 — Sem `alertar` não emite.**
Given `alertar=False` (default), qualquer status,
When chamado,
Then **não** emite ao Sentry (auditoria normal não vira alerta).

**AC-4 — Só `error`/`warning` alertam.**
Given `alertar=True` e `status ∈ {success, skipped}`,
When chamado,
Then **não** emite (só fluxo crítico alerta).

**AC-5 — Pontos do disparo emitem.**
Given o worker processa um agendamento com **modelo não aprovado** (ou **teto atingido**, ou **envio falha**),
When o ciclo roda,
Then o evento correspondente é emitido ao Sentry (via `alertar=True` naquele ponto).

**AC-6 — Sentry inerte não quebra.**
Given **sem** `SENTRY_DSN` (Sentry não inicializado),
When um evento com `alertar=True` ocorre,
Then é **no-op** (não levanta); a auditoria grava normalmente (instrumentação nunca derruba o fluxo, §5.8).

**AC-7 — Sem PII.**
Given um evento emitido,
When chega ao Sentry,
Then a mensagem/contexto **não** contém telefone nem texto de mensagem (metadados já sem PII; `before_send` mascara dígitos).

## Casos de borda
- Falha no `capture_message` não propaga (dentro do try não-bloqueante de `registrar_auditoria`).
- `template_status`: só alerta quando o novo status é `pausado`/`rejeitado` (não em `aprovado`).

## Fora de escopo
- Alertas de **agregação/ausência**: worker parado >5min, falhas >5%/dia, qualidade do número (painel Sentry / item seguinte).
- Configurar **rules/monitors** no painel Sentry (§4); canal de e-mail/push dedicado (§12 "e-mail+push" fica via rules do Sentry).
- Indicadores/alertas de **respostas IA** (§12) — IA não está ativa.

## Definition of Ready
- [x] AC testáveis (pytest com mock de `sentry_sdk.capture_message`). Non-goals explícitos. Sem migração/§4.
