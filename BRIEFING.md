# BRIEFING — Mensageiro (assistente de mensagens no WhatsApp)

> Documento de orientação para o agente de desenvolvimento (Claude Code).
> Leia por inteiro antes de qualquer alteração. Em caso de conflito entre este
> briefing e uma suposição sua, **o briefing vence**; em caso de dúvida real, pergunte.
>
> Versão: 2026-10-30 (inclui respostas controladas a mensagens recebidas) · Responsável: Jefferson Luiz da Silva · Usuário final: 1 operador (o cliente)

---

## 1. Contexto e objetivo

O sistema envia, pelo número oficial de WhatsApp de uma empresa, **cobranças, comunicados e
notificações** agendados (data, hora, destinatário e recorrência definidos pelo operador).
Volume previsto: **dezenas de mensagens por dia**. Nada de marketing.

Uma IA ajuda a **redigir/melhorar textos** e **sugere envios** (ex.: cobrança que vence em
3 dias sem lembrete). **Nada sai sem aprovação do operador**, exceto o que ele próprio agendou.

O operador usa um **PWA** (celular e computador) e também pode conversar com o assistente
**pelo próprio WhatsApp pessoal** (comandos e aprovações), já na primeira versão.

**Mudança de escopo (30/10/2026):** o assistente também **responde mensagens recebidas**, de forma
**totalmente controlada e monitorada**: só sobre assuntos liberados, com regras, limites, verificação de
cada resposta, repasse para humano e interruptor geral. Detalhes na seção 10.7.

## 2. Decisões fechadas (não reabrir sem pedir)

| Tema | Decisão |
|---|---|
| Canal | **WhatsApp Cloud API oficial da Meta**, chamada diretamente pelo backend. Nada de Evolution API/Baileys. |
| Número | Coexistência (app WhatsApp Business + API) se o número já for Business; senão, número dedicado. |
| Categorias de template | Só **UTILITY**. Nunca MARKETING. |
| Usuários do painel | **1 usuário** (admin), com verificação em duas etapas (TOTP). |
| Origem das mensagens | Digitadas no painel; IA pode sugerir melhoria de texto. |
| Anexos | Sim: **PDF (boleto)** no cabeçalho do template e **código Pix** como variável de texto. |
| Comandos pelo WhatsApp | **Na v1**, apenas do(s) número(s) de admin autorizado(s). |
| IA | OpenAI, modelo em variável `OPENAI_MODEL` (padrão `gpt-6-luna`). **Não usar `gpt-4o-mini`** (desligado da API em 14/01/2027). Reaproveitar a conta/chave do projeto antigo. |
| Hospedagem | Railway, **projeto novo** (ver `RAILWAY.md`). |
| Repositório | Monorepo `backend/` + `frontend/`. |
| Respostas a mensagens recebidas | **Sim, controladas.** Modos por assunto e por conversa: **Aprovação** (padrão), **Automático restrito**, **Manual**. A IA nunca responde fora da lista de assuntos liberados. |

## 3. Escopo

### v1 (dentro)
1. Login (1 usuário) + 2FA.
2. Contatos: CRUD, importação CSV/XLSX, consentimento, descadastro.
3. Modelos (templates): criar com ajuda da IA, enviar para aprovação da Meta, sincronizar status.
4. Nova mensagem: contato/grupo → modelo → variáveis (com prévia exata) → anexo opcional → data/hora/recorrência → confirmar.
5. Agenda (calendário + lista), editar/cancelar.
6. Worker de envio (a cada 1 min) com todas as checagens.
7. Webhook da Meta: status, mensagens recebidas, SAIR/PARAR, eventos de template.
8. Sugestões da IA (job diário) + fila de aprovação.
9. Comandos pelo WhatsApp do admin + resumo diário com botões Aprovar/Recusar.
10. Histórico, respostas recebidas, tela "Saúde do sistema", alertas.
11. PWA instalável com notificações push.
12. **Respostas controladas**: classificação de assunto, regras por assunto, rascunho/resposta da IA com base
    na base de respostas, verificações de segurança, aprovação, repasse para humano, interruptor geral.
13. Tela **Conversas** (caixa de entrada com modo por conversa e botão "Assumir"), **Base de respostas** e **Regras**.
14. Teto mensal de gasto com IA e conjunto de casos de teste (avaliação) no CI.

### Fora da v1
- Respostas sobre assuntos fora da lista liberada (sempre repassadas para humano).
- Negociação de valores, prazos ou descontos pela IA.
- Qualquer envio promocional/marketing.
- Integração automática com outros sistemas (ex.: sistema de recibos).
- Multiusuário/permissões avançadas.

## 4. Regras da Meta que moldam o sistema (obrigatório respeitar)

1. **Mensagem que inicia conversa = template aprovado.** Texto livre (`type: text`) só se o contato
   escreveu nas últimas 24 h (janela de atendimento). O backend **deve** checar
   `contatos.ultima_mensagem_recebida_em` antes de qualquer envio não-template.
2. **Fluxo "digitar → modelo":** quando o operador escreve uma mensagem nova:
   - a IA propõe texto melhorado e identifica as partes variáveis (`{{1}}`, `{{2}}`…);
   - se casar com um template **aprovado** existente → usa esse template;
   - se for novo → cria o template via API (categoria UTILITY, `pt_BR`, com exemplos) e o
     agendamento fica `aguardando_template` até a Meta aprovar (webhook
     `message_template_status_update`). Rejeitado → alerta ao operador com o motivo.
3. **Boas práticas de template:** não começar nem terminar com variável; evitar template "só
   variável"; nada de oferta/desconto/convite (vira MARKETING, ~10× mais caro).
4. **Custos (Brasil, tabela de 01/10/2026, por mensagem entregue):** utilidade R$ 0,035;
   serviço R$ 0,035 após **1.000 grátis/mês por número**; marketing R$ 0,3217 (não usar).
   Templates de utilidade **são cobrados mesmo dentro da janela de 24 h**. Mensagens recebidas são grátis.
5. **Limite de envio:** 250 destinatários únicos/24 h até a verificação da empresa; depois 2.000.
   O worker deve respeitar um `LIMITE_DIARIO` configurável (padrão 200).
6. **Qualidade do número:** monitorar; muitos bloqueios/denúncias pausam templates.
7. **Pagamento:** conta Meta em **BRL**, cartão da empresa cadastrado (sem cartão a Meta bloqueia envios).
8. **Política de IA da Meta:** o assistente é de propósito específico (notificações e atendimento do próprio
   negócio) — permitido. **Nunca** transformar em chatbot de uso geral: assunto fora da lista → repasse para humano.
9. **Respostas são mensagens de serviço:** texto livre só dentro da janela de 24 h; 1.000 grátis/mês por número,
   depois R$ 0,035 cada. Fora da janela, responder só com template aprovado.

## 5. Arquitetura

```
Operador (PWA / WhatsApp pessoal)
        │
 ┌──────┴────────────── Railway (projeto novo) ──────────────────┐
 │ frontend (Next.js PWA) ──► api (FastAPI) ◄── webhook da Meta    │
 │                              │                                 │
 │                          PostgreSQL ◄── worker (loop 1 min,     │
 │                                         jobs diários, IA)      │
 └───────────────────────────────┬─────────────────────────────────┘
                                 ▼
                     WhatsApp Cloud API ──► contatos
```

- **Só o worker inicia mensagens agendadas.** A API responde ao webhook e a comandos do admin.
- Tudo passa pelo banco; nenhum estado crítico em memória.

## 6. Repositório

```
mensageiro-whatsapp/
├── BRIEFING.md            (este arquivo)
├── RAILWAY.md             (infra)
├── CLAUDE.md              (regras de trabalho do agente — criar a partir da seção 13)
├── backend/
│   ├── app/
│   │   ├── api/           rotas: auth, contatos, modelos, agendamentos, sugestoes,
│   │   │                  historico, configuracoes, saude, webhook_meta
│   │   ├── core/          config, security, auth_deps, audit, logging
│   │   ├── models/        SQLAlchemy
│   │   ├── schemas/       Pydantic
│   │   ├── services/      whatsapp_client, templates, ia, comandos_admin, email, push
│   │   └── worker/        loop de envio, jobs diários
│   ├── migrations/        Alembic
│   ├── tests/
│   └── pyproject.toml
├── frontend/              Next.js + TypeScript (PWA)
└── .github/workflows/     CI
```

## 7. Stack

| Camada | Tecnologia |
|---|---|
| Backend/worker | Python 3.14, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, httpx (ver ADR 0003) |
| Frontend | TypeScript, Next.js, PWA (manifest + service worker + Web Push) |
| Banco | PostgreSQL |
| IA | SDK oficial da OpenAI, saída em JSON estruturado (schema) |
| Qualidade | pytest, ruff, mypy, eslint, tsc |
| Erros | Sentry (backend e frontend) |

## 8. Reaproveitamento do projeto antigo

Projeto de origem: `/Users/jefferson/Documents/Code/document-ai-system` (sistema de digitalização de
recibos, FastAPI + Next.js, rodou na Railway). **Copiar e adaptar; nunca alterar o projeto antigo.**

| Origem | Ação |
|---|---|
| `main.py`, `app/db/database.py`, `Procfile` | Adaptar para `backend/` |
| `app/api/auth.py`, `usuarios.py`, `app/core/security.py`, `auth_deps.py`, modelo de usuário | Manter (simplificar para 1 usuário, adicionar TOTP) |
| `app/services/password_reset.py`, `email.py` (Resend) | Manter |
| `app/core/audit.py`, `app/models/audit.py` | Manter |
| `app/api/health.py` | Adaptar (banco, worker, Meta) |
| `app/core/notifier.py` | Reescrever como `whatsapp_client.py` (Cloud API) |
| `app/api/webhook.py` | Reescrever (formato e assinatura da Meta) |
| `app/worker/extractor.py` | Base para `services/ia.py` |
| state_machine, session_wal, session_snapshot, redis_client, quarantine, documentos | **Não copiar** |
| `cordoce-frontend/` | Reaproveitar casca (login, layout, tema); trocar páginas |
| `CLAUDE.md`, `.claude/` | Usar como referência de governança |
| `.env` | **Nunca copiar.** Só o valor de `OPENAI_API_KEY` vai para a Railway nova |

## 9. Modelo de dados

| Tabela | Campos principais |
|---|---|
| `usuarios` | (do projeto antigo) + `totp_secret`, `telefone_whatsapp` (para comandos) |
| `contatos` | id, nome, telefone_e164 (único), grupo/tags, consentimento (bool, data, origem), descadastrado_em, ultima_mensagem_recebida_em, observacoes |
| `modelos` | id, nome_meta, idioma, categoria, status (rascunho/pendente/aprovado/rejeitado/pausado), corpo, variaveis (rótulos + exemplos), tem_anexo, motivo_rejeicao, sincronizado_em |
| `anexos` | id, nome_arquivo, mime, tamanho, armazenamento (id de mídia Meta e/ou caminho), criado_em |
| `agendamentos` | id, contato_id **ou** grupo, modelo_id, variaveis (JSON), anexo_id, executar_em (timestamptz), recorrencia (RRULE), status, origem (operador/ia/comando), criado_por, aprovado_por, chave_idempotencia (única) |
| `envios` | id, agendamento_id, contato_id, wamid, status (enviado/entregue/lido/falhou), erro_codigo, erro_texto, tentativas, categoria_cobranca, custo_estimado, enviado_em, entregue_em, lido_em |
| `conversas` | id, contato_id, modo (aprovacao/automatico/manual), motivo_modo, assumida_por_humano_em, ultima_mensagem_em, precisa_atencao (bool) |
| `mensagens` | id, conversa_id, direcao (entrada/saida), origem (contato/operador/ia/agendamento/app_celular), wamid, tipo, texto, criada_em, lida_pelo_operador |
| `assuntos` | id, nome (ex.: ja_paguei, segunda_via, horario), descricao, exemplos, modo_permitido (aprovacao/automatico/proibido), ativo, versao |
| `base_respostas` | id, assunto_id, pergunta, resposta_aprovada, dados_permitidos (quais campos do contato podem entrar), versao, aprovado_pelo_cliente_em |
| `decisoes_ia` | id, mensagem_entrada_id, assunto_detectado, confianca, regra_aplicada, rascunho, verificacoes (JSON), decisao (enviada/aguardando_aprovacao/bloqueada/repassada), motivo, versao_prompt, modelo_ia, tokens, custo_estimado, latencia_ms, criada_em |
| `sugestoes_ia` | id, contato_id, modelo_id, variaveis, executar_em_proposto, justificativa, entrada_ia, saida_ia, status, decidido_em |
| `configuracoes` | janela_envio (dias/horas), limite_diario, limite_por_contato_dia, envios_pausados, email_alertas, **respostas_automaticas_ativas** (interruptor geral), **limite_respostas_por_conversa_hora** (padrão 3), **teto_gasto_ia_mensal**, **comportamento_fora_horario** (responder/avisar_retorno/silencio), **sla_resposta_humana_min** |
| `eventos_webhook` | id_evento (único), recebido_em — para deduplicação |
| `auditoria` | (do projeto antigo) |

Ciclo de `agendamentos.status`:
`rascunho → aguardando_template → aguardando_aprovacao (só IA) → aprovado → enviando → enviado | falhou | cancelado`

Todas as datas em `timestamptz`; exibição em `America/Sao_Paulo`.

## 10. Componentes

### 10.1 Cliente WhatsApp (`services/whatsapp_client.py`)
- `POST /{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages` com `type: template` (corpo + cabeçalho DOCUMENT quando houver PDF).
- Upload de mídia (PDF) via endpoint de mídia da Meta e uso do `id` retornado.
- Templates: listar/criar via `/{WABA_ID}/message_templates`.
- Erros temporários (429, 5xx): retry exponencial, máx. 3. Erros definitivos: `falhou` + código + alerta.
- Versão da Graph API em variável `GRAPH_API_VERSION` (confirmar a atual na documentação).

### 10.2 Webhook (`api/webhook_meta.py`)
1. `GET`: verificação (`hub.verify_token` → devolve `hub.challenge`).
2. `POST`: validar `X-Hub-Signature-256` (HMAC-SHA256 do corpo cru com `APP_SECRET`, `hmac.compare_digest`). Inválido → 403.
3. Responder 200 rápido; processar em segundo plano; deduplicar por id do evento.
4. Status → atualiza `envios` pelo `wamid` (guardar também o objeto `pricing`).
5. Mensagem recebida → grava em `mensagens`, atualiza `ultima_mensagem_recebida_em` e coloca na **fila de entrada**
   do fluxo de respostas (seção 10.7). Mensagens enviadas pelo app WhatsApp Business no celular (eventos de eco da
   coexistência) são gravadas com origem `app_celular` e **pausam a IA naquela conversa** (modo Manual).
6. `SAIR`/`PARAR`/`CANCELAR` → descadastra, cancela futuros, confirma ao contato.
7. Se o remetente for o admin → encaminha para `comandos_admin`.
8. `message_template_status_update` → atualiza `modelos` e libera/bloqueia agendamentos.

### 10.3 Worker (`worker/`)
Loop a cada 60 s:
1. `SELECT … FOR UPDATE SKIP LOCKED` em agendamentos `aprovado` vencidos → `enviando`.
2. Checagens: descadastrado → cancela; fora da janela (padrão seg–sáb 8h–20h) → reagenda; modelo não aprovado → falha + alerta;
   limite diário / por contato → adia; `envios_pausados` → não envia.
3. Envia, grava `envios`, auditoria; recorrência → cria próximo.
4. Atrasos > 2 h após indisponibilidade: **não enviar automaticamente**; marcar para decisão do operador.
5. Gravar heartbeat (`ultimo_ciclo_em`).

Jobs diários: 06:00 sincronizar modelos · 07:00 gerar sugestões da IA · 07:30 resumo para o admin (WhatsApp + e-mail).

### 10.4 IA (`services/ia.py`)
- Funções: `melhorar_texto(rascunho)` → texto + variáveis detectadas; `sugerir_envios(contexto)` → lista JSON.
- Sempre saída com JSON Schema; o backend valida (modelo existe, nº de variáveis, janela, contato ativo). Inválido → descarta e loga.
- Enviar ao provedor **o mínimo** de dados pessoais. Guardar entrada/saída em `sugestoes_ia` para auditoria.
- Instrução de sistema: propor apenas cobranças, comunicados e notificações; usar só modelos fornecidos; nunca inventar valores, datas ou pedidos; responder só no schema.

### 10.5 Comandos pelo WhatsApp (`services/comandos_admin.py`)
- Aceitar **somente** de números em `ADMIN_WHATSAPP_NUMBERS`. Outros números seguem o fluxo normal de contato.
- Comandos v1: `hoje` (envios do dia), `pendentes` (sugestões), `pausar` / `retomar`, `ajuda`.
- Resumo diário: template UTILITY para o admin com botões de resposta rápida **Aprovar todas / Revisar no app**;
  aprovação individual por botões em mensagens interativas (dentro da janela de 24 h).
- Todo comando gera auditoria. Ações destrutivas (cancelar em massa) **não** existem por WhatsApp na v1.

### 10.6 Frontend (PWA)
Telas: Hoje · Nova mensagem · Agenda · Sugestões · Contatos · Modelos · Histórico · Saúde do sistema · Configurações.
Requisitos visuais detalhados em `DESIGN-DASHBOARD.md` (a definir).

### 10.7 Respostas controladas (`services/respostas/`)

Fluxo para cada mensagem recebida (processado pelo worker em loop curto de ~5 s ou via `LISTEN/NOTIFY`;
meta: resposta automática em até 30 s):

1. **Pré-checagens**: interruptor geral desligado → só registra e notifica. Conversa em modo Manual → só notifica.
   Remetente é admin → `comandos_admin`. SAIR/PARAR → descadastro (seção 10.2).
2. **Classificar assunto** (IA, saída em JSON Schema: `assunto`, `confianca`, `sentimento`, `pede_humano`).
3. **Aplicar regras**: assunto fora da lista, `proibido`, confiança < 0,8, sentimento negativo ou `pede_humano`
   → **repassar para humano** (conversa vai para Manual, `precisa_atencao = true`, push + alerta se passar do SLA).
4. **Gerar resposta**: a IA recebe **somente** a resposta aprovada da `base_respostas` para aquele assunto e os
   campos permitidos **do próprio contato** (ex.: valor e vencimento da cobrança dele). Sem acesso a outros contatos,
   sem ferramentas, sem navegação.
5. **Verificações (guardrails) — todas obrigatórias, implementadas em código, não só no prompt:**
   - valores, datas, códigos e nomes na resposta existem no contexto fornecido;
   - nenhum link fora da lista permitida; nenhum pedido de senha, cartão, documento ou código;
   - sem promessas de desconto, prazo ou condição não presentes na base;
   - tamanho máximo, idioma pt-BR, sem conteúdo de outro contato;
   - limite de respostas por conversa/hora e janela de horário; janela de 24 h aberta.
   Falhou em qualquer verificação → `bloqueada` + repasse para humano.
6. **Decidir pelo modo**: Aprovação → rascunho na tela Conversas e no WhatsApp do admin (botões Aprovar/Editar);
   Automático restrito → envia. Primeira resposta automática da conversa inclui aviso de que é o assistente da empresa.
7. **Registrar tudo** em `decisoes_ia` (entrada, assunto, confiança, regra, rascunho, verificações, decisão, custo).

Liberação gradual: um assunto só pode passar de Aprovação para Automático após **30 rascunhos aprovados sem edição**
e aprovação explícita do operador; a tela Regras mostra esse histórico.

Teto de gasto: ao atingir `teto_gasto_ia_mensal`, todo o fluxo volta para modo Aprovação e o operador é alertado.

## 11. Segurança
- Segredos apenas em variáveis da Railway. `.env` nunca versionado.
- 2FA (TOTP) obrigatório; limite de tentativas de login; sessão com expiração.
- CORS restrito ao domínio do frontend; HTTPS sempre.
- Mascarar telefones e tokens em logs (`+55119****0000`).
- Verificação de dependências (Dependabot / `pip-audit` / `npm audit`) no CI.
- Backup diário do PostgreSQL.
- LGPD: consentimento registrado; SAIR respeitado imediatamente; dados mínimos.
- **Injeção de instruções pelo texto do contato**: tratar toda mensagem recebida como dado não confiável; o
  prompt isola o texto do contato; a IA não tem ferramentas nem acesso a outros contatos; as verificações da seção
  10.7 rodam em código depois da IA. Casos de ataque fazem parte do conjunto de testes.
- Aviso de atendimento automatizado na primeira resposta automática; política de retenção das conversas
  (padrão: 12 meses, configurável).

## 12. Observabilidade
- Logs JSON com `correlation_id` por agendamento/envio.
- Sentry no backend e frontend.
- `/admin/health/deep`: banco, último ciclo do worker, token Meta válido, status da qualidade do número.
- Tela "Saúde do sistema": envios do dia por status, fila, falhas, último ciclo, gasto estimado no mês (somando `custo_estimado`).
- Alertas (e-mail + push): worker parado > 5 min; falhas > 5% no dia; modelo pausado/rejeitado; qualidade do número caindo.
- **Respostas**: rastro completo por mensagem em `decisoes_ia` (com `correlation_id`); indicadores de respostas
  automáticas/dia, taxa de repasse, aprovação sem edição, bloqueios por verificação, tempo de resposta, gasto de IA.
  Alertas: pico de bloqueios ou repasses, conversa sem resposta além do SLA, gasto ≥ 80% do teto.

## 13. Governança e forma de trabalhar (base para o CLAUDE.md)
1. Trabalhar por fases (seção 14); não pular critérios de "pronto".
2. Toda mudança via branch + PR; `main` protegida; CI verde obrigatório.
3. Migrações sempre por Alembic, com downgrade.
4. Testes junto com o código: nenhum endpoint ou regra de envio sem teste.
5. Nunca enviar mensagem para número real em testes; usar o número de teste da Meta e mocks.
6. Nunca commitar segredos, `.env`, dumps ou dados de contatos.
7. Mudanças em regras de envio (janela, limites, idempotência) exigem descrição do risco no PR.
8. Registrar decisões relevantes em `docs/decisoes/` (ADR curto).
9. **Política de respostas** em `docs/politica-respostas.md`, aprovada pelo cliente: o que a IA responde, o que
   nunca responde, quando repassa. Mudanças exigem nova aprovação.
10. Prompts versionados em `backend/app/services/respostas/prompts/` (com número de versão gravado em `decisoes_ia`).
11. **Avaliação no CI**: `backend/tests/avaliacao/` com perguntas reais e maliciosas e o resultado esperado
    (assunto, decisão). Qualquer mudança de prompt, regra ou `OPENAI_MODEL` só entra com a avaliação passando.
12. Revisão semanal de amostra das respostas automáticas (tela Conversas → filtro "automáticas").

## 14. Fases e critérios de pronto

| Fase | Entrega | Pronto quando |
|---|---|---|
| 0 | Conta Meta, verificação, número, pagamento em BRL, token | Número "Conectado" e token permanente gerado (feito pelo responsável, fora do código) |
| 1 | Esqueleto do repo + CI + deploy Railway (api, worker, frontend, Postgres) | Login funciona em staging; CI verde |
| 2 | Modelo de dados + Alembic + contatos + importação | Contatos importados de planilha com validação |
| 3 | Cliente WhatsApp + webhook + modelos (criar/sincronizar) | Template enviado ao número de teste; status entregue/lido gravados |
| 4 | Worker + agendamentos + recorrência + anexos | Envios no minuto certo, sem duplicidade, inclusive após reiniciar |
| 5 | Frontend PWA (todas as telas) | Operador agenda, aprova e acompanha sem ajuda |
| 6 | IA (melhorar texto + sugestões) | Sugestões às 07:00 viram agendamentos ao aprovar |
| 7 | Comandos pelo WhatsApp + resumo diário | Admin consulta e aprova pelo WhatsApp; outros números ignorados |
| 8 | **Respostas controladas** (seção 10.7) + telas Conversas, Base de respostas e Regras + avaliação no CI | Todos os casos de avaliação passam; repasse para humano e interruptor geral funcionando; nada sai sem passar pelas verificações |
| 9 | Testes, piloto interno (1 semana, respostas só em modo Aprovação), entrada gradual | 100% no horário, zero duplicidade, status em todos os envios, zero resposta fora da política |

Prazo estimado: ~11 a 12 semanas.

## 15. Variáveis de ambiente

`DATABASE_URL`, `WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`, `WABA_ID`, `APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`,
`GRAPH_API_VERSION`, `ADMIN_WHATSAPP_NUMBERS`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `RESEND_API_KEY`,
`EMAIL_FROM`, `EMAIL_ALERTAS`, `FRONTEND_URL`, `API_URL`, `SENTRY_DSN`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
`TZ=America/Sao_Paulo`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (só para o primeiro acesso).

## 16. Pendências do cliente
- Exemplos reais de cobrança, comunicado e notificação (para os primeiros modelos).
- Número a ser usado e situação atual (pessoal / Business / novo).
- Business Manager existente e verificado?
- Janela de envio permitida e limite por contato.
- Confirmação do uso de boleto em PDF e Pix.
- **Respostas**: lista de assuntos que a IA pode responder e assuntos proibidos.
- **Base de respostas**: perguntas e respostas frequentes escritas/aprovadas pelo cliente.
- **Fora do horário**: responder, avisar que retornará ou ficar em silêncio.
- **Prazo de resposta humana** para conversas repassadas.
