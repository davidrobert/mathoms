---
id: PLAN-go-shell
type: plan
title: "Go shell (Caminho 1 da ADR-150) — port do pipeline-service para Go + Python via subprocess"
status: in_progress
sprint_origem: null
sprint_atual: null
sprints_envolvidas: []
created_at: "2026-07-02"
last_review: "2026-07-31"
adrs_canonical:
  - "[[ADR-150]]"
  - "[[ADR-303]]"
  - "[[ADR-112]]"
  - "[[ADR-113]]"
tags:
  - type/plan
  - area/pipeline
  - area/observability
  - status/in-progress
---

# PLAN-go-shell — Go shell (Caminho 1 da ADR-150)

> **Rationale mora na [[ADR-150]]** (estratégia, 3 caminhos, gatilhos, layout Go,
> acoplamentos out-of-band, cutover, coexistência) — este plano **não a duplica**;
> só mapeia a execução: fases, fila de pré-requisitos e tracks. Boundary de
> artefatos do executor remoto: [[ADR-303]]. Contrato HTTP: [[ADR-112]].
> Convenções/skeleton Go: [[ADR-113]].

## Origem e escopo

> **Atualização 2026-07-09:** o §Origem abaixo é o estado **à época** do plano.
> Desde então ADR-150 flippou `Roadmap → Decidido`, o **gatilho 4 foi disparado
> pelo owner** (emenda 2026-07-03), a **F1 concluiu 2026-07-06** e a F2 (cutover)
> iniciou — ver §F1 e §F2 abaixo.

A [[ADR-150]] está em `Roadmap`: **nenhum dos 4 gatilhos de destrava está ativo**
(revisita 2027-Q2 ou 100 workspaces pagantes). Em 2026-07-02 o owner autorizou o
**prep antecipado dos pré-requisitos** (A3.cli, A3.cli.otel, A3.cli.benchmark) —
interface estável barata, útil independente do Go (CLI do orchestrator serve
debug/ops local; benchmark refalsifica thresholds na revisita). **O primeiro PR
Go produtivo (F1) continua condicionado aos gatilhos da ADR-150** — este plano
não os reabre nem os antecipa.

Fora das sprints temáticas (A26/A27 = data-lineage): tracks vivem aqui, sem
`sprint:`/`lane:` no frontmatter, e **não** aparecem no `SPRINT_CURRENT.md`.

## Fases

### F0 — Pré-requisitos hard (ordem obrigatória da [[ADR-150]] §4) — ✅ concluída 2026-07-02 (exceto A3.codegen, ancorado a F1)

| Pré-requisito | Estado | Referência |
|---|---|---|
| A3.store — boundary de artefatos do executor remoto | ✅ entregue 2026-07-02 ([[ADR-303]] `Decidido`, #721+#723) | `artifact_session.py` + suíte no CI |
| A2.fix — Dockerfile do pipeline-service | ✅ entregue (A20.L2/L3) | [[ADR-150]] emenda item 1 |
| A3.cli — entry-point CLI `run-stage` no orchestrator (+ injeção `DBArtifactStore`) | ✅ entregue 2026-07-02 (PR #737) | [tracks/a3cli-orchestrator-cli.md](tracks/a3cli-orchestrator-cli.md) Fase 1 |
| A3.cli.otel — `TRACEPARENT` → span filho contínuo | ✅ entregue 2026-07-02 (PR #738) | [tracks/a3cli-orchestrator-cli.md](tracks/a3cli-orchestrator-cli.md) Fase 2 |
| A3.cli.benchmark — gate empírico de cold start (decide Caminho 2) | ✅ **gate PASSA** 2026-07-02: mediana 413ms ≤ 500ms; acumulado 4,1–7,4s/run ([PERFORMANCE_BASELINE §11](../../reference/PERFORMANCE_BASELINE.md)) | [tracks/a3cli-benchmark.md](tracks/a3cli-benchmark.md) |
| A3.codegen — `oapi-codegen` → `internal/contracts/` | ✅ entregue 2026-07-03 (F1 Fase 1): `types+chi-server` sobre o 3.0 derivado (conversor `dev/convert_openapi_31_to_30.py` — oapi-codegen não lê 3.1) + registry de stages (`dev/codegen_stage_registry_go.py`), ambos com check de sync no CI | [tracks/f1-go-service.md](tracks/f1-go-service.md) |

### F0.5 — Follow-ups pós-F0 — ✅ concluída 2026-07-03

Quatro slices executados após a F0 (co-design `senior-cto` + `sre-devops` +
`data-engineer`), fechando o §Escopo deferido da [[ADR-303]] e o B2 do
[GO_PORT_DEPS §6](../../reference/GO_PORT_DEPS.md):

| Slice | PR | Entrega |
|---|---|---|
| Paridade de hidratação HTTP/CLI | #742 | `run_context_factory` = fonte única dos 3 executores (config store, resolvers, budget ADR-173, tarefas.md) |
| Container/compose smoke | #743 | Imagem executa stages; gate `make smoke-pipeline-service` (runbook próprio; restrição SQLite WAL host↔container documentada) |
| Contract tests (B2) | #747 | Schemathesis no CI congela o contrato (404/400/503 agora documentados no OpenAPI) |
| Profiler A2.1 (parcial) | #749 | `dev/profile_pipeline_stages.py` + [PERFORMANCE_BASELINE §12](../../reference/PERFORMANCE_BASELINE.md); gatilho GIL segue owner-gated (rerun real) |

### F1 — Serviço Go (`services/pipeline-service-go/`) — ✅ CONCLUÍDA 2026-07-06 (4 fases: #780/#789/#791/+Fase 4)

**Gatilho 4 da [[ADR-150]] disparado pelo owner** (emenda 2026-07-03 — ADR
flippou `Roadmap → Decidido`). Layout, convenções e invariantes: [[ADR-150]]
§5-§6 + [[ADR-113]]. **Co-design concluído 2026-07-03** (`senior-cto` +
`sre-devops` + `product-manager`): **4 PRs** (Fase 1 skeleton+codegen+router;
Fase 2 StageExecutor — corte mínimo útil; Fase 3 RunCoordinator+eventos;
Fase 4 paridade+imagem+smoke) com KRs numéricos (imagem ≤150MB, cold start
shell <100ms, paridade monetária zero). Especificação executável e decisões
fechadas: [tracks/f1-go-service.md](tracks/f1-go-service.md).

### F2 — Cutover — 🚧 em execução (owner autorizou 2026-07-08)

Toggle único `MATHOMS_PIPELINE_SERVICE_URL`; gate técnico (3 runs E0→E5,
paridade byte-a-byte + WS events + spans com `TRACEPARENT`) + **gate humano
obrigatório** (smoke [SMOKE_TEST_HUMAN](../../reference/SMOKE_TEST_HUMAN.md)).
Detalhe: [[ADR-150]] §7 + emenda datada 2026-07-08 (critério do gate byte-a-byte
vs. não-determinismo LLM + correção do fallback de prod). Design executável +
runbook: [tracks/f2-cutover.md](tracks/f2-cutover.md) (co-design `senior-cto` +
`sre-devops`, 2026-07-08).

**A pré-condição registrada na [[ADR-303]] §Escopo deferido está FECHADA** (não
mais pendente): paridade de hidratação de contexto (`run_context_factory.py`,
PR #742) + enablement do smoke em container (PR #743).

> **Reancorado 2026-07-31 — o cutover roda no dogfood local** ([[ADR-150]] emenda
> datada). O owner decidiu continuar a migração no uso local, sem mudar a
> arquitetura de banco. A pré-condição "Postgres em staging" **caiu**: a
> incoerência WAL é host↔container e o overlay `go-on ENV=native` roda o binário
> Go no host; além disso **não existe produção** (#1130), logo staging Postgres
> seria menos representativo do alvo que o próprio dogfood. Postgres vira
> **re-gate diferido** para quando [[ADR-228]] G2/G3 abrir.

Fatias de F2 já em `main`: **#900** (A1 — `dev/go_parity_gate.py`, comparador
Tier-1/Tier-2 com controle Py↔Py anti-mascaramento) e **#919** (A2 — captura de
eventos WS via `dev/go_parity_capture.py`, envelope entra na paridade). O que
resta é gate + flip, não código de produto:

1. **Executável agora, sem infra:** `make go-parity` (orquestração — o harness
   hoje só consome `run_id`s), curadoria empírica da fixture 0-LLM nas **3**
   superfícies (E0-route [[ADR-081]], E2 `requires_llm_fallback`, narrativas
   [[ADR-144]]), entrada no [RUNBOOK](../../reference/RUNBOOK.md), job CI
   `go-parity-deterministic`.
2. **Owner:** rodar Tier-1 (3×Go vs 3×Py + controle) e Tier-2 (custo LLM), gate
   humano ([SMOKE_TEST_HUMAN](../../reference/SMOKE_TEST_HUMAN.md)).
3. **Flip + soak:** `go-on ENV=native` no workspace real, watch 3 runs, soak ≥2
   semanas (≥10 runs, ≥3 com LLM, zero rollback) antes de F3.

### F3 — Decommission do `pipeline-service/` Python — ⏸ bloqueada

≥2 semanas em prod sem rollback; ADR de remoção própria ([[ADR-150]] §8).

## Tracks

| Track | Escopo | Status | Gate de pickup |
|---|---|---|---|
| [TRACK-a3cli-orchestrator-cli](tracks/a3cli-orchestrator-cli.md) | A3.cli (Fase 1) + A3.cli.otel (Fase 2) — 2 PRs | `consumed` ✅ (#737 + #738) | — |
| [TRACK-a3cli-benchmark](tracks/a3cli-benchmark.md) | A3.cli.benchmark — medição + decisão Caminho 1 vs 2 | `consumed` ✅ (gate PASSA: 413ms) | — |
| [TRACK-f1-go-service](tracks/f1-go-service.md) | F1 — serviço Go em 4 fases/4 PRs + KRs | `consumed` ✅ (#780/#789/#791/Fase 4) | — |
| [TRACK-f2-cutover](tracks/f2-cutover.md) | F2 — gate técnico (Tier-1/Tier-2) + gate humano + flip no dogfood + soak | `ready` 🚧 (A1 #900 + A2 #919 em `main`; reancorado no dogfood local 2026-07-31) | fixture 0-LLM nas 3 superfícies (Postgres **não** é mais gate) |

## Critério de destrava de F1 (não recopiar — fonte única)

Os 4 gatilhos falsificáveis + revisita agendada: [[ADR-150]] §"Quando port se
justifica". Se o benchmark (F0) medir cold start mediano >500ms, **Caminho 2
reabre por emenda na ADR-150 antes de qualquer PR Go** — o gate é anterior a F1.

## Referências

- [[ADR-150]] — estratégia (fonte única de rationale)
- [[ADR-303]] — boundary de artefatos do executor remoto (A3.store)
- [GO_PORT_DEPS](../../reference/GO_PORT_DEPS.md) — inventário de dependências (A1, refresh 2026-07-02)
- [PERFORMANCE_BASELINE](../../reference/PERFORMANCE_BASELINE.md) — baseline empírico (A2)
- [pipeline-service.openapi.json](../../reference/api/v1/pipeline-service.openapi.json) — contrato HTTP
