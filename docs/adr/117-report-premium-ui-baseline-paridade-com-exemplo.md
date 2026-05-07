---
id: ADR-117
type: adr
title: "Report Premium UI baseline (paridade com EXEMPLO_DE_RELATORIO.html)"
status: Decidido
phase: "Fase 0 do plano"
date: "2026-04-23"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-151]]"]
aliases: ["ADR 117"]
tags:
  - type/adr
  - status/decidido
size_lines: 45
---

# ADR-117 — Report Premium UI baseline (paridade com EXEMPLO_DE_RELATORIO.html)

> **Nota (2026-04-29):** parcialmente superseded por
> [ADR-151](#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces)
> — o Modo Tático (T1-T6) foi removido do relatório (Direção E). O resto
> da ADR (paridade visual com EXEMPLO_DE_RELATORIO.html, Modos Estratégico
> + USA, capa hero, navegação sticky, dark mode) permanece em vigor.

**Status:** Decidido (Fase 0 do plano) • **Data:** 2026-04-23

**Contexto:** O relatório atual em `/reports/[id]` (React) e o exporter
standalone `scripts/e6_render.py` renderizam os mesmos dados do snapshot E5,
mas visualmente ficam muito atrás do template interno
`EXEMPLO_DE_RELATORIO.html` — que usa Chart.js, dark mode, cover hero,
card variants, section dividers, KPI hero, score gauge, period toggle,
kanban tático, e print CSS polido. Produto pede paridade visual com o
template para transmitir qualidade profissional. Discovery da Fase 0
produziu `docs/REPORT_PREMIUM_GAPS.md`.

**Decisão:** Executar o plano de 14 fases documentado em
`docs/REPORT_PREMIUM_PLAN.md` que eleva `/reports/[id]` e o export
standalone ao nível do template. Biblioteca de charts em
`components/report/**`: **Chart.js 4 + react-chartjs-2 + datalabels**
(mantém Recharts fora de `/reports/**`). Dark mode obrigatório. Cover
hero + top-nav sticky coexistem com `ReportToc` sidebar. Sub-ADRs
fecham gaps específicos: 121 (typography), 122 (chart_conclusions híbrido),
123 (notes/kanban persistidos), 124 (e6 retirement).

**Consequências:**
- ✅ Paridade visual com o template — produto ganha "peso" percebido.
- ✅ Design tokens unificados (Fase 1) fecham dívida do CSS em dois sistemas.
- ⚠️ Chart.js adiciona ~180KB ao bundle de `/reports/**` (aceito via
  route-split + dynamic SSR-off).
- ⚠️ Fase 6 (E5 data) é 30-40% menor que estimado inicialmente —
  services-alvo (`financial_score_calculator`, `pontos_fortes_analyzer`,
  `if_projector`, `ratios_calculator`) já existem; extensões apenas.
- ❌ Três bugs silenciosos descobertos (APP_B-E não renderizam,
  `design-tokens/build.py` não emite CSS standalone, schema YAML tático
  divergente) — registrados para tratamento em fases específicas, não
  bloqueiam o plano.

Relaciona-se a: ADR-037 (Recharts — escopo restringido), ADR-076 (design
system), ADR-102 (contratos), ADR-111 (stateless — revisto em ADR-123).
