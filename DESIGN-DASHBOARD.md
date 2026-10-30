# DESIGN — Dashboard do Mensageiro (proposta v1)

> Requisitos visuais e de layout para o frontend (PWA). Status: **layout aprovado pelo cliente em 29/10/2026**. Sem logo ou cores próprias do cliente por enquanto: usar a paleta abaixo. Complementa o `BRIEFING.md`.

## 1. Princípios
1. **Calmo e confiável**: é uma ferramenta de cobrança; nada chamativo. Cor só onde carrega significado.
2. **Uma ação principal por tela**: "Nova mensagem" é o único botão de destaque.
3. **Status sempre com cor + texto** (nunca só cor).
4. **Celular primeiro nas ações rápidas** (aprovar, ver hoje), **computador para o trabalho longo** (agenda, contatos).
5. **Sem verde WhatsApp como cor da marca**: evita confusão com o app oficial e mantém o verde reservado para "entregue/lida".

## 2. Paleta

### Tema claro
| Token | Uso | Hex |
|---|---|---|
| `--cor-primaria` | Botão principal, links, item ativo | `#2B59C3` |
| `--cor-primaria-hover` | Hover/pressionado | `#234AA3` |
| `--fundo` | Fundo da página | `#F6F7F9` |
| `--superficie` | Cartões, painéis | `#FFFFFF` |
| `--superficie-2` | Indicadores, menu lateral | `#F0F2F5` |
| `--borda` | Divisórias, contornos | `#E2E5EA` |
| `--texto` | Texto principal | `#1A1D23` |
| `--texto-2` | Texto de apoio | `#5A6270` |
| `--texto-3` | Legendas, horários secundários | `#8A919C` |

### Tema escuro
| Token | Hex |
|---|---|
| `--cor-primaria` | `#6F93E8` |
| `--fundo` | `#0F1115` |
| `--superficie` | `#171A20` |
| `--superficie-2` | `#1E222A` |
| `--borda` | `#2A2F38` |
| `--texto` | `#E8EAEE` |
| `--texto-2` | `#A3AAB5` |
| `--texto-3` | `#7A828E` |

### Status (selos)
| Status | Fundo (claro) | Texto (claro) | Fundo (escuro) | Texto (escuro) |
|---|---|---|---|---|
| Agendada / Enviada | `#E8EEFB` | `#234AA3` | `#1C2A4A` | `#8FB0F2` |
| Entregue / Lida | `#E5F4EC` | `#18794E` | `#16352A` | `#5CC48F` |
| Aguardando aprovação / Modelo em análise / Sugestão | `#FBF1DC` | `#8A5A0B` | `#3A2E14` | `#E3B058` |
| Não enviada / Modelo recusado | `#FBE9E9` | `#B42318` | `#3E1D1C` | `#F08A80` |
| Cancelada / Descadastrado | `#EEF0F3` | `#5A6270` | `#262A31` | `#A3AAB5` |

Modos de conversa reaproveitam as mesmas cores: **Automático** = azul · **Aprovação** = âmbar · **Manual** = cinza ·
**Precisa de você** = âmbar com ponto indicador.

Todas as combinações de texto/fundo devem passar **WCAG AA (4,5:1)**; validar no CI com uma checagem de contraste.

## 3. Tipografia
- Fonte: **Inter** (Google Fonts), fallback `system-ui`.
- Base: 14 px no computador; **16 px em campos no celular** (evita zoom automático no iPhone).
- Títulos de página 20 px / peso 600; seções 15 px / 600; texto 14 px / 400; legendas 12 px.
- Números (horários, valores, indicadores) com `font-variant-numeric: tabular-nums`.

## 4. Layout

### Computador (≥ 1024 px)
- Menu lateral fixo (232 px): logo, botão **Nova mensagem**, Hoje, **Conversas** (contador de "precisam de você"), Agenda, Sugestões (contador), Contatos, Modelos, Histórico, Configurações; rodapé com "Saúde do sistema", interruptor **Respostas automáticas** (liga/desliga) e conta.
- Conteúdo com largura máxima de 1200 px, grade de 12 colunas, espaçamento base de 8 px.

### Tablet (640–1023 px)
- Menu lateral recolhido em ícones; demais regras iguais.

### Celular (< 640 px)
- Barra inferior com 4 itens: **Hoje, Conversas, Agenda, Mais** (Sugestões fica em Hoje e em Mais, com contador).
- Botão flutuante **+** (Nova mensagem) acima da barra.
- Listas viram cartões empilhados; indicadores em grade 2 × 2.
- Alvos de toque com no mínimo 44 × 44 px.

## 5. Tela "Hoje" (dashboard) — revisada com o cliente em 29/10/2026

Feedback do cliente (Pedro): layout aprovado ("simples e direto"); o volume diário será baixo, então a
lista principal deve mostrar **todos os envios programados**, com a **data acima do horário**.

Ordem dos blocos:
1. **Cabeçalho**: "Hoje", data por extenso e selo de saúde ("Sistema ok" / "Atenção" / "Envios pausados").
2. **Faixa "não enviadas"** (só quando houver): uma linha por problema, em vermelho claro, dizendo
   quem, quando e o motivo em linguagem simples (ex.: "O número não tem WhatsApp"), com o botão **Resolver**
   (editar contato, reagendar ou tentar de novo). Some quando resolvido.
   Também usa essa faixa para: envios pausados, modelo recusado, sistema parado.
3. **Indicadores** (4): **Programadas** (total futuro) · **Entregues no mês** · **Não enviadas** · **Gasto no mês**.
   - O termo "Falhas" foi trocado por **"Não enviadas"** (mais claro para o operador).
   - Clicar em um indicador abre a lista filtrada correspondente.
4. **Envios programados** (2/3 da largura) — antes "Envios de hoje":
   - Mostra **apenas envios futuros**, de qualquer data, em ordem cronológica.
   - Coluna de data/hora empilhada: **data `dd/mm` em cima (peso 500)**, **horário `HH:mm` embaixo (texto secundário)**.
     Sem ano; se o envio for em outro ano, mostrar `dd/mm/aa`.
   - Demais colunas: contato (ícone de repetição se recorrente), tipo/modelo (+ "boleto PDF" quando houver anexo), selo de status.
   - Status possíveis aqui: Agendada · Aguardando aprovação · Modelo em análise.
   - Limite de **8 linhas**; rodapé "Ver todos na agenda (N)" quando houver mais.
   - Ações por linha (menu ou deslizar no celular): ver mensagem, editar, cancelar.
   - Envios já realizados (entregue, lida, não enviada) **não aparecem aqui**: ficam no Histórico, e os problemas sobem para a faixa do item 2.
5. **Coluna lateral** (1/3):
   - **Sugestões da IA**: até 3 cartões com motivo curto e botões Aprovar / Revisar; link "Ver todas".
   - **Conversas que precisam de você** (substitui "Respostas recebidas"): conversas repassadas pela IA ou com
     rascunho aguardando aprovação, com motivo curto ("pediu para falar com alguém", "assunto não liberado",
     "rascunho para aprovar") e botões **Aprovar** (quando houver rascunho) / **Abrir**.
6. **Faixa de alerta** também cobre: respostas automáticas desligadas, gasto de IA perto do teto, conversa além do prazo de resposta.

Comportamento:
- Atualização automática a cada 30 s (e imediata ao voltar para a aba/app).
- Estado vazio: "Nenhum envio programado. Programe sua próxima mensagem." + botão Nova mensagem.
- Carregamento com esqueletos (sem spinners de tela cheia).
- No celular, a lista de envios programados é o primeiro bloco após os indicadores.

Glossário para o operador (usar estes termos na interface):
- **Programada/Agendada**: vai sair na data e hora marcadas.
- **Entregue / Lida**: chegou ao celular do contato / o contato abriu.
- **Não enviada**: o WhatsApp não conseguiu entregar (número sem WhatsApp ou inválido, contato bloqueou a empresa,
  modelo recusado ou pausado pela Meta, falta de pagamento na conta da Meta). O sistema mostra o motivo e o que fazer.
- **Modelo em análise**: mensagem de um tipo novo aguardando aprovação do WhatsApp.

## 6. Outras telas (resumo visual)
- **Nova mensagem**: assistente em 4 passos com barra de progresso; à direita (ou abaixo, no celular) uma **prévia no formato de balão de conversa**, neutra (sem imitar a interface oficial do WhatsApp). Botão secundário **Melhorar com IA** ao lado do campo de texto, mostrando a sugestão lado a lado com o original.
- **Agenda**: alternância Lista / Semana / Mês; cores de status nos eventos; filtro por tipo.
- **Sugestões**: lista com Aprovar, Editar, Recusar; aprovação em lote.
- **Contatos**: tabela no computador, cartões no celular; selo de consentimento e de descadastro.
- **Modelos**: status de aprovação da Meta, motivo de rejeição, variáveis com exemplos.
- **Histórico**: filtros por período, status e contato; exportar para Excel.
- **Saúde do sistema**: último ciclo do worker, fila, falhas do dia, qualidade do número, gasto do mês.

### Conversas (nova)
- **Computador**: duas colunas — lista de conversas à esquerda (filtros: Precisam de você · Automáticas · Todas),
  conversa aberta à direita no formato de balões.
- **Celular**: lista em tela cheia; tocar abre a conversa.
- Cada mensagem enviada mostra a **origem** com um selo discreto: Você · IA (automática) · IA (aprovada) · Agendada · App do celular.
- Topo da conversa: **seletor de modo** (Aprovação · Automático · Manual) e botão **Assumir** (vai para Manual na hora).
- Rascunho da IA aparece acima do campo de texto, com **Aprovar**, **Editar** e **Descartar**, e uma linha
  "Por quê?" que abre o rastro: assunto detectado, confiança, regra aplicada e verificações.
- Mensagem bloqueada pelas verificações aparece para o operador (nunca para o contato) com o motivo.

### Base de respostas (nova)
- Lista de perguntas frequentes por assunto, com a resposta aprovada e os dados do contato que podem ser usados
  (ex.: valor, vencimento). Editar cria nova versão.

### Regras (nova)
- Tabela de assuntos com o modo permitido (Proibido · Aprovação · Automático), número de rascunhos aprovados sem
  edição e o botão **Liberar automático** (habilitado só após 30 aprovações sem edição).
- Configurações de horário, limite por conversa, teto de gasto de IA e prazo de resposta humana.

## 7. Componentes
- Botões: primário (só "Nova mensagem" e confirmação final do assistente), secundário (contorno), fantasma (ações de linha).
- Selos de status (seção 2), sempre com texto.
- Cartões com borda de 1 px e cantos de 12 px; sem sombras pesadas.
- Avisos curtos (toast) no canto inferior; confirmação explícita para cancelar envios.
- Ícones: Tabler Icons ou Lucide (traço, não preenchidos).

## 8. Acessibilidade e texto
- Foco visível em todos os elementos interativos; navegação por teclado completa.
- Rótulos em todos os campos; mensagens de erro dizendo o que aconteceu e o que fazer.
- Textos em português, frases curtas, verbo primeiro nos botões ("Agendar envio", "Aprovar").
- Datas no formato brasileiro (29/10/2026, 14:00) e valores em R$.

## 9. PWA
- Nome: "Mensageiro"; ícone simples (avião de papel ou balão) na cor primária sobre fundo branco.
- `theme_color` = cor primária; `background_color` = fundo.
- Tela inicial ao abrir: **Hoje**.
- Notificações push: conversa que precisa de você, rascunho para aprovar, sugestão nova, mensagem não enviada, alerta de sistema.

## 10. Tema (claro, escuro, sistema) — decidido em 29/10/2026
- Seletor com três opções: **Claro**, **Escuro** e **Seguir o sistema** (padrão no primeiro acesso).
- Local: Configurações → Aparência, e atalho no menu da conta (ícone sol/lua).
- Implementação: atributo `data-theme="light|dark"` no `<html>`; "Seguir o sistema" remove o atributo e usa
  `prefers-color-scheme`, reagindo em tempo real à troca do aparelho.
- Persistência: salvar a escolha no perfil do usuário (backend) e espelhar em `localStorage` para aplicar
  **antes da primeira pintura** (script inline no `<head>`), evitando o "piscar" de tema errado.
- `theme_color` do PWA acompanha o tema ativo (meta tag com `media` para claro e escuro).
- Todos os componentes usam apenas os tokens da seção 2; nenhuma cor fixa no código.

## 11. Identidade visual
- O cliente **não tem logo nem cores próprias** por enquanto. Usar a paleta da seção 2 e um ícone simples
  (avião de papel ou balão) na cor primária.
- Manter as cores em tokens para que uma futura identidade troque só `--cor-primaria` (e o ícone), sem mexer nos status.
