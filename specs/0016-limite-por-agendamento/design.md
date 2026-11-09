# Design — 0016 Teto de segurança por agendamento

Respeita a arquitetura existente (ADR 0008 config runtime; worker expande grupo em envios; idempotência
por `(agendamento_id, contato_id)`). Decisão de **regra de envio** (§5) → **ADR 0013** (curto).

## Solução
1. **Config:** nova coluna `limite_por_agendamento_dia: int | None` em `configuracoes` (nullable, `NULL` =
   sem teto), espelhando `limite_por_contato_dia`. Semeada por env opcional `LIMITE_POR_AGENDAMENTO`
   (como `LIMITE_DIARIO` semeia `limite_diario`). Lida a cada ciclo em `disparo.py` junto dos outros limites.
2. **Worker (`_processar_agendamento`):** ao montar os destinatários, se o teto estiver definido e o nº de
   contatos a enviar exceder `teto − já_enviados_deste_agendamento`, processa **apenas até o teto** e
   **para** (não envia o excedente). `já_enviados` = `COUNT(Envio WHERE agendamento_id=aid)` (cobre reprocessos;
   normalmente 0 no 1º disparo).
3. **Status ao parar — novo status terminal `parcial`.** Distingue de `enviado` (tudo) e `falhou` (nada).
   `motivo_ultima_transicao = "teto por-agendamento atingido — N de M enviados"`.
4. **Auditoria + alerta:** evento `agendamento.limite_por_agendamento` (status=warning) com
   `{enviados, total, teto}` (sem PII) + log estruturado com `correlation_id=aid`. É o **sinal** que a
   dívida O1/§12 consumirá; o pipeline de alerta em si fica fora (non-goal).

### Ordem dos limites (a cada disparo)
`envios_pausados` → fora da janela (reagenda) → modelo aprovado → **limite global** (adia o agendamento
inteiro) → **teto por-agendamento** (envia até o teto e marca `parcial`) → **limite por-contato** (pula o
contato). O teto por-agendamento entra **dentro** do loop de contatos, antes de `_processar_contato`.

## Alternativas consideradas (e por que não)
- **Reusar `enviado` + motivo** em vez de status `parcial`: menos invasivo, mas `enviado` mente (não enviou
  tudo) e some na tela. Rejeitado — a visibilidade do corte é o ponto da feature.
- **`falhou`**: engana no outro sentido (parte foi enviada). Rejeitado.
- **Adiar o excedente** (reusando idempotência): vira "espalhar em vários dias" — non-goal explícito.
- **Teto por agendamento (coluna em `agendamentos`)**: mais flexível, mas migração+API+UI; o caso é
  proteção global, um valor na config basta. Adiado.

## Impacto / arquivos
- Migração Alembic: `+limite_por_agendamento_dia` em `configuracoes` (downgrade = drop). **/migracao**.
- `models/configuracao.py` (+coluna), `core/config.py` (+`limite_por_agendamento_default` via env),
  `services/janela.py` (semente), `worker/disparo.py` (checagem + status `parcial` + auditoria).
- Status `parcial`: `components/Selo.tsx` `seloAgendamento` (+selo tom neutro/aguardando) e onde o worker/API
  tratam terminais. **Não** vira novo estado "ativo" (terminal, não reprocessa).

## Riscos
- **Novo status terminal** toca a UI (Agenda/Histórico) e o conjunto de terminais no worker — mapear todos os
  pontos (grep `enviado|falhou|cancelado`) para não deixar `parcial` órfão.
- **Contagem**: usar `COUNT(envios do agendamento)` garante idempotência sob reprocesso; cuidado para o corte
  ser determinístico (ordenar contatos de forma estável).
- Teto mal configurado (muito baixo) corta envios legítimos → é escolha consciente do operador; default `NULL`
  (sem teto) evita surpresa; mudança de valor exige **§4**.

## ADR
Decisão de regra de envio (novo limite + status `parcial`) → **`docs/decisoes/0013-teto-por-agendamento.md`**
(curto): contexto, decisão (teto na config, parar+marcar+alertar, status `parcial`), alternativas, consequências.
