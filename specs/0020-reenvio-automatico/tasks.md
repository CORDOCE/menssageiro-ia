# Tasks — 0020 Reenvio automático de envios (falha transitória)

TDD: teste que falha primeiro, depois implementação. Ordem de dependência; gate executável em cada task.
Tier Arquitetural (ADR 0014). Migração aditiva (/migracao). Allowlist Meta via /meta-whatsapp.

- [ ] **T1 — migração (aditiva):** colunas `envios.tentativas INT NOT NULL DEFAULT 0` e
      `envios.proxima_tentativa_em TIMESTAMPTZ NULL`; atualizar o enum `StatusEnvio` (`schemas/envio.py`) com
      `aguardando_retry`/`aguardando_decisao`. `downgrade` remove as colunas. — pré-requisito.
      Gate: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.
- [ ] **T2 — classificar a falha no client (/meta-whatsapp):** `WhatsappError` ganha `classe`
      (`retentavel`/`ambiguo`/`definitivo`); `whatsapp_client` mapeia `ConnectError`→retentável,
      `TimeoutException`/5xx→ambíguo, allowlist de códigos Meta→retentável, resto→definitivo. — AC-1..AC-4.
      Gate: `pytest tests/test_whatsapp_client.py -k classe`.
- [ ] **T3 — roteamento no disparo:** extrair "enviar-1-contato + aplicar desfecho" (`disparo.py:331-367`) num
      helper reusável (reenvio não re-reserva); rotear por classe/tentativas: retentável<3→`aguardando_retry`
      (+`proxima_tentativa_em`, backoff `{1:5,2:15,3:60}`min); retentável==3 e ambíguo→`aguardando_decisao`;
      definitivo→`falhou`. Auditoria `envio.retry_agendado`/`retry_esgotado`/`falha_ambigua`. — AC-5..AC-8.
      Gate: `pytest tests/test_worker_disparo.py -k "retry or classe or ambigu"`.
- [ ] **T4 — passo de reenvio no worker:** a cada ciclo, `select status='aguardando_retry' AND
      proxima_tentativa_em<=agora FOR UPDATE SKIP LOCKED`; **reavaliar elegibilidade** (reusa
      `_motivo_inelegivel`); elegível→reenvia pelo helper (T3); inelegível→`falhou`+motivo. Ligar em
      `__main__.executar()`. — AC-9, AC-10, AC-11.
      Gate: `pytest tests/test_worker_disparo.py -k reenvio`.
- [ ] **T5 — sweep de órfãos:** passo do worker recolhe `enviando` sem `wamid` com idade `> 15min`
      (`FOR UPDATE SKIP LOCKED`) → `aguardando_decisao` + alerta `envio.orfao_detectado`. — AC-12, AC-13.
      Gate: `pytest tests/test_worker_disparo.py -k orfao`.
- [ ] **T6 — endpoint + UI de reenvio manual:** `POST /envios/{id}/reenviar` (auth; 409 se não
      `aguardando_decisao`; zera `tentativas`, `aguardando_retry`, `proxima_tentativa_em=agora`, auditoria
      `envio.reenvio_manual`). Botão "Reenviar" no Histórico (só em `aguardando_decisao`) + selos dos status
      novos. — AC-14, AC-15, AC-16.
      Gate: `pytest tests/test_envios.py -k reenviar` · `npm run test` (frontend).
- [ ] **T7 — dependência 0019:** incluir `aguardando_retry` em `_CONTAM_LIMITE` (tentativa, não falha) e
      `aguardando_decisao` nas **falhas** da taxa da 0019 (`app/worker/alertas.py`). — AC-18.
      Gate: `pytest tests/test_alertas_agregacao.py`.
- [ ] **T8 — invariantes:** at-most-once (nunca 2ª linha; nunca reenvia ambíguo/definitivo) e teto 0016
      (reenvio conta e não ultrapassa). — AC-17, AC-19.
      Gate: `pytest tests/test_worker_disparo.py -k "idempot or teto"`.

## Gate final (antes do PR)
- [ ] `/revisar` + `/seguranca` sem P0/P1 · `/validar` AC-1..AC-19 · CI completo via Docker.
- [ ] Cobertura ≥90% nas linhas novas (§8). Migração com `downgrade` testado.
- [ ] ADR 0014 registrado (feito). STATE.md atualizado.
- [ ] **Staging:** validar reenvio real (forçar falha transitória) e o reenvio manual pela UI antes de `develop`→`main`.
