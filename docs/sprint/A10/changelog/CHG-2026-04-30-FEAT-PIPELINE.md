---
id: CHG-2026-04-30-FEAT-PIPELINE
type: changelog-entry
date: "2026-04-30"
sprint: A10
adrs: ["[[ADR-157]]"]
summary: |
  feat(pipeline): IRPF full schema (E1.6 / `extract_irpf_full`) — Sprint A8 (2026-04-30). - **feat(pipeline): IRPF full schema (E1.6 / `extract_irpf_full`) — Sprint A8 (2026-04-30):** novo stage paralelo a `extract_baseline` que captura **todo** o co
tags:
  - type/changelog-entry
  - sprint/a10
---


# feat(pipeline): IRPF full schema (E1.6 / `extract_irpf_full`) — Sprint A8 (2026-04-30)

- **feat(pipeline): IRPF full schema (E1.6 / `extract_irpf_full`) — Sprint A8 (2026-04-30):**
  novo stage paralelo a `extract_baseline` que captura **todo** o conteúdo
  financeiro de declarações IRPF (rendimentos PJ/PF/exterior, isentos,
  exclusiva, pagamentos dedutíveis, dependentes, dívidas, imposto
  apurado, bens & direitos). Hoje o E1.5 só extrai Bens & Direitos
  (~30% do PDF); este commit destrava 6 KPIs novos: renda anual líquida,
  alíquota efetiva dupla (RFB-style + Cerbasi-style), capacidade PGBL
  não usada, split trabalho×capital (Perini), evolução de renda
  multi-anos. Schema `IRPFFullOutput` (Pydantic) + JSON Schema
  espelhado, prompt LLM dedicado, validator com anti-PII em campos
  livres + reconcile cross-field obrigatória, stage runner com cap
  de confidence em 0.7 quando reconcile falha + WARNING em
  `mathoms.pipeline.e16` para campos top-level desconhecidos,
  `IRPFAnalyzer` com queries puras. E5 consome via try-read opcional
  (workspaces sem IRPF não regridem). Coexiste com E1.5 — cutover de
  Bens & Direitos (E1.5 → E1.6) é deliberadamente fora desta lane,
  flag `MATHOMS_E16_SUPERSEDES_E15_BENS` definida para sprint futura.
  G0 (financial-planner) + G2 (data-engineer) + G1 (senior-cto) sign-off
  na ADR-157. 22 testes unitários cobrem schema/validator/analyzer.
  Frontend (componentes do relatório premium) fica em lane separada com
  G4 (product-designer) review.
  [ADR-157](DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)
