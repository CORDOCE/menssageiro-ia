# Runbook — Fase 0: ativar o número +55 real na Cloud API (migração)

> Levantado 2026-11-12 consultando a doc oficial da Meta (fontes no fim). **Caminho escolhido: MIGRAÇÃO**
> (o número passa a ser operado 100% pelo mensageiro). Decisão de Jefferson 2026-11-12.
>
> **⚠️ Trade-off aceito (irreversível na prática):** ao migrar, o número **deixa de funcionar no app
> WhatsApp Business do celular** e o **histórico atual se perde**. Se o cliente ainda precisar do app no
> celular, PARE — o caminho seria coexistência (Embedded Signup v4 / parceiro BSP), bem mais complexo.
>
> **§4:** mexe no painel da Meta, em credenciais e envia a número real → cada passo sensível exige o OK do
> responsável. O **código já está pronto** (cliente Cloud API, webhook HMAC, templates, worker) — a Fase 0
> é configuração, não desenvolvimento.

## Legenda
- 🧑 = Jefferson, no painel da Meta (fora do código).  ⚙️ = eu (Railway / validação).

## Fase A — Meta (🧑 no `business.facebook.com` + `developers.facebook.com`)
1. **Portfólio de negócio + verificação.** Ter um Business Portfolio (Business Manager). A **verificação do
   negócio** sobe o limite de 250 → 2.000 destinatários/24h (pode começar sem, com 250/dia).
2. **Meta App.** App Dashboard → **Create App** → use case **"Connect customers through WhatsApp"** → associar
   ao portfólio. (Pode reusar o app de teste existente — ver STATE: app id `2093735544592019`.)
3. **Adicionar o número real à conta de mensagens (WABA).** No produto WhatsApp → **API Setup** → adicionar o
   número +55. Como o número **está no app WhatsApp Business**, primeiro **remova-o do app** (ou será migrado):
   a Meta pede a verificação por **SMS/voz** e a definição de um **PIN de verificação em duas etapas** (two-step)
   — **guarde o PIN**, é necessário para registrar o número na Cloud API.
4. **Pagamento em BRL.** Nas configurações da conta/WABA, adicionar **cartão da empresa** e moeda **BRL**
   (sem método de pagamento, a Meta bloqueia os envios).
5. **System User + token permanente.** Business Settings → **System users** → criar um system user → atribuir
   **assets** (o app + a conta WhatsApp, com *Full control*) → **Generate token** com as permissões:
   `business_management`, `whatsapp_business_messaging`, `whatsapp_business_management`. **Guarde o token**
   (é o `WHATSAPP_TOKEN` permanente).
6. **Coletar os IDs/segredos** e me passar (nunca em repositório/issue):
   - `PHONE_NUMBER_ID` (API Setup, do número +55 — **não** o de teste).
   - `WABA_ID` = "Messaging account ID" (a WABA virou "Messaging account" em 2026; o id antigo segue valendo).
   - `APP_SECRET` (App → Settings → Basic → App Secret).
   - `WHATSAPP_TOKEN` (passo 5).

## Fase B — Fiação no sistema (⚙️ eu, com você aprovando §4)
7. **Setar as credenciais na Railway — STAGING primeiro** (serviço `backend` **e** `worker`):
   `WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`, `WABA_ID`, `APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`, `GRAPH_API_VERSION`
   (confirmar a versão atual na doc no dia). `WEBHOOK_VERIFY_TOKEN` já gerado: **`Xhr-76zMdpJsMydPwIfc4BejVmHneu5A`**.
8. **Webhook (🧑 no painel do App, com o valor que eu confirmo).** No produto WhatsApp → **Configuration** →
   Callback URL = `https://menssageiro-ia-backend-staging.up.railway.app/webhook/meta` + Verify token =
   `WEBHOOK_VERIFY_TOKEN` (acima) → **Verify and save** (o backend responde ao `GET` de verificação). Assinar os
   campos: **`messages`** e **`message_template_status_update`**.
9. **Registrar o número na Cloud API** (se o painel não registrar sozinho): com o **PIN** do passo 3. (O cliente
   Cloud API do repo já envia; o registro é pré-requisito único por número.)

## Fase C — Validação em STAGING (⚙️ nós, §4: envio a número real)
10. **Sincronizar modelos** pela tela Modelos (`POST /modelos/sincronizar`) → lê os templates da WABA.
11. **Criar/aprovar 1 template UTILITY `pt_BR`** (ex.: um comunicado simples; o cliente fornece o texto).
    Aguardar `message_template_status_update` → `aprovado`.
12. **Teste de ponta a ponta:** cadastrar **um contato de teste = um número de DESTINO diferente do número
    operador** (ex.: o celular pessoal do responsável; o número do mensageiro é o remetente, não envia para si),
    com consentimento registrado; agendar um envio desse template para daqui a 1–2 min, e confirmar: envio sai no
    horário, chega no celular de destino, e os **status** (enviado/entregue/lido) voltam pelo webhook e aparecem
    no Histórico. (**§4: enviar a número real exige seu OK no momento.**)

## Fase D — Produção
13. Repetir o passo 7 (credenciais) no **produção** (backend + worker) + webhook apontando para
    `menssageiro-ia-backend-production.up.railway.app/webhook/meta`. Smoke: `/webhook/meta` responde ao `GET` de
    verificação; um envio real de teste confirma a entrega. Aí o mensageiro está **operacional de verdade**.

## Variáveis de ambiente da Fase 0 (Railway, backend + worker)
`WHATSAPP_TOKEN` · `PHONE_NUMBER_ID` · `WABA_ID` · `APP_SECRET` · `WEBHOOK_VERIFY_TOKEN` · `GRAPH_API_VERSION`
(o `WHATSAPP_TEST_NUMBER` de staging pode sair — era allowlist do envio de teste.)

## Fontes (doc oficial Meta, consultada 2026-11-12)
- Get Started (Cloud API): https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started
- Coexistência / onboarding de número do app Business (por que migração perde app+histórico):
  https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users/
- Migrar número existente: https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/migrate-existing-whatsapp-number-to-a-business-account

> Nota 2026: Embedded Signup **v2 deprecado em 15/out/2026** (usar v4 se um dia for coexistência). A WABA está se
> dividindo em WhatsApp account + Messaging account; **ids e chamadas existentes seguem funcionando**.
