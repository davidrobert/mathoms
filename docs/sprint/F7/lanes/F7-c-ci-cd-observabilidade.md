---
id: F7.c
type: lane
title: "CI/CD + Observabilidade (semana 3-4)"
sprint: F7
status: open
priority: P0
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f7
  - status/open
  - priority/p0
---


# 7C — CI/CD + Observabilidade (semana 3-4)


| #    | Tarefa                                                                                         | Prio | Est. | Status |
| ---- | ---------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7C.1 | GH Actions CI (lint ruff + pytest + PG service + Docker scan CVE + coverage ≥95% new code)    | P0   | 6h   | ☐      |
| 7C.2 | GH Actions CD (push GHCR + SSH deploy + `alembic upgrade head` + compose pull + health check) | P0   | 4h   | ☐      |
| 7C.3 | Rollback automatizado (health check 3x fail → `.env.rollback`, `scripts/rollback.sh`)          | P0   | 3h   | ☐      |
| 7C.4 | Sentry setup (backend + frontend, DSN, environment tags, release tracking, perf 10%)           | P1   | 4h   | ☐      |
| 7C.5 | Structured logging (structlog JSON prod, request_id UUID, Celery task_id correlation)          | P1   | 4h   | ☐      |
| 7C.6 | Uptime monitoring (UptimeRobot, /health + frontend, email alerts)                              | P1   | 1h   | ☐      |
| 7C.7 | Runbook (`docs/RUNBOOK.md` — deploy, rollback, backup, secret rotation, scaling, first week)   | P1   | 5h   | ☐      |
