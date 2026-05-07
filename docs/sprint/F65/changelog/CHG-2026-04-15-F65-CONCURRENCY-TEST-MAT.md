---
id: CHG-2026-04-15-F65-CONCURRENCY-TEST-MAT
type: changelog-entry
date: "2026-04-15"
sprint: F65
summary: "Concurrency test `materialize_config`. - **Concurrency test `materialize_config`:** 3 tests (2 workspaces paralelos, idempotency do mesmo ws, 10 workspaces simultâneos com `ThreadPoolExecutor`) — SQL"
tags:
  - type/changelog-entry
  - sprint/f65
---


# Concurrency test `materialize_config`

- **Concurrency test `materialize_config`:** 3 tests (2 workspaces paralelos, idempotency do mesmo ws, 10 workspaces simultâneos com `ThreadPoolExecutor`) — SQLite file-based + `check_same_thread=False` para thread-safety
