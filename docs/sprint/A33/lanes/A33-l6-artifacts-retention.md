---
id: A33.l6
type: lane
title: "Retenção de artifacts: retention_until + prune diário + teste de cascade (W6-T05)"
sprint: A33
plan: PLAN-platform-review
status: planned
ship_pr: null
ship_date: null
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
consultável — e o tombstone destrutivo da ADR-311 pode correr
concorrente com o prune por idade sobre as mesmas rows. Dois gates:

- Esta lane **só abre após o merge da A32.l5 E o flip da [[ADR-311]]
  para `Decidido`** — o predicado de prune depende de onde a versão
  corrente e o tombstone moram, e isso só fica firme na decisão.
- O **predicado de prune é parte do aceite**, não detalhe de
  implementação: `WHERE NOT (row é a versão corrente por
  (workspace, stage, artifact_key)) AND NOT (row é o tombstone mais
  recente de um document_id)` — escrito contra o schema final da
  ADR-311.

## Escopo (5 PRs do track, ordem revisada pelo data-engineer)

1. Migration Alembic: `retention_until` **nullable** (o cascade de
   entidade-pai já existe — `pipeline_artifact.py:59` tem
   `ON DELETE CASCADE` de run/workspace e `SET NULL` de document; esta
   lane adiciona prune **por idade em workspace vivo**, mecanismo
   distinto — não criar FK nova).
2. Write-path: `DBArtifactStore.write` popula `retention_until` por
   política (config tipada, não dict — [[ADR-089]]).
3. Backfill idempotente das rows antigas (`WHERE retention_until IS
   NULL`) — **depois** do write-path, para não abrir janela de rows
   novas sem política.
4. Task diária `prune_artifacts` (Celery beat) com dry-run flag e o
   predicado acima.
5. Teste de cascade pré-existente sob prune + teste de que
   tombstone/versão corrente nunca são prunados.

## Critérios de aceite

1. Política de retenção documentada em config tipada com default
   conservador; co-design `data-engineer` na calibração.
2. Prune roda em dry-run no primeiro deploy, logando **contagem +
   byte_size por (workspace, stage)** do que *seria* apagado — é esse
   dado que calibra a política; flip para efetivo é PR separado da
   mesma lane.
3. Teste de cascade verde + teste do predicado (versão corrente e
   tombstone sobrevivem ao prune) (KR5); zero regressão nos goldens de
   execução.
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
