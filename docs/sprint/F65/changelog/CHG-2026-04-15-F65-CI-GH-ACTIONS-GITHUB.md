---
id: CHG-2026-04-15-F65-CI-GH-ACTIONS-GITHUB
type: changelog-entry
date: "2026-04-15"
sprint: F65
summary: |
  CI GH Actions (`.github/workflows/ci.yml`). - **CI GH Actions (`.github/workflows/ci.yml`):** 7 jobs — lint pre-commit, lint-pii, pipeline-tests, backend-tests + Redis service, frontend-tests (Vitest + JU
tags:
  - type/changelog-entry
  - sprint/f65
---


# CI GH Actions (`.github/workflows/ci.yml`)

- **CI GH Actions (`.github/workflows/ci.yml`):** 7 jobs — lint pre-commit, lint-pii, pipeline-tests, backend-tests + Redis service, frontend-tests (Vitest + JUnit), frontend-e2e (condicional: push main OU label `e2e` em PR) com PG+Redis services + alembic upgrade + Playwright cross-browser + artifacts 30d + all-green gate
