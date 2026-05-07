---
id: ADR-078
type: adr
title: "Render Nativo React + E6 como Exportador Standalone"
status: Decidido
phase: "F9"
date: "2026-04-15"
relates_to: []
supersedes: ["[[ADR-033]]"]
superseded_by: ["[[ADR-129]]"]
aliases: ["ADR 078"]
tags:
  - area/frontend
  - area/pipeline
  - area/testing
  - status/decidido
  - type/adr
size_lines: 72
---

# ADR-078 — Render Nativo React + E6 como Exportador Standalone

**Status:** Decidido (F9) • **Data:** 2026-04-15

> **Nota (2026-04-24):** parte operacional desta ADR (`e6_render.py` como
> exportador HTML standalone, endpoints `/html` e `/download.html`) foi
> **superseded por [ADR-129](#adr-129--descontinuação-completa-do-renderer-html-server-side)**.
> O renderer React nativo (`/reports/[id]`) é o único caminho vivo;
> exportador HTML morreu. PDF via Playwright sobre a mesma rota cobre
> os 3 casos de uso originalmente atribuídos ao standalone.

**Contexto:**
O relatório financeiro era exibido via iframe carregando o HTML produzido pelo `e6_render.py` (4000 linhas, string replacement, Chart.js Canvas). Isso causava:
- Dissonância visual com o site (duas linguagens de design, cf. ADR-076)
- Limitações de UX: sem deep-links, search, dark mode sincronizado, a11y parcial
- Dependência de `doc.write()` + MutationObserver para scroll-spy e mode toggle
- Charts Canvas não imprimiam bem (fallback PNG manual no template)

**Alternativas:**
- **A** — Manter iframe, injetar CSS via postMessage. Resolve dissonância mas não UX.
- **B** — ✅ **Escolhida**: eliminar iframe, renderizar como rota Next.js nativa consumindo E5 JSON. E6 vira exportador HTML standalone (produto preservado).
- **C** — Reescrever E6 em React Server Components. Over-engineering; E6 faz um bom trabalho como gerador estático.

**Decisão:**

1. **Render primário**: rota Next.js `/reports/[id]` consome `GET /reports/{id}/data` (E5 JSON snapshot) e renderiza via componentes React com design tokens do ADR-076.
2. **Estrutura**: `report_layout.yaml` é fonte de verdade (codegen TS/Pydantic, F0.2.5). 18 seções em 3 modos (Estratégico S1-S10, Tático T1-T6, USA U1-U4).
3. **Charts**: Recharts (SVG) substituiu Chart.js (Canvas). SVG imprime nativamente — elimina fallback PNG.
4. **PDF server-side**: Playwright headless Chromium renderiza a rota React. Token efêmero (60s) para autenticação.
5. **E6 preservado**: `e6_render.py --html` continua gerando HTML standalone para 3 use cases: contador (email), backup (offline), impressão (sem app).
6. **Migration**: iframe removido; relatórios pré-F9 (sem `analysis_json_path`) redirecionam para download HTML.

**Componentes criados** (frontend/src/components/report/):
- Shell: ReportShell, ReportHeader, ReportToc, ReportModeProvider
- Cards: 13 componentes (Patrimonio, Fluxo, Investimentos, Previdencia, Pontos, etc.)
- Charts: 8 componentes Recharts + NarrativeChartCard genérico
- Infra: MonetaryValue (font-mono tabular-nums), card registry, chart registry

**Consequências:**
- ✅ Uma linguagem visual, uma codebase — fim da dissonância site × relatório
- ✅ Deep-links (`/reports/id?mode=usa#U2`), scroll-spy nativo, dark mode sincronizado
- ✅ SVG charts imprimem perfeitamente (zero workaround)
- ✅ Tipagem end-to-end: YAML → TS → componentes → runtime validated
- ✅ PDF server-side resolve o "salvar como PDF" que antes dependia de Cmd+P do browser
- ✅ E6 standalone preservado — valor real para contador e backup
- ⚠️ Playwright adiciona ~200MB ao container Docker (Chromium) — aceito para v1
- ⚠️ `e6_render.py` (4000 linhas) fica como código legado — aceito; mantém valor como exportador
- ❌ Sem export XLSX de tabelas (existia via iframe `table_to_sheet`). Recuperar como feature futura

**Supersedes parcial:**
- [ADR-033 "React components para report"](#adr-033--react-components-para-report) — era placeholder; esta ADR implementa a decisão com arquitetura completa.
- [ADR-035 "Media print para PDF export"](#adr-035--media-print-para-pdf-export) — media print continua como fallback mas Playwright é o caminho primário.

---

## Decisões pendentes

| #   | Decisão                           | Quando precisa | Opções                                                               |
| --- | --------------------------------- | -------------- | -------------------------------------------------------------------- |
| D8  | Pricing do premium                | Pós-beta       | R$29/mês / R$49/mês / R$99/mês                                       |
| D9  | Nome do produto                   | Pré-GA         | Mathoms AI (escolhido) / FinPlan / outros                                                |
| D10 | Prioridade de novos bancos        | Pós-beta       | Nubank / Inter / Mercado Pago / Open Finance                         |
| D11 | Email transactional provider      | Pré-7B.11      | Resend / Mailgun / AWS SES / SendGrid                                |
| D12 | Multi-language support            | F8+            | pt-BR only / pt-BR + en                                              |
| D13 | MFA: F7 ou F8                     | Pré-7B.14      | F7 (TOTP via authenticator app) / F8 (após beta validado)            |
| D14 | Menores como `FamilyMember`       | Pré-beta       | Permitir (LGPD/ECA exigem cuidados) / Bloquear (apenas adultos)      |
| D15 | Cost cap mensal default           | Pré-7E.11      | 500K tokens / 1M / 2M / configurável sem default                     |
| D16 | Off-site backup destination       | Pré-7E.4       | S3 BR (custo) / Backblaze B2 (US, mais barato) / R2 Cloudflare       |
| D17 | Status page provider              | Pré-7E.6       | uptime-kuma self-hosted / instatus.com free / better-stack           |
| D18 | RPO/RTO target                    | Pré-7E.3       | Dogfood: RPO=24h RTO=4h • Beta: RPO=1h RTO=1h • GA: RPO=15min RTO=30min |
