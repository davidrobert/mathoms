---
id: ADR-096
type: adr
title: "Observabilidade de cutover"
status: Proposto
phase: "execução paralela à Fase 2"
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 096"]
tags:
  - area/ops
  - area/pipeline
  - status/proposto
  - type/adr
size_lines: 64
---

# ADR-096 — Observabilidade de cutover

**Status:** Proposto (execução paralela à Fase 2) • **Data:** 2026-04-19 • **Plano:** §16

**Contexto:** §4.6 do plano descreve o **procedimento** de cutover, mas não
**como detectar** que deu errado. Ativar `MATHOMS_USE_DB_ARTIFACTS=True` em
workspace com dados históricos precisa de validação contínua — ficaria
invisível se diferenças estruturais aparecessem no output.

**Decisão:** Kit operacional de 4 peças:

**1. Script de comparação disk-vs-db** — `_scratch/compare_disk_vs_db.py`:

```
python compare_disk_vs_db.py --workspace-id <uuid> [--stage STAGE] [--strict]

Saída:
  - 0: sem diff estrutural
  - 1: diff detectado (com detalhes)
  - 2: erro de leitura (um dos stores não tem o artifact)
```

Lista `(stage, key)` em cada store; para cada par presente nos dois, compara
estruturalmente com tolerância para floats. Reporta: artefatos só em disk,
só em DB, diferentes, idênticos.

**2. Métricas em produção** (`backend/app/observability/cutover_metrics.py`):

| Métrica | Tipo | Uso |
|---------|------|-----|
| `pipeline_run_duration_seconds{store="disk\|db"}` | Histogram | Regressão perf |
| `artifact_write_count{stage, store}` | Counter | Saúde de escrita |
| `artifact_read_missing{stage}` | Counter | Detectar cutover incompleto |
| `artifact_diff_count{stage}` | Counter | Incrementado pelo compare em job nightly |
| `pipeline_run_failed_total{stage, use_db}` | Counter | Taxa de falha por modo |

Expostas em `/metrics` (Prometheus). Dashboard durante janela de cutover
com os 5 painéis.

**3. Alertas**:

| Alerta | Condição | Ação |
|--------|----------|------|
| `CutoverRegression` | p95(duration_db) > baseline × 1.5 por 15min | Reverter deploy ou flag |
| `ArtifactReadMissing` | rate(read_missing) > 0 | Investigar |
| `DiskDbDiffDetected` | diff_count > 0 por stage | Pausar cutover |
| `PipelineFailureSpike` | rate(failed{use_db=True}) > 2× rate({use_db=False}) | Flip back |

**4. Runbook** — `docs/RUNBOOKS/cutover.md` com procedimento T-24h / T-0 / T+48h.

**Status de implementação:**

- Fase 1 entregou baseline placeholder em `tests/pipeline/perf/`.
- Scripts `compare_disk_vs_db.py`, métricas Prometheus, dashboard Grafana:
  **pendentes** — devem ser entregues antes de qualquer cutover em produção
  (pré-Fase 4.6).

**Consequências:**
- ✅ Cutover reversível com sinal claro de problema.
- ✅ Métricas contínuas validam paridade em background.
- ⚠️ Requer stack Prometheus/Grafana (não existe em dev hoje).
- ❌ Alertas dependem de receiver configurado (PagerDuty/Slack).
