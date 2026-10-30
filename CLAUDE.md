# CLAUDE.md — Regras de trabalho do repositório Mensageiro

Carregado em toda sessão: é curto de propósito. Detalhes do sistema estão em `BRIEFING.md`
(produto e arquitetura), `RAILWAY.md` (infra) e `DESIGN-DASHBOARD.md` (interface). Leia-os **sob demanda**,
só a seção necessária para a tarefa.

**Hierarquia em conflito:** pedido explícito do responsável (Jefferson) > este CLAUDE.md > BRIEFING.md >
spec ativa (`specs/NNNN-*/spec.md`) > código existente. Conflito real → pare e pergunte.

---

## 1. Evidência antes de afirmação (anti-alucinação)

1. **Só afirme o que verificou nesta sessão.** Fato sobre código, ambiente, banco ou API externa exige evidência:
   arquivo:linha lido, saída de comando, resultado de teste ou documentação oficial consultada.
2. **Classifique o que diz** quando houver incerteza: `[verificado]` (com a evidência), `[não verificado]`, `[hipótese]`.
3. **Proibido inventar** nomes de funções, arquivos, endpoints, campos de payload da Meta/OpenAI, versões de API,
   flags, variáveis de ambiente, códigos de erro ou comportamentos de biblioteca. Não sabe → procure (`grep`, doc
   oficial, `--help`, teste) ou pergunte.
4. **Sem inferência silenciosa.** Toda suposição necessária para avançar deve ser **explícita, mínima e reversível**,
   registrada na resposta e no PR/`STATE.md`. Nunca preencha lacuna de requisito com "provavelmente o usuário quer".
5. **"Não encontrei" ≠ "não existe".** Diga onde e como procurou.
6. **"Pronto", "funciona", "corrigido" só com o gate rodado** (testes, lint, tipos) e o resultado mostrado.
   Sem gate executável → diga "implementado, não verificado" e o que falta para verificar.
7. **Não ajuste um teste para fazê-lo passar** sem demonstrar que o teste estava errado (com evidência).
8. **"Não sei" é resposta válida** e preferível a uma resposta plausível não verificada.
9. Ao citar documentação externa, cite a URL e a data de consulta; APIs da Meta e da OpenAI mudam com frequência.

## 2. Método científico (falseabilidade, Karl Popper)

Toda investigação de bug, decisão técnica incerta ou "por que isso acontece" segue:

1. **Observação**: o fato reproduzível (comando, entrada, saída obtida vs esperada).
2. **Hipótese falseável**: uma explicação que diga **o que observaríamos se ela fosse falsa**.
   Hipótese que não pode ser refutada por nenhum experimento não serve.
3. **Predição**: resultado concreto esperado do experimento se a hipótese for verdadeira.
4. **Experimento mínimo e executável**: de preferência um **teste que falha primeiro** (red); uma variável por vez.
5. **Resultado**: hipótese **refutada** (descarte, registre, formule outra) ou **corroborada** (nunca "provada";
   o teste fica no repositório como guarda contra regressão).
6. **Busque refutar, não confirmar**: procure o contraexemplo, o caso de borda, a entrada maliciosa.
7. Registre hipóteses descartadas no PR ou no `STATE.md` (evita repetir caminhos mortos).

Use a skill **/hipotese** para conduzir esse ciclo.

## 3. Economia de tokens sem perder rigor

- Localize antes de ler: `grep`/`glob` → abra só o trecho necessário (offset/limit). Não releia arquivo inalterado.
- Não cole arquivos inteiros, logs longos ou diffs extensos na resposta; mostre só o trecho que sustenta a conclusão.
- Uma tarefa por vez, diffs pequenos e focados. Nada de refatoração "de passagem".
- Durante a iteração rode só os testes afetados; a suíte completa roda antes do PR.
- Buscas amplas no código → subagente; consultas pontuais → ferramenta direta.
- Respostas curtas no formato da seção 10. Sem repetir o pedido, sem preâmbulo, sem resumo do óbvio.
- **Rigor não é negociável:** economia nunca justifica pular verificação, teste ou revisão de segurança.

## 4. Fluxo de trabalho e governança

1. Tarefa não trivial → **/nova-feature** (spec com critérios de aceite testáveis `AC-N`). Ambiguidade → **/clarificar**.
2. Branch por tarefa a partir de `develop`; PR para `develop`; `develop` → `main` só após staging validado.
   Push direto em `main` é bloqueado pelo hook `guard-push`.
3. Commits no padrão Conventional Commits, em português. **Sem co-autoria de IA** (hook `guard-coauthor`).
4. **Antes de abrir PR de código**, nesta ordem e tudo verde: **/revisar** → **/seguranca** → **/validar**,
   e rodar a **suíte de CI completa localmente no host via Docker** — os mesmos passos do workflow de CI
   (`.github/workflows/ci.yml`), com PostgreSQL em container. Achado P0/P1 de **/revisar**, vulnerabilidade
   explorável de **/seguranca** ou **CI vermelho** bloqueiam o PR. PR só de documentação/texto dispensa a
   suíte Docker (mas não **/revisar**).
5. Banco: toda mudança via **Alembic**, com `downgrade` funcional (**/migracao**).
6. Decisão difícil de reverter → ADR curto em `docs/decisoes/NNNN-titulo.md`.
7. Ao pausar ou encerrar: **/handoff** (atualiza `STATE.md`).

### Exigem aprovação explícita do responsável, sempre
- Migração destrutiva (drop/rename de coluna ou tabela, delete de dados).
- Qualquer mudança em **regras de envio** (janela, limites, idempotência, recorrência) ou em **regras de resposta da IA**
  (assuntos, modos, verificações, prompts, `OPENAI_MODEL`).
- Alterar infraestrutura/variáveis na Railway ou configurações no painel da Meta.
- Enviar mensagem para **qualquer número real**.
- Adicionar dependência nova (justificar: necessidade, manutenção, licença, alternativa nativa).

## 5. Invariantes do domínio (nunca violar)

1. Só o **worker** inicia mensagens agendadas; a API nunca envia agendamentos diretamente.
2. **Idempotência**: cada agendamento tem `chave_idempotencia` única; o worker trava com `FOR UPDATE SKIP LOCKED`.
   Nenhum caminho de código pode enviar a mesma mensagem duas vezes.
3. Mensagem que inicia conversa é **template aprovado, categoria UTILITY**. Texto livre só com janela de 24 h aberta,
   checada no banco no momento do envio.
4. Contato descadastrado (SAIR/PARAR) nunca recebe nada; o descadastro é imediato.
5. A IA **não envia nada** sem passar pelas verificações em código (BRIEFING §10.7); assunto fora da lista → humano.
6. O interruptor geral de respostas e a pausa de envios são checados **a cada ciclo**.
7. Testes nunca chamam as APIs reais da Meta/OpenAI: usar mocks ou o número de teste em staging.
8. Toda ação que muda estado gera registro de auditoria.

## 6. Segurança (baseline OWASP)

- Validar toda entrada com Pydantic; ORM/queries parametrizadas; nunca montar SQL por concatenação.
- Webhook: validar `X-Hub-Signature-256` com `hmac.compare_digest` antes de qualquer processamento.
- Segredos só em variáveis de ambiente; nunca em código, logs, testes, issues ou PRs (hook `guard-secrets`).
- Logs sem PII: telefones e tokens mascarados; texto de mensagens não vai para logs de erro.
- Autorização em todo endpoint (dependência de auth); 2FA no login; rate limit em login e webhook.
- **Texto de contato é dado não confiável** (risco de injeção de instruções na IA): nunca concatenar sem delimitação,
  nunca dar à IA ferramentas ou acesso a dados de outros contatos.
- Dependências com versão fixada; `pip-audit` e `npm audit` no CI; menor privilégio em tokens e acessos.

## 7. Observabilidade

- Logs estruturados (JSON) com `correlation_id` por agendamento, envio e mensagem recebida.
- Todo erro tratado registra contexto suficiente para reproduzir (sem PII) e é enviado ao Sentry.
- Mudança em fluxo crítico inclui a métrica/alerta correspondente (BRIEFING §12) no mesmo PR.

## 8. Qualidade de código

- Python 3.14 com type hints; `ruff` + `mypy` (estrito em `services/`, `worker/` e `respostas/`). Ver ADR 0003.
- TypeScript estrito no frontend; `eslint` + `tsc --noEmit`.
- Testes: pytest (unitários + integração com PostgreSQL real em container). Regras de envio, webhook e
  verificações da IA: cobertura mínima de **90%** de linhas e testes de borda explícitos.
- Nomes de domínio em português, como no BRIEFING (contatos, agendamentos, envios); termos técnicos em inglês.
- Funções pequenas, sem efeitos colaterais escondidos; datas sempre `timestamptz`, exibição em America/Sao_Paulo.

## 9. Definition of Done

- [ ] Critérios de aceite da spec cobertos por teste e passando.
- [ ] Lint, tipos e suíte completa verdes no CI.
- [ ] /revisar e /seguranca sem achados P0/P1.
- [ ] Logs, métricas e alertas do fluxo alterado presentes.
- [ ] Documentação afetada atualizada (BRIEFING/ADR/README) e `STATE.md` atualizado.
- [ ] Validado em staging quando tocar envio, webhook ou IA.

## 10. Formato de resposta ao concluir uma tarefa

```
Feito: <o que mudou, 1–3 linhas>
Evidência: <comandos/testes rodados e resultado>
Suposições: <explícitas, ou "nenhuma">
Riscos/pendências: <ou "nenhum">
Próximo passo: <um>
```

## 11. Skills do repositório

| Skill | Quando usar |
|---|---|
| /clarificar | Requisito ambíguo; uma pergunta por vez, com resposta recomendada |
| /nova-feature | Abrir feature com spec e critérios de aceite |
| /hipotese | Investigar bug ou decisão incerta pelo método falsificacionista |
| /meta-whatsapp | Qualquer código que toque a Cloud API, templates, webhook ou custos da Meta |
| /avaliar-ia | Mudança em prompts, assuntos, verificações ou modelo de IA |
| /migracao | Qualquer mudança de esquema do banco |
| /revisar | Code review do diff antes do PR |
| /seguranca | Security review do diff antes do PR |
| /validar | Provar critérios de aceite pelo gate executável e checar o Definition of Done |
| /handoff | Pausar ou retomar sessão via `STATE.md` |
