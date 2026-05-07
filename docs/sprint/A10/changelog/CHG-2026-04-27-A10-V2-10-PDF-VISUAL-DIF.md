---
id: CHG-2026-04-27-A10-V2-10-PDF-VISUAL-DIF
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["19a79c7", "25003234190", "25003003442", "73218060762"]
summary: |
  v2.10 ✅ PDF visual diff em Playwright (2026-04-27). - **v2.10 ✅ PDF visual diff em Playwright (2026-04-27):** spec novo [`frontend/tests/e2e/reports/print.@critical.spec.ts`](frontend/tests/e2e/reports/print.@cri
tags:
  - type/changelog-entry
  - sprint/a10
---


# v2.10 ✅ PDF visual diff em Playwright (2026-04-27)

- **v2.10 ✅ PDF visual diff em Playwright (2026-04-27):** spec novo
  [`frontend/tests/e2e/reports/print.@critical.spec.ts`](frontend/tests/e2e/reports/print.@critical.spec.ts)
  renderiza `/reports/[id]?print=1` via CDP `Page.printToPDF()` (paridade
  com [`backend/app/services/pdf_renderer.py:109`](backend/app/services/pdf_renderer.py):
  A4 portrait, margens 15/12/15/12mm, `printBackground: true`), converte
  primeira página em PNG via `pdf-to-png-converter@^3.18.0` e compara
  contra baseline em
  [`frontend/tests/e2e/reports/__snapshots__/report.print.pdf.png`](frontend/tests/e2e/reports/__snapshots__/)
  usando `pixelmatch@^7.1.0` + `pngjs@^7.0.0` com tolerância
  `maxDiffPixels: 500`. **Por que PNG e não diff binário do PDF:** PDFs
  carregam timestamps + IDs de objetos que mudam por geração, gerando
  ~100% diff binário no mesmo render visual. **Job CI dedicado**
  `frontend-print-visual` em [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
  opt-in via label `print` (PR) ou `workflow_dispatch run_print=true`
  (paridade com `frontend-visual`); 2 inputs novos: `run_print` +
  `update_print_baseline`. Job fora do `all-green needs` — não bloqueia
  merge default; gate é deliberado. Spec faz skip silencioso fora de
  Chromium (CDP `Page.printToPDF` é Chrome-specific) e quando deps
  PDF→PNG não estão presentes (caminho de degradação para job
  cross-browser não rodar este spec por engano). Baselines
  OS-específicas (Linux/CI runner). **Gate empírico validado** via
  branch descartável `agent/test-print-visual-gate-throwaway/20260427-1212`
  (commit `19a79c7` — muda `@page margin: 15mm 12mm` → `25mm 22mm` em
  [report-print.css](frontend/src/components/report/report-print.css):
  CI run `25003234190` job `frontend-print-visual` falhou conforme
  esperado em `expect(diffPixels).toBeLessThanOrEqual(500)`. Branch
  fechada sem merge logo após. Run de baseline-generation:
  `25003003442` (job `73218060762`, conclusion=success). Refs:
  [REPORT_PREMIUM_PLAN.md §11.1](REPORT_PREMIUM_PLAN.md) ·
  [track_report_v2.md §3 v2.10](agent_prompts/track_report_v2.md).
