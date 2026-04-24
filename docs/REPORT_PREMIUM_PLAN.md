# Plano — Elevar `/reports/[id]` ao nível do `EXEMPLO_DE_RELATORIO.html`

> ⚠️ **Status do plano (2026-04-24):** Fases 0-10 ✅ entregues em `main`.
> **Fases 11 / 12 / 13 canceladas** via
> [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).
> O renderer HTML server-side (`scripts/e6_render.py`) foi descontinuado
> por completo — não há mais alvo de paridade HTML. React
> (`/reports/[id]`) é o único renderer; PDF via Playwright é o único
> export server-side. Todo conteúdo deste plano referente à Fase 11
> (§10), Fase 12 (§11) e Fase 13 (§12) está mantido abaixo apenas como
> **registro histórico** — não executar.
>
> **Audiência:** LLM executor (agente Claude em worktree próprio).
> **Referência visual:** `EXEMPLO_DE_RELATORIO.html` (raiz do repo, 10 024 linhas).
> **Referência atual (viva):** `frontend/src/components/report/**`,
> `design-tokens/tokens.json`, `config/report_layout.yaml`.
> **Referência histórica (removida na execução da ADR-129):**
> `scripts/e6_render.py`, `scripts/e6/`.
> **Data de emissão:** 2026-04-23.
> **Última revisão de status:** 2026-04-24.
> **Status geral:** 10 de 10 fases úteis entregues em `main` — Fases 0-10.
> Detalhes de cada fase na [tabela do §2](#2-roadmap-de-fases-visão-geral) e
> em [BACKLOG.md — Report Premium UI](BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml).

---

## ⚠️ Deltas aplicados após Fase 0 (leitura obrigatória)

Resultado da discovery + decisões humanas nas 13 open questions. Sempre que
este plano conflitar com os deltas abaixo, **os deltas prevalecem**.

1. **Fase 6 menor que estimado.** `financial_score_calculator`, `pontos_fortes_analyzer`,
   `if_projector`, `ratios_calculator` já existem em `pipeline/domain/services/`.
   Trabalho é **extensão**, não criação. Único service genuinamente novo:
   `SnapshotChangelogBuilder` — **diferido para v2** (ver #4).
2. ~~**Fase 11 reescrita — aposentar `e6_render.py`** (ADR-124). Em vez
   de Jinja2, a rota Next SSR `/reports/[id]/export` gera o HTML
   standalone. Backend endpoint passa a proxyar. `scripts/e6_render.py`
   é deletado ao final da fase. Os 19 V-checks migram para Playwright
   contra a rota.~~ **[Obsoleto — superseded por
   [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).**
   Nenhuma rota SSR será construída; o endpoint HTML inteiro é removido.
   Os 19 V-checks desaparecem junto com o validador.
3. **Nova Fase 6.5 — backend persistence para Notas + Kanban** (ADR-123).
   Duas tabelas novas (`report_notes`, `kanban_items`), migração Alembic,
   4 endpoints REST com `response_model`, OpenAPI snapshot. Entra entre
   Fase 6 (dados E5) e Fase 7 (seções). Esforço: ~1 sprint.
4. **`comparisons` e `changelog` diferidos para v2** (decisão usuário Q6).
   Entram como `enabled: false` no YAML durante Fase 5. Ativação pós-Fase 13
   quando `SnapshotChangelogBuilder` for construído.
5. **Typography configurável — 13px default** (ADR-121). `--font-base-px`
   escopado no shell de `/reports/**`. Toggle "Compacto/Normal/Confortável"
   na top-nav. Escala recalculada em px (não rem) dentro do relatório.
6. **Chart conclusions ≠ section summaries** (ADR-122). Conclusions são
   **templates determinísticos** em `config/prompts/chart_conclusions.yaml`
   (Fase 6 `E5-det`, esforço S). Summaries são **LLM** com cache Redis
   (Fase 6 `E5-new`, primeiro uso de Anthropic em E5 — prepare Fase 6 para
   lidar com Anthropic key, cache, fakes nos testes).
7. **`pontos_fortes` fica como está** (Q11 — sem LLM por ora). Analyzer
   atual gera textos equivalentes ao exemplo. Revisar pós-Fase 12.
8. **Breakpoints do shell** (Q7): ≥1024 sidebar+topnav; 768–1023 sidebar
   vira drawer; ≤767 só topnav. `<ReportToc>` vira `<ReportTocDrawer>` em
   tela média.
9. **Branch strategy por fase** (Q8): fases curtas (1, 2, 3, 4, 5) em
   `.claude/worktrees/<slug>/`; fases longas (6, 6.5, 7–11) em worktree
   externo `../fin-report-premium-<phase>/` para isolamento de resets.
10. **JetBrains Mono no standalone** (Q9): sim, Fase 1 adiciona na lista de
    fontes — agora que o standalone sai por SSR, a font viaja junto.
11. **Três bugs silenciosos** descobertos (ver GAPS.md §5 Observations):
    `APP_B-E` não renderiza (`ReportShell.MIGRATED_SECTIONS` hardcoded),
    `design-tokens/build.py` não emite CSS standalone,
    YAML tático com schema divergente. **Fase 1 resolve o #2**; **Fase 5
    resolve o #3**; **Fase 10 resolve o #1**.
12. **ADR numbering real:** 117 / 121 / 122 / 123 / 124 (não 117–120 como
    o plano original sugeriu — 118/119/120 já estão em uso).

---

## 0. Premissas e contratos

### 0.1 Decisões de escopo (já aprovadas pelo usuário)

| # | Decisão | Valor |
|---|---------|-------|
| 1 | Alvos de render | **React (rota `/reports/[id]`) + `e6_render.py` em paridade** |
| 2 | Biblioteca de charts | **Chart.js 4 + react-chartjs-2 + chartjs-plugin-datalabels** — apenas dentro de `frontend/src/components/report/**`. Recharts permanece no dashboard interno. |
| 3 | Navegação / modos | **Manter `ReportToc` sidebar**; **adicionar** top-nav sticky igual ao exemplo (com numeração + grupos + toggle de modo + toggle de tema). Os dois coexistem. |
| 4 | Elementos visuais | **Todos** os do exemplo (cover hero, dark mode, chart-conclusion, section-divider, card variants, KPI-hero, score gauge, period toggle, back-to-top, export-toolbar, skip-nav, print CSS, kanban em T3). |
| 5 | Dados | **Visual + data.** Onde o pipeline (E5) não produz o campo necessário, estender E5 e propagar no `ReportAnalysisData`. |

### 0.2 Invariantes inegociáveis (CLAUDE.md)

O executor **não** pode violar:

- `Money`/`Decimal` em dinheiro — nunca `float` (ADR-090).
- `pipeline/**` não importa `fastapi`/`celery`/`sqlalchemy` (dev/check_pipeline_boundaries.py).
- Sem `--force`, `--no-verify`, `--amend` em commit pushado, `reset --hard` em branch compartilhada.
- Stateless rigoroso (ADR-111): nada de estado mutável in-memory em `backend/` / `pipeline/`. Notas do T6 vão para **localStorage** (client-only) ou Redis via endpoint, **nunca** módulo global.
- Endpoint JSON novo → `response_model` + `make update-openapi-snapshot` (ADR-109).
- Sem `any` em TypeScript; sem `Dict[str, Any]` fora de boundaries em Python.
- Pre-commit + `pytest` locais verdes **antes** de cada push.
- Commits pequenos e coesos — 1 mudança lógica por commit, diff ≤ 300 linhas idealmente.
- Branch `agent/<slug>/<yyyyMMdd-HHmm>`, criada **antes** da primeira edição.

### 0.3 Protocolo de execução

1. **Primeira ação em cada nova sessão:** `git status && git log --oneline HEAD -3`. Se vier suja e você não reconhece — pare e peça instrução.
2. **Branch:** `agent/report-premium/<yyyyMMdd-HHmm>`. Uma branch por fase (ver §2) para manter PRs ≤ 800 linhas.
3. **Commits WIP são obrigatórios** entre turnos. Nada de working tree sujo ao devolver a palavra.
4. **Anunciar cada operação git** (commit hash + mensagem curta, push + destino).
5. **Pausas para revisão humana** estão marcadas como 🛑 neste plano. Não prossiga sem resposta.
6. **Em caso de dúvida de domínio** — consulte `config/definitions.md`, `config/pipeline.json`, `docs/DECISIONS.md`. Não invente regra.

### 0.4 "Concluído" significa

Para cada fase: **commit em `main` com CI verde** (§CLAUDE.md). Até lá, a fase está `in_progress` no seu tracking interno. "Passou local" não conta.

---

## 1. Fase 0 — Discovery & Gap Inventory (obrigatória antes de código)

**Branch:** `agent/report-premium/phase0-discovery/<ts>`
**Entregável:** `_scratch/REPORT_PREMIUM_GAPS.md` (commitado como `chore(docs): gaps inventory (phase 0)` em `_scratch/` que está no `.gitignore` — então **não** commita; entrega via tool-output e salva local).

### 1.1 Leitura obrigatória integral

- [ ] `EXEMPLO_DE_RELATORIO.html` inteiro (10 024 linhas) — leia em 3 blocos (`1-3500`, `3501-7000`, `7001-fim`). Anote por seção: cards presentes, charts presentes, dados injetados (`{{PLACEHOLDER}}` ou valor literal).
- [ ] `frontend/src/types/report-analysis.ts` — shape atual do `ReportAnalysisData`.
- [ ] `frontend/src/components/report/sections/*.tsx` — o que cada seção já consome e renderiza.
- [ ] `config/report_layout.yaml` — inventário de cards/charts por seção (fonte de verdade do layout).
- [ ] `design-tokens/tokens.json` + `design-tokens/build.py` — como tokens viram CSS.
- [ ] `scripts/e6_render.py` + `scripts/e6/sanitize.py` + `scripts/e6/validate.py` — pipeline do export standalone.
- [ ] `pipeline/domain/services/` (e5-relacionados) — onde E5 gera o payload de análise.

### 1.2 Produto do discovery

Um documento `_scratch/REPORT_PREMIUM_GAPS.md` com 4 tabelas:

**Tabela A — Gaps de token.** Para cada variável CSS do `:root` do exemplo (linhas 31–147), marcar: `existe / ausente / renomear-para`. Saída esperada: lista de ~60 tokens a acrescentar em `tokens.json`.

**Tabela B — Gaps de primitivo UI.** Componentes React que precisam existir e ainda não existem: `ReportCover`, `ReportTopNav`, `ModeToggle`, `ThemeToggle`, `CardVariant` (wrapper), `SectionDivider`, `IconBadge`, `KpiHero`, `KpiStrip`, `ScoreCard`, `ScoreBreakdownTable`, `ChartConclusion`, `PeriodToggle` (já existe — audita), `ChartNav`, `AlertBox`, `Badge`, `PontoForteItem`, `Kanban`, `KanbanColumn`, `KanbanCard`, `Timeline`, `ChangelogList`, `NotasCard`, `BackToTop`, `GoToBottom`, `ExportToolbar`, `SkipNav`, `CollapsibleSectionHeader`.

**Tabela C — Gaps de dado no `ReportAnalysisData`.** Para cada campo que o exemplo exibe, mapear para fonte. Suspeitos iniciais (confirmar na discovery):
- `score.overall`, `score.classe` ∈ {`Excelente`,`Bom`,`Regular`,`Ruim`,`Péssimo`,`Crítico`}, `score.breakdown[]` com `{dimensao, valor, peso, contrib}`, `score.formula`.
- `meta_if.pct_atual`, `meta_if.pct_meta`, `meta_if.ano_alvo`, `meta_if.gap_mensal`.
- `projecao.kpi_strip[]` (5 KPIs do `.proj-kpi-strip`).
- `chart_conclusions[chart_id]` — texto curto (≤180 char) por gráfico.
- `section_summaries[section_id]` — mini-resumo de 1-2 frases.
- `pontos_fortes[]` — lista de `{icon, titulo, descricao}`.
- `cerbasi.presente_vs_futuro` — 4 barras percentuais.
- `tatico.kanban.itens[]` — `{id, titulo, prioridade ∈ {alta,media,baixa}, prazo_iso, coluna ∈ {a_fazer,em_andamento,concluido}}`.
- `tatico.timeline[]`, `tatico.alertas[]`, `tatico.changelog[]`.
- `capa.meta[]` — 4 cards (ex.: "Período analisado", "Gerado em", "Versão", "Metodologia").
- `comparisons[]` — pares antes/depois por card quando aplicável.
- `priority_badges` em tabelas estratégicas — `{alta,media,baixa}`.

Para cada gap: `origem proposta` (E5 novo campo | LLM call | regra determinística | input manual do usuário) + `esforço` (S/R/O) + `bloqueia quais seções`.

**Tabela D — Gaps no `report_layout.yaml`.** Cards/charts presentes no exemplo mas ausentes do YAML. O YAML é fonte de verdade — todos os novos itens visuais entram lá antes de virar código (pipeline `dev/codegen_report_layout.py` regenera os tipos).

### 1.3 🛑 PAUSA para revisão humana

Ao final da Fase 0, entregar o `REPORT_PREMIUM_GAPS.md` e **aguardar** aprovação. Não começar Fase 1 sem:

- Lista de gaps de dado aprovada (usuário pode cortar: "o score fica para depois, entrega sem").
- Decisão sobre onde os `chart_conclusions` e `section_summaries` são gerados: (i) LLM na E5, (ii) prompt template em `config/`, (iii) input manual do consultor.
- Decisão sobre `NotasCard` T6: localStorage (client) vs endpoint persistido (Redis/DB).

Saída esperada dessa pausa: decisões registradas em `docs/DECISIONS.md` como nova ADR (próximo número disponível — hoje seria ADR-117 ou superior; confira antes).

---

## 2. Roadmap de fases (visão geral)

Cada fase = branch própria + PR próprio + merge antes de iniciar a próxima. Fases 3–7 podem paralelizar entre agentes diferentes se houver capacidade (ver §11).

| Fase | Nome | Branch suffix | Saída | Depende de | Status |
|------|------|---------------|-------|------------|--------|
| 0 | Discovery & gaps | `phase0-discovery` | `REPORT_PREMIUM_GAPS.md` + ADR | — | ✅ 2026-04-24 |
| 1 | Design tokens + dark mode | `phase1-tokens` | `tokens.json` expandido, CSS regenerado | 0 | ✅ 2026-04-24 |
| 2 | Chart.js foundation | `phase2-charts` | Componentes `ChartBar/Donut/Area/Gauge/Combo/Stacked` + `PeriodToggle` + `ChartConclusion` | 1 | ✅ 2026-04-24 |
| 3 | UI primitives | `phase3-primitives` | Card variants, Alert, Badge, SectionDivider, IconBadge, KpiHero, ScoreCard, PontoForteItem | 1 | ✅ 2026-04-24 |
| 4 | Shell: cover + topnav + toolbar | `phase4-shell` | `ReportCover`, `ReportTopNav`, `ModeToggle`, `ThemeToggle`, `BackToTop`, `ExportToolbar`, `SkipNav` | 3 | ✅ 2026-04-24 |
| 5 | Layout YAML expansion | `phase5-layout` | `report_layout.yaml` atualizado + codegen TS/py | 0 | ✅ 2026-04-24 |
| 6 | Derivadores determinísticos (chart_conclusions + section_summaries + adapters) ¹ | `phase6-e5-data` | `deriveChartConclusion`, `deriveSectionSummary`, adapters Kanban/Timeline | 0, 5 | ✅ 2026-04-24 |
| 6.5 | Backend persistence — Notas + Kanban (ADR-123) | `phase6_5-persistence` | 2 tabelas Alembic + 6 endpoints REST + OpenAPI snapshot | 0 | ✅ 2026-04-24 |
| 7 | Sections estratégicas | `phase7-sections-strategic` | S1–S4, S7–S10 repaginadas | 2, 3, 4, 6 | ✅ 2026-04-24 |
| 8 | Sections táticas + Kanban + Notas | `phase8-sections-tactical` | T3/T5/T6 consumindo endpoints 6.5 + HTTP client | 2, 3, 4, 6, 6.5 | ✅ 2026-04-24 |
| 9 | Sections USA | `phase9-sections-usa` | U1–U4 | 2, 3, 4, 6 | ✅ 2026-04-24 |
| 10 | Apêndices A–E (+ fix `MIGRATED_SECTIONS`) | `phase10-appendices` | APP_A refatorado + B/C/D/E novos + router unificado | 5 | ✅ 2026-04-24 |
| 11 | `e6_render.py` paridade (Jinja2 + tokens — ADR-124) | `phase11-e6-parity` | Reescrever exportador standalone com templates Jinja2 + CSS tokens; 19 V-checks verdes | 7, 8, 9, 10 | ☐ **próxima** |
| 12 | Print + a11y + tests | `phase12-polish` | Print CSS, Playwright screenshots, axe-core | 11 | ☐ |
| 13 | Rollout & docs | `phase13-rollout` | CHANGELOG, RUNBOOK, delete `scripts/e6_render.py` | 12 | ☐ |

¹ **Fase 6 redimensionada conforme Delta #1** — `financial_score_calculator`,
`pontos_fortes_analyzer`, `if_projector`, `ratios_calculator` já existiam em
`pipeline/domain/services/`. Entrega virou derivadores frontend-side
determinísticos + templates YAML, sem primeiro uso de Anthropic em E5
(LLM para `section_summaries` adiado — revisar pós-Fase 12).

Estimativa total (um agente, serial): **10–14 sprints equivalentes**. Paralelizando Fases 3/5/6 e depois 7/8/9, o caminho crítico cai para ~7–9 sprints.

---

## 3. Fase 1 — Design tokens + dark mode

**Branch:** `agent/report-premium/phase1-tokens/<ts>`

### 3.1 Entregas

1. Estender `design-tokens/tokens.json` com **todos** os tokens do `:root` do exemplo (linhas 31–147):
   - Paleta completa (`--color-primary` até `--color-compare-pos`).
   - Tokens semânticos de alert (4 pares `bg`/`text`) em light e dark.
   - Escala completa de fontes (`--font-xs` a `--font-3xl`) — 8 níveis.
   - Escala de spacing (`--space-xs` a `--space-4xl`) — 8 níveis + aliases legados.
   - Escala de radius (`--radius-sm`, `md`, `lg`, `card`, `badge`, `pill`).
   - Shadows (`card`, `card-hover`) — light e dark.
   - Badge tokens (5 semânticas × 2 modos).
   - Dark-mode overrides completos (linhas 108–147 do exemplo + gradientes `--card-feature-bg`, `--card-success-bg`, `--roadmap-bg`).
2. `design-tokens/build.py` precisa produzir **dois artefatos**: o CSS que o Next.js já consome + o CSS que o `e6_render.py` injeta no HTML standalone. Se hoje só produz um, estender.
3. Confirmar que fontes (`Plus Jakarta Sans`, `Inter`, `JetBrains Mono`) estão carregadas via `next/font/google` em `frontend/src/app/layout.tsx` conforme ADR-076. Nunca redefinir em CSS.
4. Acrescentar theme toggle com `data-theme="light|dark"` em `<html>` + `localStorage` persistente. Componente fica em `frontend/src/components/report/ReportThemeToggle.tsx` (usado pela top-nav da Fase 4 — criar stub agora, integrar depois).

### 3.2 Arquivos tocados

- `design-tokens/tokens.json` (+ ~60 tokens)
- `design-tokens/build.py` (+ export modo standalone se não existe)
- `design-tokens/README.md` (documentar escalas)
- `frontend/src/app/globals.css` (ou equivalente) — garantir que `data-theme="dark"` troca vars
- `frontend/src/components/report/ReportThemeToggle.tsx` (novo, stub funcional)

### 3.3 Critério de aceite

- `python3 design-tokens/build.py` roda sem erro.
- `npm run build` passa (Next.js).
- Visual regression: capturar `/reports/[id]` em light e dark — não quebrou (mesmo sem cover novo, os cards existentes devem renderizar; dark mode fica elegante, não quebrado).
- Pre-commit limpo; `pytest backend/tests -q` limpo.

### 3.4 Commits sugeridos

```
feat(design-tokens): expand scale — fonts, spacing, radius, shadows (ADR-117)
feat(design-tokens): dark mode tokens with calibrated gradients
feat(design-tokens): build.py emits standalone CSS for e6_render
feat(report): ReportThemeToggle with data-theme + localStorage
```

---

## 4. Fase 2 — Chart.js foundation

**Branch:** `agent/report-premium/phase2-charts/<ts>`

### 4.1 Dependências

```bash
cd frontend && npm install chart.js@^4 react-chartjs-2@^5 chartjs-plugin-datalabels@^2
```

Adicionar em `frontend/next.config.ts` ou `tsconfig.json` nada — funciona direto. Para SSR (Next App Router), envolver em `dynamic(() => import(...), { ssr: false })` todos os componentes de chart (Chart.js depende de `window`).

### 4.2 Componentes a criar

Todos em `frontend/src/components/report/charts/`:

| Arquivo | Propósito | Base no exemplo |
|---------|-----------|-----------------|
| `ChartRegistry.ts` | Registro único de escalas/plugins Chart.js + datalabels (evita tree-shaking quebrar) | — |
| `ChartCanvas.tsx` | Wrapper com `dynamic` SSR-off + `aspect-ratio` + dark-mode aware | — |
| `ChartBar.tsx` | Bar chart simples + agrupado | receita vs despesa |
| `ChartStackedBar.tsx` | Stacked com legend agrupada | categorias despesa |
| `ChartDonut.tsx` | Doughnut com `cutout` + label central opcional | patrimônio_doughnut |
| `ChartPie.tsx` | Pie clássico | — |
| `ChartLine.tsx` | Line + area fill opcional | evolução patrimonial |
| `ChartCombo.tsx` | Bar + Line no mesmo canvas (dois eixos) | — |
| `ChartWaterfall.tsx` | Waterfall via bar com floating bars | `waterfall_if` |
| `ChartGaugeSemi.tsx` | Semi-circle gauge via doughnut `rotation:-90 circumference:180` | `#chart-score-gauge` |
| `ChartConclusion.tsx` | Box de texto pós-gráfico (`.chart-conclusion`) | linha 298 |
| `ChartNav.tsx` | Navegação temporal (dots + setas) | linhas 349–379 |
| `PeriodToggle.tsx` | Segmented control 3M/6M/12M/YTD/ALL (já existe — auditar; expandir API) | linhas 381–413 |

### 4.3 API consistente

Cada chart exporta:

```ts
type ChartProps<TDatum> = {
  data: TDatum;                    // shape tipado por chart
  title?: string;
  subtitle?: string;
  conclusion?: string;             // texto curto — render automático de <ChartConclusion>
  periodWindow?: PeriodWindow;     // controlled by parent via <PeriodToggle>
  onPeriodChange?: (w: PeriodWindow) => void;
  height?: number | "auto";
  printFallbackSrc?: string;       // PNG base64 para print (injetado em build)
  "data-testid"?: string;
};
```

**Nunca** use `any`. Cada chart tem `TDatum` próprio documentado.

### 4.4 Dark mode em charts

Grid lines, tick labels e legendas precisam ler cores via `getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted')`. Encapsule em `useChartTheme()` hook — retorna `{ gridColor, textColor, palette[] }`. Hook re-dispara em mudança de `data-theme`.

### 4.5 Critério de aceite

- Storybook local (ou página `/reports/_dev/charts`) renderiza cada chart com fixture estática.
- Print-preview do Chrome mostra PNG fallback (não SVG vazio).
- Testes unitários Vitest para `useChartTheme` e transformações de dados (não precisa teste visual Playwright ainda — vem na Fase 12).

---

## 5. Fase 3 — UI primitives

**Branch:** `agent/report-premium/phase3-primitives/<ts>`

### 5.1 Componentes

Todos em `frontend/src/components/report/ui/`:

| Componente | Props mínimas | Mapeamento CSS |
|------------|---------------|----------------|
| `Card` | `variant?: 'default'\|'feature'\|'success'\|'warn'\|'critical'\|'primary'\|'neutral'\|'top-danger'\|'top-accent'\|'highlight'`, `children` | `.card`, `.card-feature` etc. |
| `CardTitle` | `as?: 'h2'\|'h3'`, `color?: 'primary'\|'green'\|'red'`, `size?: 'md'\|'lg'` | `.card-title`, `.card-title-*` |
| `CardSubtitle` | `children` | `.card-subtitle` |
| `Alert` | `severity: 'info'\|'success'\|'warning'\|'danger'`, `children` | `.alert-*` |
| `Badge` | `color: 'green'\|'red'\|'yellow'\|'blue'\|'neutral'`, `children` | `.badge-*` |
| `IconBadge` | `color: 'blue'\|'green'\|'red'\|'orange'\|'dark'`, `children` (1–2 chars) | `.icon-badge-*` |
| `SectionDivider` | `icon?: ReactNode` | `.section-divider` + `.section-divider-icon` |
| `KpiCard` | `label`, `value`, `sub?`, `tone?: 'default'\|'green'\|'red'\|'blue'`, `hero?: bool`, `accent?: 'default'\|'accent'\|'danger'\|'primary'`, `progress?: {value: 0..1, tone: 'green'\|'blue'\|'red'}` | `.kpi-card`, `.kpi-hero`, `.kpi-progress` |
| `KpiGrid` | `columns?: 4\|6`, `children` | `.kpi-grid`, `.dash-kpis` |
| `KpiStrip` | `items: {label, value, meta?}[]` | `.proj-kpi-strip` |
| `ScoreCard` | `value: 0..100`, `classe`, `breakdown: {dimensao, valor, peso, contrib}[]`, `formula?` | `.score-card-wrap` + `.score-breakdown` |
| `PontoForteItem` | `icon`, `titulo`, `descricao` | `.ponto-forte-item` |
| `PontosFortesList` | `items: PontoForteProps[]` | `.pontos-fortes-list` |
| `CollapsibleSectionHeader` | `title`, `collapsed`, `onToggle`, `hint?` (quando collapsed) | `.section-header` + `.collapse-icon` |
| `SectionSummary` | `children` (1–2 frases) | `.section-summary` |
| `TwoColCards` | `left`, `right` | `.two-col` |
| `SplitCards` | idem, com `min-height` equalizado | `.split-cards` |
| `ComparisonBlock` | `before: {titulo, valor}`, `after: {titulo, valor}` | `.comparison` |
| `PriorityBadge` | `level: 'alta'\|'media'\|'baixa'` | `.priority-badge` |
| `DeadlineBadge` | `iso`, computa `vencida`/`urgente`/`ok` | `.deadline-badge` |
| `EffortBadge` | `effort: 'S'\|'R'\|'O'` | `.effort-badge-*` |

### 5.2 Princípios

- **Sem `className` prop em consumidores** a menos que seja flag de layout externo. Variant > className.
- **Sem inline `style={{ color: '#...' }}`** no código final. Se precisar cor dinâmica, use `style={{ color: 'var(--color-accent)' }}` lendo token.
- **Dark mode gratuito** — todos os primitivos referenciam vars CSS que já têm override em `[data-theme="dark"]`.

### 5.3 Critério de aceite

- Página `frontend/src/app/(dev)/reports/primitives/page.tsx` (gated por `process.env.NODE_ENV !== 'production'`) renderiza todos os primitivos com todas as variants.
- Tipos exportados em `components/report/ui/index.ts`.
- Teste Vitest mínimo: cada componente renderiza sem warning.

---

## 6. Fase 4 — Shell: cover + topnav + toolbar

**Branch:** `agent/report-premium/phase4-shell/<ts>`

### 6.1 Componentes

- `ReportCover` (`components/report/ReportCover.tsx`):
  - Gradient + `::before`/`::after` blobs (CSS puro).
  - `cover-badge` em caps-lock.
  - Título principal + subtítulo com gradient-clip (Plus Jakarta Sans 800 / 600).
  - Grid de 4 `cover-meta-card` — props: `meta: {label, value}[]`.
  - Props: `title`, `subtitle`, `badge`, `meta[]`. Todos vêm do snapshot de dados.
- `ReportTopNav` (`components/report/ReportTopNav.tsx`):
  - Sticky top, gradiente `linear-gradient(90deg, #0F2A44, #152F4A)`.
  - `nav-brand` à esquerda (logo Mathoms).
  - `nav-scroll` — horizontal scroll em mobile.
  - 3 grupos por modo (`.nav-strategic`, `.nav-dashboard`, `.nav-usa`) — troca via `data-mode`.
  - `ModeToggle` + `ThemeToggle` à direita.
  - Active link via `IntersectionObserver` observando cada `<section id="...">`.
- `ModeToggle` (`components/report/ModeToggle.tsx`):
  - 3 botões (`Estratégico`/`Tático`/`USA`) — já integrados com `ReportModeProvider`.
- `BackToTop` + `GoToBottom` (`components/report/FloatingNav.tsx`):
  - Mostra/esconde via scroll listener (`opacity` transition). Debounce 100ms.
- `SkipNav` (`components/report/SkipNav.tsx`):
  - Primeiro foco da página, salta para `<main>`.
- `ExportToolbar` (`components/report/ExportToolbar.tsx`):
  - Botões: "Baixar HTML" (chama endpoint existente), "Baixar PDF" (print → save), "Copiar link" (clipboard).

### 6.2 Integração em `ReportShell`

- `<SkipNav />` primeiro filho.
- `<ReportCover />` antes de `<ReportTopNav />` (hero aparece ao abrir, nav fica sticky ao rolar).
- `<ReportTopNav />` sticky.
- Sidebar `<ReportToc />` **mantida** — coexistem (usuário decidiu #3).
- `<BackToTop />` + `<GoToBottom />` fixos.
- `<ExportToolbar />` antes do `<Footer />`.

### 6.3 Critério de aceite

- Screenshots manuais: hero renderiza com gradient e meta cards em light e dark.
- Sticky nav não sobrepõe conteúdo (testar scroll).
- `tab`-navegação funcional (skip-nav aparece no primeiro `tab`, mode/theme toggle focáveis, nav links focáveis).
- Mobile (<768px): hero compacta, nav esconde labels, sidebar vira drawer ou esconde.
- Lighthouse acessibilidade ≥95.

---

## 7. Fase 5 — Layout YAML expansion

**Branch:** `agent/report-premium/phase5-layout/<ts>`

### 7.1 Entregas

Atualizar `config/report_layout.yaml` para refletir **todos** os cards/charts do exemplo. Exemplo de diff (fragmento):

```yaml
estrategico:
  sections:
    - id: "S1"
      title: "Patrimônio — Estrutura e Composição"
      summary: true                   # novo: renderiza <SectionSummary>
      charts:
        - id: "patrimonio_doughnut"
          enabled: true
          conclusion: true            # novo: espera chart_conclusions[...]
        - id: "waterfall_if"
          enabled: true
          conclusion: true
        - id: "score_gauge"
          enabled: true               # movido para S10 se fizer mais sentido — decidir na fase
      cards:
        - id: "perfil_familia"
          variant: "feature"
          size: "full"
        - id: "patrimonio_resumo_tabela"
          variant: "default"
          size: "full"
        - id: "pontos_fortes"
          variant: "success"
          size: "full"
        - id: "comparacao_anterior"   # novo — comparison block
          variant: "neutral"
          size: "full"
          enabled: false              # liga após Fase 6 entregar os dados
```

Para cada seção (S1–S10, T1–T6, U1–U4, APP_A–APP_E): enumerar cards/charts a partir de uma varredura do HTML do exemplo. Marcar `enabled: false` itens que dependem de dados ainda não entregues na Fase 6 — liga no commit correspondente.

### 7.2 Codegen

Rodar `python3 dev/codegen_report_layout.py` após cada mudança no YAML. Comitar `frontend/src/generated/report-layout.ts` e `backend/app/generated/report_layout.py` **no mesmo commit** que o YAML.

### 7.3 Critério de aceite

- Lint YAML passa (`pre-commit`).
- Codegen produz TS/py válidos (`tsc --noEmit` + `ruff check`).
- `ReportShell` itera o novo YAML sem quebrar (stubs aparecem para cards/charts ainda não migrados).

---

## 8. Fase 6 — Pipeline E5: campos novos

**Branch:** `agent/report-premium/phase6-e5-data/<ts>`

> Essa fase é a **mais arriscada**. Mexe em `pipeline/domain/services/` e no snapshot. Golden tests de paridade podem quebrar. Siga rigorosamente o padrão `tests/test_e3_main_with_store_parity.py`.

### 8.1 Campos a adicionar

Da Tabela C do `REPORT_PREMIUM_GAPS.md` (Fase 0). Lista **provável** (refinar na discovery):

| Campo | Origem | Fonte | Esforço |
|-------|--------|-------|---------|
| `score` (objeto) | Determinística + LLM para classe | novo service `FinancialScoreCalculator` | O |
| `meta_if` | Determinística a partir de `independencia.*` | extensão em service existente | S |
| `chart_conclusions` (dict) | LLM na E5, um prompt por chart id | novo service `ChartConclusionGenerator` + prompt template em `config/prompts/chart_conclusions.md` | R |
| `section_summaries` | LLM | novo service `SectionSummaryGenerator` | R |
| `pontos_fortes` | LLM + regras | extensão de narrativas existentes | R |
| `cerbasi_presente_futuro` | Determinística a partir de `fluxo_caixa.*` | regra nova | S |
| `capa.meta` | Determinística | derivado de metadata já existente | S |
| `comparisons` | Determinística a partir de snapshot anterior | requer fetch do snapshot t-1 | O |
| `tatico.kanban.itens` | Determinística a partir de `tarefas` + `alertas` | transformação + enum | R |
| `tatico.timeline` | Já existe ou deriva de `proximos_passos` | verificar | S |
| `tatico.changelog` | Determinística a partir de diff snapshot t-1 vs t | O | — |

Esforços: S (≤4h), R (4–12h), O (>12h — quebrar em subtarefas).

### 8.2 Padrão obrigatório

- Cada campo é **value object tipado** Pydantic (ADR-102 R18).
- Services recebem `config: ValueObjectConfig`, não `StageConfig` inteiro (ADR-089/097).
- **Dinheiro** sempre `Money` (ADR-090). Wire = string decimal.
- Warnings = dataclasses tipadas com `.format()` (ADR-097 D1).
- Golden test de paridade: input fixture → output JSON com campo novo; comparado byte-a-byte (tolerância `0.01` em whitelist monetária).
- Schema em `config/schemas/e5.schema.json` atualizado; `make update-openapi-snapshot` depois de tocar endpoint.

### 8.3 Migração no `ReportAnalysisData`

- Cada campo novo é **opcional** (`?`) no TS. Seções consomem com default seguro. Assim a Fase 7 pode começar antes da Fase 6 terminar todos os campos.

### 8.4 Critério de aceite

- `pytest tests -q` verde — goldens atualizados com commits explícitos.
- `pytest backend/tests -q` verde.
- Schema E5 valida fixtures de produção (varredura dos snapshots disponíveis em `storage/`).
- Nenhum `pipeline/**` importa `fastapi`/`celery`/`sqlalchemy` (check automático).
- Nenhum `float` em campo monetário.

### 8.5 🛑 PAUSA antes do merge

Rodar o pipeline inteiro em uma fixture de produção e comparar o snapshot novo com o antigo. Se algum campo existente mudou inesperadamente → investigar antes de merge. Não siga para Fase 7 sem esse gate.

---

## 9. Fases 7–10 — Migrar seções

**Branches:** `agent/report-premium/phase{7,8,9,10}-sections-*/<ts>`

### 9.1 Padrão por seção

Cada seção migra em **4 commits sequenciais**:

1. **`feat(report): S1 visual skeleton`** — substitui o componente atual por estrutura nova com primitivos da Fase 3, mock data se necessário, sem charts ainda. Section-summary, cards, divider, footer. Deve renderizar bonito mesmo sem gráficos.
2. **`feat(report): S1 wire data from snapshot`** — remove mocks, conecta `ReportAnalysisData`. Trata ausência de campo novo (Fase 6) com fallback silencioso (não quebra a seção).
3. **`feat(report): S1 charts with Chart.js`** — adiciona os charts da Fase 2 + `PeriodToggle` onde aplicável + `ChartConclusion`. Verifica print fallback.
4. **`test(report): S1 playwright snapshot + a11y`** — screenshot em light/dark/print, axe-core sem violations críticas.

### 9.2 Ordem recomendada

**Fase 7 (estratégica) — ordem por impacto visual:**
- S10 Síntese (abre com ScoreCard + KpiHero — "primeira impressão" forte)
- S1 Patrimônio (doughnut + waterfall)
- S2 Fluxo de caixa (stacked bar + combo receita/despesa)
- S3 Investimentos (pie + tabela + comparison)
- S7 Independência financeira (KpiStrip de projeção + gauge)
- S4 Imóveis
- S8 Tributário
- S9 Riscos (alert-heavy)

**Fase 8 (tático):** T4 alertas → T1 fluxo → T2 aportes → T3 tarefas (Kanban é pesado — reservar sub-commit dedicado) → T5 próximos passos → T6 notas.

**Fase 9 (USA):** U1 → U2 → U3 → U4.

**Fase 10 (apêndices):** APP_A existente refatorado → APP_B premissas → APP_C cenários → APP_D referências → APP_E próximos ciclos. B/C/D/E são novos — estrutura cards + tabelas, dados simples.

### 9.3 Kanban (T3) — atenção especial

- `<Kanban>` `<KanbanColumn>` `<KanbanCard>` em `components/report/ui/kanban/`.
- Props aceitam `onItemMove?` — **não persistir** por ora (sem backend). Estado local + localStorage com chave `mathoms:kanban:<reportId>`. Esse é um desvio de stateless: **aceitável porque é client-only**. Documentar em `docs/STATELESS_AUDIT.md`.
- Drag-and-drop: `@dnd-kit/core` (leve, bem-mantido). Adicionar em `frontend/package.json`.

### 9.4 T6 Notas

- Textarea com autosave a cada `keyup` debounced 500ms.
- Storage: localStorage (`mathoms:notas:<reportId>`). Indicador `.notas-save-dot` muda para `.saving` enquanto escreve.
- Botões "Copiar markdown" (usa `turndown` — já referenciado no exemplo) e "Limpar".

### 9.5 Critério de aceite por seção

- Visual corresponde ao exemplo ao comparar screenshots lado-a-lado (tolerância de posicionamento, não pixel).
- Sem `console.error` em dev.
- Sem `any`.
- `npm test -- --run` passa.
- Lighthouse performance ≥85 na seção isolada (sem rede).

---

## 10. Fase 11 — `e6_render.py` paridade ❌ CANCELADA

> ❌ **Cancelada 2026-04-24 via [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).**
> Conteúdo abaixo mantido apenas como registro histórico do desenho
> original (Jinja2) e da revisão de 2026-04-24 (Next SSR sob ADR-124).
> Nenhuma das duas abordagens será executada. A execução real é a
> **remoção** do renderer, tracked em BACKLOG.md sob a lane
> `adr-129-e6-kill`.



**Branch:** `agent/report-premium/phase11-e6-parity/<ts>`

### 10.1 Abordagem

O `e6_render.py` hoje provavelmente monta HTML procedural. Duas opções:

- **(a)** Reescrever com Jinja2 — templates em `scripts/e6/templates/` (um por seção). Recomendado.
- **(b)** Manter procedural e só trocar o CSS + gerar placeholders onde o exemplo usa `{{PLACEHOLDER}}`.

Vá com (a). Jinja2 já é dependência usada indiretamente pelo FastAPI. Isolar o render em `scripts/e6/renderer.py` + `templates/` mantém `e6_render.py` fino como orquestrador.

### 10.2 Reuso do CSS

- `design-tokens/build.py` (Fase 1) já produz o CSS standalone. O template Jinja carrega esse CSS inline (como o exemplo faz).
- Chart.js standalone: manter os `<script>` do CDN exatamente como no exemplo (`chart.umd.min.js` + `datalabels` + `turndown`). Isso **é** o modelo do exemplo — HTML auto-contido para email/backup.
- JS inline de inicialização dos charts: extrair do React Runtime e regravar como vanilla. Onde React usa `useChartTheme`, o standalone lê diretamente `getComputedStyle`. Duplicação aceita (diferentes runtimes).

### 10.3 Critério de aceite

- `python3 scripts/e6_render.py <args>` gera HTML que passa nos **19 checks V1–V19** (`scripts/e6/validate.py`).
- Abrir o HTML no Chrome: visual ~idêntico à rota `/reports/[id]` (tolerância de estado cliente — kanban e notas aparecem em estado "empty").
- Dark mode funciona: toggle no HTML standalone muda o tema via `data-theme` + localStorage.
- Print do Chrome gera PDF legível (sem canvas vazio — fallback PNG presente).

### 10.4 🛑 PAUSA

Comparar visualmente `e6_render.py` output com o exemplo em 3 cenários: fixture pequena (1 conta), fixture média (múltiplos bancos), fixture grande (dados reais redacted). Aprovação humana obrigatória antes do merge.

---

## 11. Fase 12 — Print + a11y + tests ⏭ ESCOPO REDIRECIONADO

> ⏭ **2026-04-24:** a Fase 12 como descrita (Playwright com snapshot do
> `e6_render.py` output, diff PDF contra baseline do renderer Python)
> **perde sentido** com [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).
> Os itens que sobrevivem — **print CSS no React**, axe-core, keyboard-nav,
> Playwright de fluxo da rota `/reports/[id]` — viram uma lane dedicada
> em F11 se prioritários. Conteúdo abaixo mantido como referência do
> que já era útil independente do E6.



**Branch:** `agent/report-premium/phase12-polish/<ts>`

### 11.1 Print CSS

Copiar bloco `@media print` do exemplo (linhas 661–688) adaptando nomes de classe onde divergiu. Pontos críticos:

- `.chart-print-img` — cada `<ChartCanvas>` precisa emitir um `<img>` irmão gerado em runtime via `canvas.toDataURL()` depois do primeiro render. Esconde em screen, mostra em print.
- `@page { margin: 15mm; }` + `@page :first { margin-top: 0 }` para cover sangrar.
- `print-color-adjust: exact` em hero, badges, alerts, cards coloridos.

### 11.2 Acessibilidade

- Rodar `axe-core` em cada seção via Playwright e falhar build se houver violações **critical** ou **serious**.
- Keyboard-nav: fluxo `tab` → skip-nav → theme → mode → sidebar TOC → first section → charts → export.
- `aria-label` em ícones sem texto (FloatingNav, ThemeToggle, ModeToggle).
- Contraste WCAG AA mínimo (AAA onde possível) — verificar tokens dark.

### 11.3 Testes Playwright

Em `frontend/tests/e2e/reports/`:

- `cover.@critical.spec.ts` — hero renderiza, meta-cards visíveis, dark mode toggleia.
- `navigation.@critical.spec.ts` — clique em nav link faz scroll; IntersectionObserver atualiza active.
- `sections.strategic.spec.ts` — percorre S1→S10, screenshot por seção, light + dark.
- `sections.tactical.spec.ts` — idem para T1→T6, inclui Kanban drag básico.
- `print.spec.ts` — CDP `Page.printToPDF`, diff contra baseline PDF.

### 11.4 Critério de aceite

- Suíte `@critical` 100% verde no CI.
- Lighthouse: Performance ≥85, Accessibility ≥95, SEO ≥90, Best Practices ≥95.
- `pytest tests -q` + `pytest backend/tests -q` + `npm test -- --run` + `npm run test:e2e -- --grep @critical` todos verdes **na mesma execução local** antes do push.

---

## 12. Fase 13 — Rollout & docs ❌ ABSORVIDA PELA ADR-129

> ❌ **2026-04-24:** A Fase 13 previa "feature flag + CHANGELOG + delete
> `e6_render.py`" como passo final do Report Premium. O `delete` acontece
> agora sob [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side),
> não como rollout, mas como **remoção definitiva** do renderer legado.
> CHANGELOG e docs são atualizados no mesmo PR docs-only que emite ADR-129
> e nos PRs de código subsequentes. Feature flag é dispensável (sem prod,
> cutover direto).



**Branch:** `agent/report-premium/phase13-rollout/<ts>`

### 12.1 Feature flag

- Env `MATHOMS_REPORT_PREMIUM_UI=true` em `.env.example` (default true em dev, false em staging até validar).
- Se `false`: rota `/reports/[id]` continua no shell antigo (precisa manter o código antigo arquivado em branch, não no main). **Decisão:** sem feature flag, cutover direto — rollback é `git revert` do PR da Fase 13. **Mais simples, aceito risco.**

### 12.2 Docs

Atualizar, cada um em commit separado:

- `docs/DECISIONS.md` — ADR-117 (design premium), ADR-118 (Chart.js), ADR-119 (notas localStorage), ADR-120 (kanban localStorage). Numeração real depende do estado no momento.
- `docs/CHANGELOG.md` — entrada "Premium report UI (A6g.X · ADR-117..120)".
- `docs/ARCHITECTURE.md §10` — nova estrutura `components/report/{ui,charts,sections,shell}`.
- `docs/RUNBOOK.md` — como toggle de tema, onde localStorage é limpo, como regerar `e6` standalone.
- `docs/BACKLOG.md` — mover a sprint para `CHANGELOG`.
- `CLAUDE.md` — adicionar na tabela "Onde procurar contexto" referência ao novo design system de relatório.

### 12.3 Smoke test humano

Seguir `docs/SMOKE_TEST_HUMAN.md` com adições:
- Abrir 3 relatórios reais (tamanhos diferentes).
- Togglear tema, modo, period em cada.
- Exportar PDF.
- Rodar `e6_render.py` em fixture e comparar.

---

## 13. Paralelização (caminho crítico)

```
Fase 0 (discovery)
   ↓
Fase 1 (tokens) ─→ Fase 2 (charts) ─┐
                Fase 3 (primitives) ─┼─→ Fase 4 (shell) ─→ Fase 7+8+9+10 (sections, paralelos) ─→ Fase 11 (e6) ─→ Fase 12 (polish) ─→ Fase 13 (rollout)
                                     │
Fase 5 (YAML) ─→ Fase 6 (E5 data) ───┘
```

- **Agente A** pode tocar Fases 1, 2, 4 em série.
- **Agente B** pode tocar Fase 3 após Fase 1.
- **Agente C** pode tocar Fases 5 + 6 após Fase 0.
- Fases 7/8/9 são naturalmente paralelas entre agentes (seções distintas = arquivos distintos). A regra do CLAUDE.md §Antes de pegar uma task aplica: checar `git worktree list` + `origin/agent/*` antes de escolher.

---

## 14. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Chart.js bundle size explode o frontend | M | M | Dynamic import + route-split em `/reports/**` apenas. Medir bundle com `@next/bundle-analyzer` na Fase 2. |
| Golden tests de E5 quebram em massa | A | A | Na Fase 6, campos novos são **aditivos** e **opcionais** no schema. Existing fields não mudam. Goldens só atualizam para incluir os novos. |
| Dark mode quebra em algum screenshot | M | B | Playwright multi-tema (light + dark) já na Fase 12. |
| Score LLM gera resultado inconsistente entre runs | M | M | `temperature=0` + seed fixo + cache Redis por snapshot (TTL 24h). Documentar determinismo parcial. |
| Kanban localStorage perde dados | B | B | Avisar usuário no footer do componente + botão "exportar estado" que copia JSON. |
| Print PDF do Chrome ignora `@page` em algumas versões | M | B | Testar Chrome ≥120 (mínimo suportado no projeto); fallback `user-select: none` no header. |
| PRs gigantes travando review | A | A | **Regra dura:** cada PR de seção ≤800 linhas. Se estourou, quebrar em sub-PRs "skeleton" + "data" + "charts". |

---

## 15. Checklist de início de cada fase (para o LLM)

Cole no início de cada sessão:

```
□ git fetch origin && git status
□ git log --oneline origin/main..HEAD -10
□ git worktree list                       # §antes de pegar task
□ Confirmar branch agent/report-premium/... correta; se no worktree `.claude/worktrees/*`,
  criar sub-branch antes de qualquer edit
□ Ler o ramo da fase neste plano de ponta a ponta
□ Ler CLAUDE.md §Git e commits se faz >24h desde a última sessão
□ TodoWrite com as entregas da fase
□ Antes de tocar CLAUDE.md / CHANGELOG / BACKLOG / DECISIONS: git log -5 --oneline origin/main -- <arquivo>
□ Ao terminar: git diff --stat (≤300 linhas?), pre-commit, pytest, npm test, push
□ Anunciar commit hashes e push no chat
```

---

## 16. O que **não** está no escopo

Para o LLM não ficar tentado a "melhorar":

- Trocar Recharts em telas que não são `/reports/**`.
- Refatorar `pipeline/domain/services/` além do necessário para os campos novos da Fase 6.
- Adicionar i18n (relatório é pt-BR fixo — ADR existente).
- Substituir Tailwind por CSS Modules no resto do projeto (fora de scope).
- Mover assets para CDN próprio.
- Introduzir Storybook como dependência produtiva (páginas `_dev/` bastam).

Se surgir necessidade legítima de extrapolar, **pausar** e pedir aprovação — registrar como nova ADR, não fazer "de orelhada".

---

**Fim do plano.**
Próxima ação do executor: abrir Fase 0.
