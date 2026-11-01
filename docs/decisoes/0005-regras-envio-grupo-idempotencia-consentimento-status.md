# ADR 0005 — Regras de envio: expansão de grupo, idempotência por contato, consentimento e estado `aguardando_decisao`

- **Status:** aceito
- **Data:** 2026-11-01
- **Contexto da feature:** refino de especificações pré-fases 2–4 (sabatina `/clarificar`)
- **Aprovação:** regras de envio exigem aprovação explícita (CLAUDE.md §4) — dada por Jefferson em 2026-11-01

## Contexto
Três lacunas do BRIEFING que tocam schema/invariante e são caras de reverter depois das migrations das fases 2–4:
1. Agendamento de **grupo** vira N envios, mas a idempotência estava ancorada **por agendamento** (CLAUDE.md §5.2,
   BRIEFING §9) — não impedia reenvio ao mesmo contato (ex.: worker cai após enviar 5 de 20 e reinicia).
2. **Consentimento** existia como campo (§9) e menção LGPD (§11), mas **não** era invariante de bloqueio (§5).
3. O **ciclo de status** (§9) não tinha estado para "adia", "reagenda" e "marcar para decisão do operador" (§10.3).

## Decisão
1. **Expansão de grupo no disparo.** 1 `agendamento` com `grupo`; o worker materializa **1 `envio` por contato
   elegível no momento do envio** (grupo dinâmico — quem está no grupo no disparo). Idempotência via
   **`UNIQUE(envios.agendamento_id, contato_id)`**; reinício no meio do lote não duplica (contatos já enviados têm
   linha em `envios`). Checagens (descadastro, consentimento, limites) rodam **por contato**.
2. **Recorrência.** Cada ocorrência é uma **nova linha de agendamento** (§10.3.3); logo `(agendamento, contato)` é
   chave completa — sem dimensão extra de ocorrência nos envios. A criação da próxima ocorrência é dedupada por
   **`UNIQUE(agendamento_pai_id, executar_em)`**.
3. **Consentimento como invariante (novo CLAUDE.md §5.9).** Nenhum envio sem opt-in registrado (`consentimento = true`
   com origem+data), no mesmo nível do descadastro. Importação CSV/XLSX **não** auto-consente: linha sem origem+data
   entra "sem consentimento" e fica **bloqueada** até o operador registrar a base.
4. **Ciclo de status.** `adia` (limite) e `reagenda` (fora da janela) **permanecem `aprovado`**, só atualizam
   `executar_em` (reagenda → início da próxima janela permitida); `motivo_ultima_transicao` e `reagendamentos`
   registram o porquê. Novo estado **`aguardando_decisao`**: o worker move pra lá quando detecta **gap de heartbeat**
   (`ultimo_ciclo_em` maior que o intervalo do loop = indisponibilidade) **e** o item está **>2h atrasado**; dali o
   operador faz **reenviar** (→ `aprovado`) ou **cancelar** (→ `cancelado`). Atraso **sem** gap de heartbeat segue normal.

## Consequências
- Toca o schema das fases 2–4: `envios` (`UNIQUE(agendamento_id, contato_id)`), `agendamentos`
  (`motivo_ultima_transicao`, `reagendamentos`, `agendamento_pai_id`, estado `aguardando_decisao`), `contatos`
  (regra de consentimento no import). Definido **antes** das migrations → sem retrabalho.
- A fila de verificações do worker passa a iterar contatos do grupo; custo previsto (dezenas/dia) é baixo.
- Fica **fora** desta decisão (tratar no `/nova-feature` da fase correspondente): definição de "sem edição" na
  liberação gradual (§10.7), status de webhook fora de ordem (§10.2.4), teto de gasto estimado×real + reset
  mensal (§10.7).
