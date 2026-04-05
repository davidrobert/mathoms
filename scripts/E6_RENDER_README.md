# E6 Renderer — Comprehensive Financial Report Generator

## Overview

`e6_render.py` is a **deterministic, pure-Python financial report generator** that reads E5 analysis JSON (containing data + narratives) and an HTML template, then produces a complete financial report via string replacement. **No LLM required.**

## Features

- **Deterministic**: Same input → same output, every time
- **Fast**: Pure string replacement, JSON serialization
- **Comprehensive**: 20 top-level data keys, 19 chart datasets, 10 sections, 5 appendices
- **Production-ready**: 18 validation checks, error handling, structured logging
- **Scalable**: Modular design for easy extension

## Input Files

| File | Purpose | Location |
|------|---------|----------|
| `E5_analysis.json` | Analysis output with data + narratives | `processed/E5_analysis/` |
| `report_template.html` | HTML structure + CSS + JS template | `config/` |
| `manual_operacao.md` | Manual for version extraction | `config/` |
| `definitions.md` | Categories and definitions (optional) | `config/` |

## Output

```
output/relatorio_financeiro_ferreira_campos_YYYYMMDD.html
```

Latest example: `relatorio_financeiro_ferreira_campos_20260404.html` (166KB)

## Architecture

### 1. Load Phase (E6.0)
- Load E5 JSON with patrimonio, fluxo_caixa, narrativas, etc.
- Load HTML template with placeholders
- Load manual_operacao.md for version extraction

### 2. Build Phase (E6.1–E6.5)

#### E6.1 — Cover, KPIs, Footer
Builds replacements for:
- Cover page: family name, period, version, timestamp
- KPIs: patrimônio, renda, poupança, IF meta/gap, score
- Footer: current São Paulo time, period, version

Key formatting utilities:
```python
fmt_brl(3501275)           # "R$ 3.501.275"
fmt_brl_m(7200000)        # "R$ 7,2M"
fmt_pct(65.7)             # "65,7%"
```

#### E6.2 — Perfil Familia
Direct passthrough from E5.narrativas.perfil_familia (left/right columns)

#### E6.3 — Report-Data JSON
Builds complete `report-data` object with 20 keys:
- `meta`: versioning, timestamp
- `kpis`: KPI values
- `patrimonio`: asset structure
- `charts`: 19 datasets for Chart.js
- `consumo_consciente`: spending patterns
- `investimentos`: portfolio data
- `score`: rating + components
- ... + 13 more

**19 Charts included:**
1. patrimonio_doughnut
2. waterfall_if
3. receita_bar
4. fluxo_mensal
5. receita_despesa_mensal
6. despesas_doughnut
7. score_gauge
8. alocacao_atual
9. alocacao_alvo
10. top15_ativos
11. yield_imoveis
12. custos_f1f2
13. cenario_cambial
14. projecao_if
15. renda_passiva
16. impostos_pj
17. riscos_bubble
18. decisoes
19. alertas_criticos

#### E6.4 — Sections S1–S10
Builds HTML for 10 major report sections:
1. Patrimônio — Estrutura e Composição
2. Fluxo de Caixa — Receitas e Despesas
3. Investimentos — Carteira Financeira
4. Real Estate — Imóveis e Renda Passiva
5. Mudança EUA — Estrutura F1/F2
6. Green Card — EB2-NIW e Compliance
7. Independência Financeira — Meta 2035
8. Previdência — PGBL e Fiscalidade
9. Riscos e Proteção — Seguros Críticos
10. Síntese Estratégica — Tarefas e Score

Each section includes:
- Chart containers with narrative context/conclusion
- Summary cards with data
- Proper semantic HTML (h2, p, canvas)

#### E6.5 — String Replacement
Applies all ~100 replacements to template:
- `{{COVER_FAMILIA}}` → "Ferreira Campos"
- `{{KPI_PATRIMONIO_BRUTO}}` → "R$ 3.501.275"
- `{{REPORT_DATA_JSON}}` → full JSON object
- `{{CONTENT_S1}}` through `{{CONTENT_S10}}` → section HTML
- ... and more

### 3. Validation Phase (E6.6)

**18 validation checks:**

| # | Check | Status |
|---|-------|--------|
| V1 | No remaining {{...}} outside HTML comments | ✓ |
| V2 | report-data JSON is valid | ✓ |
| V3 | charts has 19 datasets | ✓ |
| V4 | 19 canvas IDs present | ✓ |
| V5 | 9+ sections present | ✓ |
| V6 | 5 appendices present | ✓ |
| V7 | Mandatory cards present | ✓ |
| V8 | COVER_DATA_HORA contains time pattern | ✓ |
| V9 | COVER_VERSAO is version number | ✓ |
| V10 | Perfil is narrative prose | ✓ |
| V11 | KPIs match E4 | ✓ |
| V12 | patrimonio.imoveis_estimado > 0 | ✓ |
| V13 | orcamento_prospectivo has 14+ categories | ✓ |
| V14 | HTML > 100KB | ✓ |
| V15 | No inline margin-top/bottom | ✓ |
| V16 | .card has .card-title first child | ✓ |
| V17 | No hardcoded hex colors in HTML | ✓ |
| V18 | tr.total-row for total rows | ✓ |

## Usage

```bash
cd /mnt/Financas\ Familia/financas-familia/scripts
python3 e6_render.py
```

Output:
```
======================================================================
E6 RENDERER — Deterministic Financial Report Generation
======================================================================

[E6.0] Loading E5 JSON...
[E6.1-E6.5] Building all replacements...
[E6.3.charts] Building 19 chart datasets...
[E6.5] Applying replacements to template...
[E6.6] Running validation checks...

[E6.6] Validation Results:
  V1: No remaining {{...}} [PASS]
  V2: report-data JSON is valid [PASS]
  ...
  V18: CSS rule: tr.total-row [PASS]

[E6.7] Writing output to .../relatorio_financeiro_ferreira_campos_20260404.html...
[E6.8] Report size: 166.0KB

✓ Report generated successfully!
```

## Report Content

### Cover Page
- Family name: "Ferreira Campos"
- Data period: "2025-05 a 2026-03"
- Manual version: "3.3"
- Generation timestamp: "4 abr 2026, 14h32" (São Paulo time)

### Key Performance Indicators (KPIs)
- **Patrimônio Bruto**: R$ 3.501.275
- **Patrimônio Investível**: R$ 2.530.778 (72.3% of bruto)
- **Renda Mensal Recorrente**: R$ 79.112
- **Taxa de Poupança**: 65,7%
- **IF Meta**: R$ 7,2M
- **IF Gap**: R$ 4,7M
- **IF Prazo**: 9,2 anos (realista) → David com 54 em 2035
- **Score**: 8.4 / 10 (Excelente)

### Perfil Familia
- David Camargo Ferreira Ferreira Campos, 45, CTO Arvo
- Mariana Teixeira Ferreira Campos, 40, Enfermeira Einstein
- Theo Ferreira Campos, 9 meses (dupla cidadania US/BR)
- 3 gatos, 5 imóveis, 10+ contas bancárias

### Charts (19 datasets)
All rendered dynamically via Chart.js with:
- Narrative context (why this chart matters)
- Data visualization
- Conclusion (what it means)

### Sections (10 major + 5 appendices)
- Strategic narrative structure
- Data-driven insights
- Actionable recommendations
- Compliance & risk highlights

### Report-Data JSON
Complete data object embedded in `<script id="report-data">` for:
- Chart.js initialization
- Interactive mode switching (Estratégico ↔ Tático)
- Export and reporting features
- Future API integration

## Key Metrics from E5

| Metric | Value | Target |
|--------|-------|--------|
| Patrimônio Bruto | R$ 3.501.275 | — |
| Patrimônio Investível | R$ 2.530.778 | — |
| Receita Recorrente Mensal | R$ 79.112 | — |
| Despesa Média Mensal | R$ 19.708 | — |
| Superávit Mensal | R$ 59.404 | — |
| Taxa Poupança | 65,7% | 20%+ |
| Taxa Endividamento | 6,7% | <10% |
| Cobertura Despesas | 128,4 meses | 12+ |
| Renda Passiva Atual | R$ 10.042/mês | R$ 30.000/mês |
| IF Progress | 35,1% | 100% by 2035 |
| Score | 8.4/10 | — |

## CSS Rules Enforced

- ✓ No inline `margin-top` or `margin-bottom` on cards/charts
- ✓ Every `.card` has `.card-title` as first child
- ✓ No hardcoded hex colors (use CSS variables)
- ✓ `.kpi-card-accent` for accent cards
- ✓ `.card-primary` for primary cards
- ✓ `tr.total-row` for table totals
- ✓ No empty `<p>` tags
- ✓ No `<h2>` inside CONTENT (template has h1)
- ✓ `<h3>` for subsections

## File Structure

```
financas-familia/
├── scripts/
│   ├── e6_render.py              ← Main script
│   ├── E6_RENDER_README.md       ← This file
│   └── ...
├── config/
│   ├── report_template.html      ← HTML structure
│   ├── manual_operacao.md        ← Version source
│   ├── definitions.md
│   └── ...
├── processed/
│   └── E5_analysis/
│       └── analise_financeira-5_analysis.json  ← Data source
├── output/
│   └── relatorio_financeiro_ferreira_campos_20260404.html  ← Generated
└── ...
```

## Performance

| Metric | Value |
|--------|-------|
| Execution Time | < 5 seconds |
| Output Size | 166 KB |
| JSON Size (embedded) | ~40 KB |
| Chart Datasets | 19 |
| Canvas Elements | 20 |
| Placeholders Replaced | ~100 |
| Validation Checks | 18 |

## Error Handling

```python
if __name__ == "__main__":
    try:
        output = render_report()
        print(f"\nSUCCESS: {output}")
    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()
        exit(1)
```

## Future Enhancements

1. **Template Versioning**: Support multiple template formats
2. **Multi-Family Reports**: Batch generation for different families
3. **Incremental Updates**: Only re-generate changed sections
4. **Export Formats**: PDF, XLSX, JSON-only modes
5. **Interactive Dashboard**: Web UI with filters and drill-downs
6. **Scheduling**: Cron integration for automatic monthly reports

## Dependencies

- Python 3.8+
- `json` (stdlib)
- `re` (stdlib)
- `pathlib` (stdlib)
- `datetime` (stdlib)
- `pytz` (for São Paulo timezone)

## Author Notes

This script follows deterministic rendering principles:
- No randomization
- No external API calls
- No LLM generation
- Pure function composition
- Testable and reproducible

Last Updated: **2026-04-04**
Rendered By: **Claude Opus 4.6**
Version: **E6.0 — Deterministic Renderer**
