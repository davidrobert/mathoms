---
id: CHG-2026-05-06-FIX-BACKEND
type: changelog-entry
date: "2026-05-06"
sprint: A10
summary: |
  fix(backend): PDF semaphore (BB-009) + SECRET_KEY fail-fast prod (SR-022 · 2026-05-06). - **fix(backend): PDF semaphore (BB-009) + SECRET_KEY fail-fast prod (SR-022 · 2026-05-06):** W1-T04 + W1-T05 do PLATFORM_REVIEW_PLAN.
tags:
  - type/changelog-entry
  - sprint/a10
---


# fix(backend): PDF semaphore (BB-009) + SECRET_KEY fail-fast prod (SR-022 · 2026-05-06)

- **fix(backend): PDF semaphore (BB-009) + SECRET_KEY fail-fast prod (SR-022 · 2026-05-06):**
  W1-T04 + W1-T05 do PLATFORM_REVIEW_PLAN. Antes: `pdf_renderer.render_pdf`
  lançava Playwright Chromium sem cap — 4 PDFs simultâneos em CX32 (8GB)
  causavam OOM garantido (BB-009). E `SECRET_KEY` tinha default literal
  `"dev-secret-key-change-in-production"`; se prod subisse sem env, JWT
  era forjável (SR-022) e ainda `DATABASE_URL` podia ficar em sqlite com
  multi-worker quebrando silenciosamente (SR-021).
  Fix: (a) `asyncio.Semaphore` singleton lazy em
  `backend/app/services/pdf_renderer.py` lê `MATHOMS_PDF_CONCURRENCY`
  (default 2, range 1-8) — registrado em
  `docs/reference/STATELESS_AUDIT.md §2` categoria (b) por ser recurso local
  idempotente; (b) `@model_validator(mode="after")` em `Settings`
  rejeita prod com SECRET_KEY default/curta (<32 chars) ou
  DATABASE_URL=sqlite. Dev defaults intactos. Regression tests:
  `backend/tests/test_pdf_renderer.py` (5 calls simultâneas → max 2
  ativas), `backend/tests/test_config_prod_gates.py` (7 cenários).
