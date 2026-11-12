---
name: spec-metrics-prometheus
description: Spec da feature 0024-metrics-prometheus. Expor /metrics (Prometheus) protegido por token para a Central de Observabilidade raspar. Os critérios de aceite são o contrato e o oráculo de teste.
---

# Spec: 0024 Expor `/metrics` (Prometheus) protegido por token

> Tier **Pequeno** (spec + tasks). Endpoint de **leitura** máquina-a-máquina; **sem migração**, não
> toca regra de envio nem IA. Adiciona 1 dependência (`prometheus-fastapi-instrumentator`, aprovada
> por Jefferson 2026-11-12). Deploy/Railway e fiação na central ficam **fora desta spec** (passos
> separados, com aprovação).

## Contexto
A Central de Observabilidade (repo `Central-Observabilidade`) monitora sistemas em produção lendo um
endpoint `/metrics` no formato Prometheus, protegido por um Bearer token estático (ver o modelo
`modelos/fastapi.coleta.yml` da central: `authorization: Bearer` + `credentials_file`). O mensageiro-ia
hoje **não expõe `/metrics`** — só `/health`. Sem ele, o painel da central só consegue sonda externa
(no ar / fora do ar), sem SLO, latência p95, taxa de erro 5xx nem memória/CPU do processo. Esta spec
entrega esse endpoint, no formato que a central já consome.

## Suposições (explícitas, mínimas, reversíveis)
- **S1 (auth dedicada)** — A proteção do `/metrics` é um **token estático dedicado** (`METRICS_TOKEN`),
  **não** a sessão de usuário (ADR 0001/0004): o Prometheus não faz login. O token vai no header
  `Authorization: Bearer <token>`, como no modelo da central. Comparação em tempo constante.
- **S2 (fail-closed)** — Sem `METRICS_TOKEN` configurado, o endpoint **não é registrado** (responde
  **404**). Nunca expõe métricas sem proteção.
- **S3 (métricas padrão)** — O conjunto é o **padrão do `prometheus-fastapi-instrumentator`**
  (`http_requests_total`, `http_request_duration_seconds*`, `http_request_duration_highr_seconds*`) +
  as métricas de processo do `prometheus_client` (`process_resident_memory_bytes`,
  `process_cpu_seconds_total`), que é exatamente o que as regras da central traduzem. Sem métricas de
  negócio custom nesta fase.
- **S4 (máquina-a-máquina)** — A rota fica **fora do schema OpenAPI** (`include_in_schema=False`) e não
  participa do CORS do frontend. Só o processo `api` expõe (o `worker` não serve HTTP).

## Critérios de aceite (o contrato)
Cada AC é testável e não-ambíguo; um teste por AC.

- **AC-1 (sem credencial → 401)** — Dado `METRICS_TOKEN` configurado, Quando `GET /metrics` **sem**
  header `Authorization`, Então **401**.
- **AC-2 (token errado → 401)** — Dado `METRICS_TOKEN` configurado, Quando `GET /metrics` com
  `Authorization: Bearer <token-errado>`, Então **401**.
- **AC-3 (token certo → 200 Prometheus)** — Dado `METRICS_TOKEN` configurado, Quando `GET /metrics`
  com `Authorization: Bearer <token-certo>`, Então **200**, `content-type` de exposição Prometheus
  (`CONTENT_TYPE_LATEST` da lib — hoje `text/plain; version=1.0.0; charset=utf-8`) e o corpo contém
  `http_requests_total`.
- **AC-4 (desabilitado sem token → 404)** — Dado `METRICS_TOKEN` ausente ou vazio, Quando `GET /metrics`
  com **qualquer** credencial, Então **404** (rota não registrada; não vaza métricas).
- **AC-5 (comparação resistente a timing)** — A verificação do token usa `secrets.compare_digest`
  (não `==`), provado no nível da função que compara.
- **AC-6 (métricas de requisição presentes)** — Dado que o app atendeu ≥1 requisição a uma rota de
  domínio (ex.: `/health`), Quando `GET /metrics` autenticado, Então o corpo contém a família
  `http_request_duration_seconds` e o contador `http_requests_total` com o rótulo `handler`.
- **AC-7 (fora do OpenAPI)** — Dado o app, Quando `GET /openapi.json`, Então `/metrics` **não** aparece
  em `paths`.

## Casos de borda
- Esquema de auth errado (`Authorization: Basic ...` ou sem o prefixo `Bearer`) → **401** (trata como AC-2).
- `METRICS_TOKEN` = string vazia → equivalente a ausente → **404** (AC-4).
- Registro do instrumentator **idempotente**: montar o app duas vezes (ex.: na suíte de testes) não pode
  levantar "Duplicated timeseries in CollectorRegistry".
- `status` vem agrupado por classe (`2xx/4xx/5xx`) pelo instrumentator — comportamento esperado, as
  regras da central já contam com isso (não é bug).

## Fora de escopo (vinculante)
- **Deploy e variável na Railway** (`METRICS_TOKEN` no serviço `api`) — passo separado, exige aprovação.
- **Fiação na central** (`novo-sistema.sh`, `segredos/…`, `recarregar.sh`) — outro repo.
- **Métricas de negócio custom** (envios, fila, gasto) — fase futura; aqui só o padrão HTTP/processo.
- **Métricas do `worker`** — não serve HTTP; memória/CPU do worker ficam fora.
- **Proteção extra por IP/mTLS** — o token estático basta nesta fase (rede pública do Railway + Bearer).

## Matriz de decisão (registro × token → resposta)
| `METRICS_TOKEN` | `Authorization` enviado | resultado |
|---|---|---|
| ausente/vazio | qualquer (ou nenhum) | **404** (rota não existe) |
| configurado | nenhum | **401** |
| configurado | `Bearer <errado>` / esquema errado | **401** |
| configurado | `Bearer <certo>` | **200** + corpo Prometheus |
