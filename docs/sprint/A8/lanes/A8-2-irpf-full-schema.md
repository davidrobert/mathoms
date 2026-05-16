---
id: A8.2
type: lane
title: "IRPF full schema (E1.6 — pipeline + analyzer + E5 wire)"
sprint: A8
status: shipped
branch_slug: irpf-full-schema
ship_date: "2026-04-30"
adrs: ["[[ADR-157]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a8
  - status/shipped
---


# A8.2 — IRPF full schema (E1.6 — pipeline + analyzer + E5 wire)

> Migrada de tabela em `## Sprint A8` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Depende de:** A7 ✅
- **Branch slug:** `irpf-full-schema`

## Status (legado)

🚧 pipeline + tests ✅ entregues 2026-04-30 (ADR-157 + schema + prompt + validator + stage + analyzer + E5 wire + 22 tests); **goldens** ✅ entregue 2026-04-30 ([track](../../A11/tracks/irpf-full-schema-goldens.md): 3 fixtures sintéticas completo/simplificado/edge_cases + 28 tests stage runner com `FakeStructuredLLMClient` em [tests/fakes/llm.py](../../../../tests/fakes/llm.py)); **UI** (S_IRPF_RENDA + S_IRPF_OTIMIZACAO no relatório premium) ✅ entregue 2026-04-30 via [track_irpf_full_schema_ui.md](../../A11/tracks/irpf-full-schema-ui.md) — YAML+codegen, 2 sections, 5 cards, 2 charts (Chart.js), narrow guard `isIrpfKpis`, hook `useIrpfKpis`, 16 testes, degrada gracioso quando workspace sem IRPF. Pendente: G0/G4 sign-off em PR comment + visual baselines + Playwright `@critical`
