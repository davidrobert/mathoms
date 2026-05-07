---
id: CHG-2026-04-30-FEAT-REPORT
type: changelog-entry
date: "2026-04-30"
sprint: A10
adrs: ["[[ADR-076]]", "[[ADR-157]]"]
summary: |
  feat(report): seções IRPF no relatório premium — UI lane (2026-04-30). - **feat(report): seções IRPF no relatório premium — UI lane (2026-04-30):** materializa os 6 KPIs do `IRPFAnalyzer` (já em produção via E5 try-read) em duas se
tags:
  - type/changelog-entry
  - sprint/a10
---


# feat(report): seções IRPF no relatório premium — UI lane (2026-04-30)

- **feat(report): seções IRPF no relatório premium — UI lane (2026-04-30):**
  materializa os 6 KPIs do `IRPFAnalyzer` (já em produção via E5 try-read)
  em duas seções novas do shell nativo: **S_IRPF_RENDA** (renda anual e
  impostos — cards de renda bruta/líquida, IR pago + alíquota dual, split
  trabalho×capital + chart de evolução multi-anos via Chart.js + dual gauge
  RFB/Cerbasi) e **S_IRPF_OTIMIZACAO** (capacidade PGBL não usada,
  dependentes declarados, dedutíveis subutilizados — placeholders para
  follow-up em copy editorial). Inseridas no `config/report_layout.yaml`
  entre S8 e S9, com codegen sincronizado para `frontend/src/generated/
  report-layout.ts` + `backend/app/generated/report_layout.py`. Tipo
  `IrpfKpis` em `frontend/src/types/irpf.ts` com narrow guard
  `isIrpfKpis` (TS strict — `unknown` → tipado), hook `useIrpfKpis`
  (memoiza leitura de `output.irpf_kpis` do snapshot E5). **Degrada
  gracioso**: workspaces sem declaração IRPF têm as duas seções inteiras
  omitidas (componentes retornam `null`, sem placeholder vazio). Tokens
  de cor (`var(--brand-*)`, `var(--semantic-*)`) — nenhum hex literal,
  alinhado com ADR-076. Side effect saudável: `MigratedSection` extraída
  de `ReportShell.tsx` (de 500→403 linhas) para um módulo próprio,
  destrancando o limite T2 do baseline. 16 testes Vitest novos (narrow
  guard + null-render das seções) — 712 testes frontend e 1536 backend
  todos passando. Acompanha fix de paridade `pipelineStageNames.ts`
  (E1.6 → `extract_irpf_full`). Lane pendente de G0/G4 sign-off em PR
  comment + visual baselines + Playwright `@critical` (follow-ups).
  [ADR-157](DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)
  · [ADR-076](DECISIONS.md#adr-076--design-tokens-unificados-site--relatório)
