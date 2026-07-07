---
id: A33.l6
type: lane
title: "Retenção de artifacts: retention_until + prune diário + teste de cascade (W6-T05)"
sprint: A33
plan: PLAN-platform-review
status: planned
priority: P2
branch_slug: a33-l6-artifacts-retention
adrs: ["[[ADR-212]]"]
prompt: "[[TRACK-w6t05-artifacts-retention]]"
depends_on: ["[[A32.l5]]"]
parallel_with: ["[[A33.l4]]", "[[A33.l5]]"]
tags:
  - type/lane
  - sprint/a33
  - status/planned
  - priority/p2
  - area/pipeline
  - area/db
---

# A33.l6 — `artifacts-retention` (W6-T05 do [[PLAN-platform-review]])

## Problema

`pipeline_artifacts` ([[ADR-212]] DB-only) cresce sem política de
retenção — todo re-run acumula rows antigos indefinidamente. O track
[[TRACK-w6t05-artifacts-retention]] está `scoped` desde a A11 com plano
de 5 PRs; nunca virou lane.

## Gate de sequenciamento (por que depends_on A32.l5)

[[A32.l5]] (lifecycle de artifact E2: tombstone na reclassificação +
versão de extração consultável, [[ADR-311]]) mexe na **mesma tabela e na
mesma semântica de lifecycle**. Retenção que prune rows sem conhecer
tombstone/versão pode apagar exatamente o que a A32.l5 torna
consultável. Esta lane **só abre após o merge da A32.l5**, e o desenho
do prune deve respeitar tombstones e versões (não prunar a versão
corrente nem o tombstone que explica uma reclassificação).

## Escopo (5 PRs do track, revisados pós-A32.l5)

1. Migration Alembic: `retention_until` + revisão de FK/cascade.
2. Backfill de `schema_version`/`retention_until` para rows existentes.
3. Write-path: `DBArtifactStore.write` popula `retention_until` por
   política (config tipada, não dict — [[ADR-089]]).
4. Task diária `prune_artifacts` (Celery beat) com dry-run flag.
5. Teste de cascade + teste de que tombstone/versão corrente nunca são
   prunados.

## Critérios de aceite

1. Política de retenção documentada em config tipada com default
   conservador; co-design `data-engineer` na calibração.
2. Prune roda em dry-run no primeiro deploy (log estruturado do que
   *seria* apagado); flip para efetivo é PR separado da mesma lane.
3. Teste de cascade verde (KR5); zero regressão nos goldens de execução.
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
