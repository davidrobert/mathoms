# Design Tokens — Mathoms Editorial

Fonte única de tokens de design do produto Mathoms AI. Ver **ADR-076**, **ADR-117** (report premium) e **ADR-121** (typography configurável) em [../docs/DECISIONS.md](../docs/DECISIONS.md).

## Estrutura

```
design-tokens/
├── tokens.json              ← FONTE DE VERDADE (editar aqui)
├── build.py                 ← gera CSS
└── README.md
```

Saídas geradas (não editar à mão):

```
frontend/src/styles/tokens.css       ← site (Next.js + Tailwind v4 @theme inline)
frontend-ops/src/styles/tokens.css   ← console ops (Next sem @theme inline)
```

Renderer HTML standalone foi descontinuado em ADR-129 — o relatório vive
exclusivamente em `/reports/[id]` (React) e o export PDF passa por
Playwright sobre essa rota.

## Uso

Gerar:
```bash
python3 design-tokens/build.py
```

Verificar sync (usado no pre-commit e CI):
```bash
python3 design-tokens/build.py --check
```

## Categorias de tokens

- **typography** — fontes (display/body/mono), tamanhos, pesos, line-heights
- **spacing** — escala 4px
- **radius** — cantos
- **shadow** — elevação (light + dark)
- **modes.light / modes.dark** — paletas por modo:
  - `brand` (primary, accent, danger, warning, neutral, info)
  - `surface` (background, card, border, muted…)
  - `semantic` (gain, loss, alert — domínio financeiro)
  - `chart` (12 cores categóricas)
  - `sidebar`
- **card_variants** — variantes do relatório (highlight, feature, success, warn, critical, primary, neutral, top-danger, top-accent)
- **report_palette** (ADR-117) — paleta exclusiva do relatório premium (`/reports/**`), emitida sob `[data-report-scope]` para não vazar no resto do app. Light + dark. Grupos: `surface_ext` (accent-bg, row-total, summary-bg…), `alert` (danger/warning/success/info × bg+text), `badge` (green/red/yellow/blue/neutral × bg+text), `table` (even/hover/total/header), `gradient` (cover-primary, cover-subtitle, nav-sticky, card-feature/success). Vars geradas: `--report-surface-*`, `--report-alert-*`, `--report-badge-*`, `--report-table-*`, `--report-gradient-*`.
- **report_typography** (ADR-121) — escala tipográfica configurável escopada em `[data-report-scope][data-font-scale=…]`. 3 presets: `compact` (base 13px — default), `normal` (15px), `comfortable` (17px). Vars geradas: `--report-font-size-{xs,sm,base,md,lg,xl,2xl,3xl}` + `--report-font-base-px`. Também emite `--report-space-*` (section-gap, card-sm/md/lg) e `--report-radius-badge`.

### Escopo do relatório (`[data-report-scope]`)

O shell do relatório envolve o conteúdo em `<div data-report-scope data-font-scale="compact">`. Dentro desse escopo:

- A paleta premium (`--report-*`) está disponível.
- Os tokens globais (`--brand-*`, `--surface-*`) **continuam** disponíveis — o escopo é aditivo, não substitutivo.
- Dark mode funciona automaticamente via `.dark [data-report-scope]` ou `[data-theme='dark'] [data-report-scope]`.
- Trocar `data-font-scale` no wrapper muda a escala de fontes do relatório inteiro sem afetar o resto do app.

Hooks de runtime:
- `useReportFontScale()` em `frontend/src/components/report/` — lê/grava `localStorage['mathoms:report:font-scale']`.
- `<ReportThemeToggle />` em `frontend/src/components/report/` — wrappa `next-themes` com UI segmentada light/dark.

## Regras de uso

1. Nenhum literal hex ou cor OKLch fora de `tokens.json`.
2. Nenhum `font-family:` fora de `tokens.css`.
3. Valores monetários SEMPRE com `font-mono` + `tabular-nums` — use o componente `<MonetaryValue/>`.
4. Variantes de card são consumidas via classe `.card-variant-<nome>` — não reestilize à mão.

## Fluxo de mudança

1. Edita `tokens.json`.
2. Roda `python3 design-tokens/build.py`.
3. Commita os arquivos (tokens.json + 2 CSS gerados).
4. Pre-commit valida sync via `--check`.
