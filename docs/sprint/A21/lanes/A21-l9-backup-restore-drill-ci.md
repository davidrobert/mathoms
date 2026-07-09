---
id: A21.l9
type: lane
title: "Backup/restore mechanism + drill CI-local (subset W4-T01)"
sprint: A21
plan: PLAN-launch-trust
status: shipped
priority: P1
branch_slug: a21-l9-backup-restore-drill-ci
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a21
  - status/shipped
  - priority/p1
  - area/infra
---

# A21.l9 — Backup/restore mechanism + drill CI-local

> **Plano:** [[PLAN-launch-trust]] §F2-2.1 (subset de W4-T01 do [PLAN-platform-review](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md)).

## Contexto

W4-T01 (G1 backup + G2 rollback drill) tem duas metades: (i) o **mecanismo**
(scripts + runbook), testável contra Postgres efêmero em CI/local; (ii) o
**drill off-site real** (R2), que exige bucket/credencial (humano). Esta lane
entrega **só a metade (i)** — adianta ~70% de W4-T01 sem tocar prod nem
depender do owner.

## Escopo

- `dev/backup_postgres.sh` + `dev/restore_drill.sh`.
- Runbook de backup/restore (forma → co-revisar com `information-architect`;
  conteúdo operacional → `sre-devops`).
- Drill em CI: backup → restore contra container Postgres efêmero → medir RTO.

## Critério de aceite

- `restore_drill` recupera Postgres efêmero em CI, **RTO medido ≤ 30min**
  (A21-KR7 — KR4 **parcial**).
- Runbook commitado.

## Dependências e fronteira

- **Sem deps** — pickup imediato.
- **Não** escolhe provider de off-site nem aponta para R2 real (isso é
  build-vs-buy/sre-devops + credencial humana → A22). Esta lane entrega só o
  mecanismo testável.
- Puro código/CI — **sem passo humano, sem deploy em prod**.
