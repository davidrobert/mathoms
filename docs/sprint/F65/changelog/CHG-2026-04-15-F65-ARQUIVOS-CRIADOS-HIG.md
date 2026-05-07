---
id: CHG-2026-04-15-F65-ARQUIVOS-CRIADOS-HIG
type: changelog-entry
date: "2026-04-15"
sprint: F65
summary: "Arquivos criados (highlights). - 26 arquivos frontend de test (Vitest + Playwright) - 8 arquivos backend de test novos - 7 arquivos de infra: `docker-compose.test.yml`, `scripts/test_backend_"
tags:
  - type/changelog-entry
  - sprint/f65
---


# Arquivos criados (highlights)


- 26 arquivos frontend de test (Vitest + Playwright)
- 8 arquivos backend de test novos
- 7 arquivos de infra: `docker-compose.test.yml`, `scripts/test_backend_up.sh`/`_down.sh`, `.github/workflows/ci.yml`, `.github/CODEOWNERS`, `tests/fixtures/pdf_generator.py`, `tests/utils/{cpf,lint_no_real_pii}.py`
- 4 fixtures: `backend/tests/fixtures/{pipeline_runs,llm_mock}.py`, `frontend/scripts/{msw-lint,contract-check}.mjs`
- 3 scaffolds CI P1: `.lighthouserc.json`, `.size-limit.json`, `visual-regression.visual.spec.ts`
- 2 componentes novos: `ErrorBoundary.tsx`, wrap em `(app)/layout.tsx`
- 3 novas ADRs (069-071) + 1 nova doc (`SMOKE_TEST.md`) + `TESTING.md` expandido
