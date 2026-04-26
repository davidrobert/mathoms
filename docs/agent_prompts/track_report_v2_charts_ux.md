# Track Report v2.E — Charts UX (paridade visual final dos charts)

> **Lane ID família:** `report-v2-charts-ux` (8 sub-lanes — ver §3)
> **Branch prefix:** `agent/report-v2-<sub-slug>/<yyyyMMdd-HHmm>`
> **Depende de:** v1 ✅ (10 fases). Onda v2.E é independente das outras
> ondas v2 — não bloqueia nem é bloqueada por v2.A/B/C/D.
> **Paralelo com:** v2.4, v2.6, v2.7, v2.D.1+v2.8, v2.9, v2.10
> (arquivos disjuntos — ver §2.4)
> **Conflita com:** v2.5 (`score-dto`) — **absorvida nesta onda como
> v2.E.7**. Não pegar v2.5 isolada; está fundida ao plug do `ScoreCard`.
> **Onda v2:** E (nova)
> **Sprint:** Report Premium UI · v2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:**
> - [BACKLOG.md — Report Premium UI v2 lanes](../BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml)
> - [REPORT_PREMIUM_PLAN.md §17 — v2 roadmap](../REPORT_PREMIUM_PLAN.md)
> - [DECISIONS.md ADR-117](../DECISIONS.md) — Chart.js para `/reports/**`
> - Meta-prompt v2: [track_report_v2.md](track_report_v2.md)

> **Objetivo (1 frase):** terminar a migração Recharts→Chart.js dentro
> de `/reports/**` que ADR-117 Fase 2 abriu mas não fechou na Fase 7,
> introduzir `PeriodToggle` (3M/6M/12M/Ano), plugar o `ScoreCard`
> premium em S1, e adicionar slide window 12m com tooltip por stack
> e legenda agrupada no chart "Receita vs Despesa Mês a Mês" — fechando
> a paridade visual com `EXEMPLO_DE_RELATORIO.html` para os 5 charts
> mais visíveis do relatório.

---

## 1. Por que esta lane existe

[ADR-117](../DECISIONS.md) (2026-04-23) decidiu **Chart.js 4 +
react-chartjs-2 + datalabels** para `/reports/**`, com Recharts
escopo-restringido. A Fase 2 do plano construiu os primitivos
([primitives/](../../frontend/src/components/report/charts/primitives/)
— `ChartCanvas`, `ChartBar`, `ChartDonut`, `ChartGaugeSemi`,
`ChartCombo`, `ChartLine`, `ChartWaterfall`, `ChartRegistry` com print
fallback canvas→PNG e tema via `useChartTheme`). A Fase 3 construiu o
[`ScoreCard` premium](../../frontend/src/components/report/ui/ScoreCard.tsx)
(badge classe + gauge Chart.js + breakdown table + fórmula).

Mas **a substituição efetiva nas seções não foi concluída**. Os 5
charts que o relatório expõe na primeira dobra continuam em **Recharts**
(débito da migração F2.A/F2.B antiga, anterior à ADR-117):

| Chart | Componente atual (Recharts) | Onde é wired |
|---|---|---|
| Score Financeiro | [ScoreGaugeChart.tsx](../../frontend/src/components/report/charts/ScoreGaugeChart.tsx) (`RadialBarChart`) | [S1PatrimonioSection.tsx:12,72](../../frontend/src/components/report/sections/S1PatrimonioSection.tsx) |
| Fluxo de Caixa Mensal | [FluxoMensalChart.tsx](../../frontend/src/components/report/charts/FluxoMensalChart.tsx) (`BarChart`) | [S2FluxoCaixaSection.tsx:9,60](../../frontend/src/components/report/sections/S2FluxoCaixaSection.tsx) |
| Receita por Fonte | [ReceitaBarChart.tsx](../../frontend/src/components/report/charts/ReceitaBarChart.tsx) | [S2FluxoCaixaSection.tsx:10,62](../../frontend/src/components/report/sections/S2FluxoCaixaSection.tsx) |
| Despesas por Categoria | [DespesasDoughnutChart.tsx](../../frontend/src/components/report/charts/DespesasDoughnutChart.tsx) | [S2FluxoCaixaSection.tsx:11,63](../../frontend/src/components/report/sections/S2FluxoCaixaSection.tsx) |
| Receita vs Despesa — Mês a Mês | [ReceitaDespesaMensalChart.tsx](../../frontend/src/components/report/charts/ReceitaDespesaMensalChart.tsx) (`AreaChart`) | [S2FluxoCaixaSection.tsx:12,65](../../frontend/src/components/report/sections/S2FluxoCaixaSection.tsx) |

Gap funcional vs `EXEMPLO_DE_RELATORIO.html`:

1. **Score**: HTML usa gauge semi-circular profissional com 5 segmentos
   coloridos (`EXEMPLO_DE_RELATORIO.html:7984-8120`); React usa
   `RadialBar` Recharts plano. **`ScoreCard` Chart.js já existe**, só
   falta plugar em S1 e adicionar `chart-context` + `chart-conclusion`.
2. **Fluxo Mensal / Receita Bar / Despesas Doughnut / Receita vs Despesa**:
   HTML tem `period-toggle` (3M/6M/12M/Ano) acima do canvas
   (`EXEMPLO_DE_RELATORIO.html:1776,1783,1790`); React **não tem
   `PeriodToggle`**.
3. **Receita vs Despesa — Mês a Mês**: HTML tem **slide window de 12m**
   com botões `‹/›` + dots (`EXEMPLO_DE_RELATORIO.html:1797-1804`),
   **tooltip que só mostra o stack hovered + total**
   (`EXEMPLO_DE_RELATORIO.html:7796-7829`), **legenda agrupada
   "Receitas"/"Despesas" clicável** com strikethrough
   (`EXEMPLO_DE_RELATORIO.html:7902-7938`). React tem `AreaChart`
   simples com totais agregados — perde toda a granularidade
   por sub-fonte/sub-categoria que o backend já produz em
   `chart_receita_datasets[]` / `chart_despesa_datasets[]`
   ([fluxo_caixa_enricher.py:147-174](../../pipeline/domain/services/fluxo_caixa_enricher.py)).

**Esta onda fecha esses três gaps.** Não introduz Chart.js no projeto —
ele já é dep paga do `package.json` desde a Fase 2; introduz a
**finalização** da migração que ADR-117 mandou fazer.

---

## 2. Estrutura da onda (8 sub-lanes)

### 2.1 Grafo de dependências

```
v2.E.1 PeriodToggle + hook usePeriodWindow ──┐         (enabler, ≤4h)
                                             ├─→ v2.E.3 FluxoMensal Chart.js   (paralelo, 1d)
v2.E.2 types receita_datasets/despesa_datasets ┤      ├─→ v2.E.4 ReceitaBar Chart.js       (paralelo, 1d)
                                             │       ├─→ v2.E.5 DespesasDoughnut Chart.js (paralelo, 1d)
                                             │       └─→ v2.E.6 ReceitaDespesaMensal Chart.js + slide window (1-2d)
                                             │
                                             └─→ v2.E.7 ScoreCard plug + score.context/conclusion + DTO  (paralelo, ½-1d)
                                                          (absorve v2.5)

                          v2.E.3-7 todas ──→ v2.E.8 re-baseline + cleanup + ADR-13X (½d)
```

**Caminho crítico (1 agente serial):** E.1 → E.2 → E.6 → E.8 ≈ 3-4 dias.
**Caminho crítico paralelo (5 agentes):** E.1+E.2 (½d) → E.3/E.4/E.5/E.6/E.7
em paralelo (1-2d) → E.8 (½d) ≈ **2-3 dias**.

### 2.2 Tabela de sub-lanes

| Sub-lane | Slug branch | Esforço | Prio | Bloqueado por | Toca |
|---|---|---|---|---|---|
| **v2.E.1** PeriodToggle UI + hook `usePeriodWindow` | `report-v2-period-toggle` | S (≤4h) | P0 | — | `frontend/src/components/report/ui/PeriodToggle.tsx` (novo); `frontend/src/components/report/hooks/usePeriodWindow.ts` (novo); Vitest |
| **v2.E.2** TS types `receita_datasets`/`despesa_datasets` | `report-v2-fluxo-types` | S (≤2h) | P0 | — | [`frontend/src/types/report-analysis.ts:122-126`](../../frontend/src/types/report-analysis.ts) |
| **v2.E.3** FluxoMensal Recharts→Chart.js + PeriodToggle | `report-v2-fluxo-mensal-chartjs` | R (1d) | P1 | E.1 | [`FluxoMensalChart.tsx`](../../frontend/src/components/report/charts/FluxoMensalChart.tsx); [`_shared.ts`](../../frontend/src/components/report/charts/_shared.ts) |
| **v2.E.4** ReceitaBar Recharts→Chart.js + PeriodToggle (séries mensais) | `report-v2-receita-bar-chartjs` | R (1d) | P1 | E.1, E.2 | [`ReceitaBarChart.tsx`](../../frontend/src/components/report/charts/ReceitaBarChart.tsx) |
| **v2.E.5** DespesasDoughnut Recharts→Chart.js + datalabels + PeriodToggle | `report-v2-despesas-doughnut-chartjs` | R (1d) | P1 | E.1, E.2 | [`DespesasDoughnutChart.tsx`](../../frontend/src/components/report/charts/DespesasDoughnutChart.tsx) |
| **v2.E.6** ReceitaDespesaMensal Recharts→Chart.js + slide window 12m + tooltip stack + legenda agrupada | `report-v2-receita-despesa-chartjs` | R/O (1-2d) | P1 | E.1, E.2 | [`ReceitaDespesaMensalChart.tsx`](../../frontend/src/components/report/charts/ReceitaDespesaMensalChart.tsx) |
| **v2.E.7** Plugar `ScoreCard` premium em S1 + `score.context`/`score.conclusion` (absorve v2.5) | `report-v2-score-card-plug` | R (½-1d) | P1 | — | [`S1PatrimonioSection.tsx:12,72`](../../frontend/src/components/report/sections/S1PatrimonioSection.tsx); [`ScoreCard.tsx`](../../frontend/src/components/report/ui/ScoreCard.tsx); [`report-analysis.ts`](../../frontend/src/types/report-analysis.ts); backend `financial_score_calculator` |
| **v2.E.8** re-baseline + cleanup imports Recharts órfãos + ADR-13X | `report-v2-charts-rebaseline` | S (≤4h) | P0 | **todas as anteriores** | `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/`; [`_registry.ts`](../../frontend/src/components/report/charts/_registry.ts); deletar `ScoreGaugeChart.tsx`; nova ADR-13X |

### 2.3 Decisões de design pré-aprovadas

- **Lib:** Chart.js 4 + react-chartjs-2 + datalabels (já em deps; ADR-117).
  Recharts removido de `/reports/**`. Recharts permanece em
  `frontend/src/app/(app)/dashboard/_components/` e
  `frontend/src/components/charts/Mathom*.tsx` — **não tocar**.
- **Primitives:** reaproveitar
  [primitives/](../../frontend/src/components/report/charts/primitives/) —
  cada chart envolve `ChartBar` / `ChartDonut` / `ChartGaugeSemi`,
  não `ChartCanvas` direto.
- **Period toggle:** componente novo em `report/ui/PeriodToggle.tsx`,
  estado local em cada chart (não global). Estilo idêntico a
  `EXEMPLO_DE_RELATORIO.html:381-413` portado para tokens
  (`--brand-primary`, `--surface-card`).
- **Janela 12m do "Receita vs Despesa Mês a Mês":** **não usa
  PeriodToggle** — usa o slide window com prev/next/dots do exemplo
  (mais informativo para série temporal granular). Os outros 3 charts
  usam PeriodToggle. Decisão consciente para preservar paridade visual.
- **chart-context / chart-conclusion:** geração via **template TS no
  frontend** (v1). LLM-driven fica para v2.9 quando ADR fechar.
- **Print mode:** em `@media print` ou prop `printMode`, ocultar
  `PeriodToggle` e nav do slide window; charts fixam em **12m** (período
  mais informativo); chart-conclusion então é a do 12m.
- **Cantos do stack:** `borderRadius` por segmento (Chart.js suporta
  nativo via `borderRadius`/`borderSkipped`). Paridade exata com HTML.

### 2.4 Regras de paralelização

| Par | Pode rodar simultâneo? | Motivo |
|---|---|---|
| v2.E.1 ↔ v2.E.2 | ✅ Sim | UI primitive vs types — disjuntos |
| v2.E.3 ↔ v2.E.4 ↔ v2.E.5 ↔ v2.E.6 | ⚠ Coordenar | Disjuntos no chart, **mas todos editam `_shared.ts` e `_registry.ts`** — usar protocolo de hotspot do CLAUDE.md (commits atômicos + push imediato). Conflito é trivial de resolver (linhas adjacentes). |
| v2.E.7 ↔ qualquer Eyx | ✅ Sim | Toca S1 + `ScoreCard` + DTO score; charts E.3-6 são S2 |
| v2.E.8 ↔ qualquer | ❌ Não | Espera todos os charts mergeados (caso contrário re-baseline fica inconsistente) |
| Qualquer Onda E ↔ v2.4 (T2 Aportes) | ✅ Sim | Sections diferentes (S1/S2 vs T2) |
| Qualquer Onda E ↔ v2.6 (cards/) | ✅ Sim | `report/charts/` (Onda E) vs `report/cards/` (v2.6) — diretórios disjuntos |
| Qualquer Onda E ↔ v2.7 (DnD Kanban) | ✅ Sim | `Kanban.tsx` independente |
| Qualquer Onda E ↔ v2.D.1+v2.8 | ✅ Sim | Pipeline + render genérico, não toca charts |
| v2.E.8 ↔ v2.2b (Tático+USA baselines) | ✅ Sim | Snapshots disjuntos (E.8 re-captura S1+S2; v2.2b captura Tático+USA). **Coordenar timing do PR** apenas se ambos forem mergeados na mesma janela de 30min. |

---

## 3. Catálogo detalhado de cada sub-lane

### v2.E.1 — `PeriodToggle` + hook `usePeriodWindow`

**Branch:** `agent/report-v2-period-toggle/<ts>`
**Esforço:** S (≤4h)
**Prio:** P0 (enabler de E.3/E.4/E.5)

**Entrega:**

1. `frontend/src/components/report/ui/PeriodToggle.tsx`:
   ```ts
   export type Period = "3m" | "6m" | "12m" | "ytd";
   export interface PeriodToggleProps {
     value: Period;
     onChange: (p: Period) => void;
     periodLabel?: string;
     className?: string;
   }
   ```
   Visual idêntico a `EXEMPLO_DE_RELATORIO.html:1776` (linha
   `<div class="period-toggle-row">…<span class="period-label">…</span>`).
   Tokens: `--brand-primary` (active), `--surface-card` (bg),
   `--surface-border` (border).
2. `frontend/src/components/report/hooks/usePeriodWindow.ts`:
   ```ts
   export function usePeriodWindow(
     allLabels: readonly string[],
     period: Period,
     anchorDate?: Date,
   ): { start: number; end: number; label: string };
   ```
   Lógica: `12m` = últimos 12; `6m` = últimos 6; `3m` = últimos 3;
   `ytd` = de `jan/<ano corrente>` até último mês com dado. Anchor
   default = último mês de `allLabels`.
3. Adicionar `PeriodToggle` ao
   [`frontend/src/components/report/ui/index.ts`](../../frontend/src/components/report/ui/index.ts).
4. Vitest unit em `frontend/src/components/report/__tests__/`:
   - `usePeriodWindow.test.ts` — 4 cenários (3m/6m/12m/ytd) + edge cases (≤3 meses, anchor inválido).
   - `PeriodToggle.test.tsx` — render + click muda `value`.

**Critério de aceite:**
- [ ] `npm test -- --run` verde com 2 specs novas.
- [ ] Hook puro (zero side-effects, sem `useEffect` desnecessário).
- [ ] Componente sem state interno — controlado pelo pai.
- [ ] `tsc` verde, sem `any`.

**O que NÃO entrega:** uso real do toggle em chart algum (isso é E.3-E.6).

---

### v2.E.2 — TS types `receita_datasets`/`despesa_datasets`

**Branch:** `agent/report-v2-fluxo-types/<ts>`
**Esforço:** S (≤2h)
**Prio:** P0 (enabler de E.4/E.5/E.6)

**Entrega:**

1. Estender [`FluxoCaixaSummary.receita_despesa_mensal_detalhado`](../../frontend/src/types/report-analysis.ts:122-126):
   ```ts
   receita_despesa_mensal_detalhado?: {
     labels?: string[];
     totais_receita?: number[];
     totais_despesa?: number[];
     receita_datasets?: ChartSeries[]; // NOVO
     despesa_datasets?: ChartSeries[]; // NOVO
   };

   export interface ChartSeries {
     readonly label: string;
     readonly data: readonly number[];
     readonly backgroundColor?: string;
     readonly stack?: "receita" | "despesa";
     readonly borderRadius?: number;
   }
   ```
2. Confirmar que backend já entrega — sim, [`fluxo_caixa_enricher.py:168-174`](../../pipeline/domain/services/fluxo_caixa_enricher.py)
   já serializa em `to_legacy_dict()`. **Não tocar pipeline.**
3. Validar com `tsc` que nenhum consumidor existente quebra (campos
   opcionais, retrocompatível).

**Critério de aceite:**
- [ ] `tsc` verde.
- [ ] Nenhum import novo no backend.
- [ ] Snapshot E5 real renderiza sem warning de tipo.

---

### v2.E.3 — FluxoMensal Chart.js + PeriodToggle

**Branch:** `agent/report-v2-fluxo-mensal-chartjs/<ts>`
**Esforço:** R (1 dia)
**Prio:** P1
**Depende:** v2.E.1 ✅

**Entrega:**

1. Reescrever [`FluxoMensalChart.tsx`](../../frontend/src/components/report/charts/FluxoMensalChart.tsx)
   trocando `recharts` por `ChartBar` de
   [primitives](../../frontend/src/components/report/charts/primitives/).
2. Adicionar estado `period: Period` (default `"12m"`) e
   `<PeriodToggle>` acima do chart (visual `EXEMPLO_DE_RELATORIO.html:1776`).
3. Aplicar `usePeriodWindow` para slice de `labels` e `data` antes de
   passar ao `ChartBar`.
4. Adicionar **chart-context** acima do chart com texto auto-gerado:
   `"Janela dos últimos {N} meses ({first} a {last}). Receita
   recorrente média de {fmtBRL(receita_recorrente_mensal)}/mês versus
   despesa média de {fmtBRL(despesa_mensal_media)}/mês."` Recalcular ao
   mudar period.
5. **chart-conclusion** já é prop existente — manter, mas reformatar
   para o período selecionado.
6. **Print mode:** `useIsPrint()` (criar em `report/hooks/useIsPrint.ts`
   se não existir; `matchMedia("print")`) — quando true, esconder
   `PeriodToggle` e fixar `period="12m"`.

**Critério de aceite:**
- [ ] Visual no `/reports/[id]` com fixture `medium.json` paridade
      `EXEMPLO_DE_RELATORIO.html:1773-1779` para o card de Fluxo.
- [ ] Toggle 3M/6M/12M/Ano muda chart e textos sem reload.
- [ ] PDF via `pdf_renderer.py` (smoke local) renderiza chart sem
      botões de toggle, fixado em 12m.
- [ ] Zero import de `recharts` no arquivo.
- [ ] Vitest snapshot do componente atualizado.
- [ ] **Não atualizar baseline visual ainda** — isso é E.8.

---

### v2.E.4 — ReceitaBar Chart.js + PeriodToggle (séries mensais)

**Branch:** `agent/report-v2-receita-bar-chartjs/<ts>`
**Esforço:** R (1 dia)
**Prio:** P1
**Depende:** v2.E.1 ✅, v2.E.2 ✅

**Entrega:**

1. Hoje [`ReceitaBarChart.tsx`](../../frontend/src/components/report/charts/ReceitaBarChart.tsx)
   usa `por_fonte` (totais agregados sem decomposição mensal).
   **Trocar para usar `receita_datasets[]`** (séries mensais por fonte
   já entregues pelo backend).
2. Reescrever em Chart.js via `ChartBar`. Cada fonte vira 1 dataset
   horizontal stacked OU 1 barra agregada por fonte, conforme exemplo
   (`EXEMPLO_DE_RELATORIO.html:1781-1785` — single bar chart com 1 barra
   por fonte ordenada por valor).
3. Aplicar `usePeriodWindow` ao `receita_datasets[i].data` para
   somar dentro da janela escolhida; ordenar fontes por total
   desc; renderizar barras horizontais.
4. **chart-context** auto-gerado: `"Composição da receita total de
   {fmtBRL(total)} por fonte: {top3.join(', ')}"`.
5. **chart-conclusion** existente.

**Critério de aceite:**
- [ ] Toggle 3M/6M/12M/Ano recalcula e re-ordena.
- [ ] PDF: toggle escondido, 12m fixo.
- [ ] Zero import de `recharts`.
- [ ] Sem `any`, sem `Record<string, number>` exposto na API do componente.

---

### v2.E.5 — DespesasDoughnut Chart.js + datalabels + PeriodToggle

**Branch:** `agent/report-v2-despesas-doughnut-chartjs/<ts>`
**Esforço:** R (1 dia)
**Prio:** P1
**Depende:** v2.E.1 ✅, v2.E.2 ✅

**Entrega:**

1. Reescrever [`DespesasDoughnutChart.tsx`](../../frontend/src/components/report/charts/DespesasDoughnutChart.tsx)
   em `ChartDonut` (primitive). Hoje usa `despesas_por_categoria` (totais
   agregados); trocar para `despesa_datasets[]` (séries mensais por
   categoria) e somar dentro da janela.
2. **Datalabels:** ativar `chartjs-plugin-datalabels` (já em deps);
   mostrar `R$ Xk` no segmento se ≥ 5% (paridade `EXEMPLO_DE_RELATORIO.html:7966-7979`).
3. `PeriodToggle` + recálculo de fatias por período.
4. **chart-context** auto-gerado: `"Distribuição das despesas totais
   ({fmtBRL(total)}) entre {n} categorias..."`.
5. **chart-conclusion** existente.

**Critério de aceite:**
- [ ] Datalabels visíveis para fatias ≥ 5%.
- [ ] Toggle muda fatias.
- [ ] `cutout: '50%'` (donut, não pie).
- [ ] PDF: toggle escondido, 12m fixo.

---

### v2.E.6 — ReceitaDespesaMensal Chart.js + slide window + tooltip + legenda

**Branch:** `agent/report-v2-receita-despesa-chartjs/<ts>`
**Esforço:** R/O (1-2 dias)
**Prio:** P1
**Depende:** v2.E.2 ✅ (E.1 não, este chart usa slide window próprio)

**Entrega — esta é a sub-lane mais densa.** Replicar
`EXEMPLO_DE_RELATORIO.html:1794-1806` + script `:7756-7939`:

1. Reescrever [`ReceitaDespesaMensalChart.tsx`](../../frontend/src/components/report/charts/ReceitaDespesaMensalChart.tsx)
   trocando `AreaChart` Recharts por `ChartBar` Chart.js stacked com 2
   `stackId` (`"receita"`, `"despesa"`).
2. **Datasets:** consumir `receita_datasets[]` + `despesa_datasets[]`
   (E.2 expôs). 1 `<Bar>` por sub-fonte/sub-categoria, paleta fixa por
   dataset (cor já vem do backend em `backgroundColor`).
3. **Slide window 12m:**
   - State `offset: number` (default = `Math.max(0, totalMonths - 12)`).
   - Botões prev/next + dots (visual `EXEMPLO_DE_RELATORIO.html:1797-1803`).
   - Quando `totalMonths ≤ 12` → ocultar nav + dots.
4. **Tooltip custom** (`options.plugins.tooltip.callbacks`):
   - Title: `"<mês> — Receitas"` ou `"— Despesas"` (conforme stack hovered).
   - Body: lista entries do mesmo stack ordenadas desc, formato
     `"<label>: R$ X.XXX,XX"`.
   - Footer: `"Total: R$ Y.YYY,YY"`.
   - Implementação literal em `EXEMPLO_DE_RELATORIO.html:7798-7829`.
5. **Legenda agrupada custom** (não usar Chart.js legend default):
   - Componente `RDMLegend` em arquivo próprio (≤60 linhas).
   - 2 grupos: "Receitas" + "Despesas".
   - Swatches clicáveis: toggle `meta.hidden` no chart + classe
     `strikethrough` no item (paridade `EXEMPLO_DE_RELATORIO.html:7902-7938`).
6. **chart-context** + **chart-conclusion** existentes — paridade exata
   com `EXEMPLO_DE_RELATORIO.html:1796,1805`.
7. **Print mode:** ocultar nav + dots + legenda interativa; renderizar
   última janela 12m + bloco textual de totais consolidados.

**Critério de aceite:**
- [ ] Todos os 7 itens acima visíveis e funcionais no
      `/reports/[id]`.
- [ ] Vitest snapshot do tooltip com `stack=receita`.
- [ ] E2E Playwright `@critical`: rota → encontra card → clica `›` → label
      muda → clica swatch → dataset some.
- [ ] PDF tem chart legível com bloco textual no lugar dos controles.

**Nota:** os primitivos atuais não têm `ChartBarStacked` específico;
o `ChartBar` aceita `stack` por dataset via Chart.js options. Se o
agente identificar que falta API no primitive, **adicionar API ao
primitive** em commit separado dentro desta lane (`feat(chart-bar):
suporte a stack groups`) — não criar primitive novo.

---

### v2.E.7 — ScoreCard plug + score.context/score.conclusion (absorve v2.5)

**Branch:** `agent/report-v2-score-card-plug/<ts>`
**Esforço:** R (½-1 dia)
**Prio:** P1
**Absorve:** v2.5 (`report-v2-score-dto`) — **fechar v2.5 no BACKLOG ao
mergear este PR**.

**Entrega — 3 partes:**

**Parte A (frontend — plug do ScoreCard):**

1. Em [`S1PatrimonioSection.tsx:12,72`](../../frontend/src/components/report/sections/S1PatrimonioSection.tsx),
   trocar `<ScoreGaugeChart score={score} />` por
   `<ScoreCard … />` ([ScoreCard.tsx](../../frontend/src/components/report/ui/ScoreCard.tsx)).
2. Estender [`ScoreCardProps`](../../frontend/src/components/report/ui/ScoreCard.tsx):
   ```ts
   readonly context?: string;       // parágrafo abaixo do título
   readonly conclusion?: string;    // parágrafo abaixo do breakdown
   ```
3. Renderizar `context` + `conclusion` com classes `chart-context` /
   `chart-conclusion` (já existem em design-tokens; ver
   `EXEMPLO_DE_RELATORIO.html:297-298`).

**Parte B (frontend — DTO score top-level — escopo da v2.5 absorvida):**

Origem v2.5: hoje `score` está sendo lido com `as ScoreData` casting em
sections, sem campo top-level no `ReportAnalysisData`. Resolver:

1. Adicionar `score?: ScoreData` no top-level de `ReportAnalysisData`
   em [`report-analysis.ts`](../../frontend/src/types/report-analysis.ts).
2. Estender `ScoreData` com `context?: string` e `conclusion?: string`.
3. Remover casts `as ScoreData` em `S1PatrimonioSection.tsx` e
   onde mais houver (grep).

**Parte C (backend — score.context / score.conclusion):**

1. Localizar `financial_score_calculator` em
   `pipeline/domain/services/` (já entrega `valor`,
   `classificacao`, `breakdown`, `formula` — ver auditoria).
2. Adicionar campos `context: str` e `conclusion: str` no resultado,
   gerados via **template Python** simples:
   - `context = f"Indicador geral de saúde financeira da família, com
     score de {valor:.1f}/{max} ({classificacao}). Reflete equilíbrio
     entre pontos fortes e oportunidades de melhoria."`
   - `conclusion = f"A classificação '{classificacao}' reflete
     {top_drivers}."` — drivers do `breakdown` ordenados por
     `contribuicao` desc, top 2.
3. Atualizar goldens E5 (caminho B parity); rodar `make
   update-openapi-snapshot` se houver mudança de contrato.

**Parte D (cleanup):**

1. Deletar [`ScoreGaugeChart.tsx`](../../frontend/src/components/report/charts/ScoreGaugeChart.tsx).
2. Remover linha de `_registry.ts:10` e do `MIGRATED_CHART_IDS:21`.

**Critério de aceite:**
- [ ] S1 mostra `ScoreCard` premium com gauge profissional, badge,
      contexto, breakdown, conclusão.
- [ ] PDF idem.
- [ ] Zero `as ScoreData` no codebase (`grep -r "as ScoreData" frontend/src`).
- [ ] Goldens E5 verdes; OpenAPI snapshot commitado.
- [ ] `ScoreGaugeChart.tsx` removido.

---

### v2.E.8 — Re-baseline visual + cleanup + ADR-13X

**Branch:** `agent/report-v2-charts-rebaseline/<ts>`
**Esforço:** S (≤4h)
**Prio:** P0 (não fecha onda sem isso)
**Depende:** **TODAS** as anteriores ✅ em `main`.

**Entrega:**

1. **Re-baseline visual:**
   - Trigger `gh workflow run CI -f run_visual=true -f update_visual_baselines=true`
     (ver `track_report_v2.md` v2.2 para protocolo).
   - Baixar artefato `report-visual-baselines-generated`.
   - Copiar para `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/`.
   - **Esperado:** 4 baselines mudam (cover×2 + S1×2 + S2×2 = 6 PNGs;
     cover não muda na verdade — ajustar contagem). Restantes idênticos.
   - Diff visual revisado item a item antes do commit.
2. **Cleanup imports Recharts:**
   - `grep -rn "from ['\"]recharts" frontend/src/components/report/`
     deve retornar **zero** linhas.
   - `grep -rn "import .* from ['\"]recharts" frontend/src/components/report/charts/`
     deve retornar **zero** linhas.
   - Remover entradas `_registry.ts` de charts deletados.
3. **ADR-13X** em `docs/DECISIONS.md`:
   - Título: "ADR-13X — Finalização migração Recharts→Chart.js em /reports/**"
   - Status: Decidido • Data atual.
   - Contexto: ADR-117 Fase 2 abriu primitives; Fase 7 não fechou; Onda v2.E fechou.
   - Decisão: 5 charts migrados; `ScoreCard` plugado; `PeriodToggle` introduzido;
     slide window 12m em "Receita vs Despesa Mês a Mês"; Recharts removido de
     `/reports/**`.
   - Consequências: paridade visual com EXEMPLO; baselines re-capturadas;
     bundle Recharts pode ser tree-shaken (verificar `bundle-analyzer`).
   - Relaciona-se a: ADR-037, ADR-117, ADR-122.
4. **CHANGELOG.md** entry: `## YYYY-MM-DD — Onda v2.E (charts UX) ✅`
   com 8 sub-lanes ticked.
5. **BACKLOG.md** atualização: marcar v2.E.1-8 ✅, marcar v2.5 ✅
   (absorvida em E.7).

**Critério de aceite:**
- [ ] Workflow CI verde com novos baselines.
- [ ] Zero `recharts` em `/reports/**`.
- [ ] ADR-13X em main.
- [ ] CHANGELOG + BACKLOG sincronizados.

---

## 4. Regras inegociáveis (do CLAUDE.md)

- **Concluído = mergeado em main com CI verde.** Cada sub-lane = PR
  próprio + merge antes da próxima dependente. Sub-lanes paralelas
  podem compartilhar branch base de `main`.
- **Conventional Commits** validado por `dev/validate_commit_msg.py`.
  Citar sub-lane: `feat(report): chart Receita vs Despesa stacked + slide
  window (v2.E.6)`.
- **Pre-commit + suíte localmente antes do push:**
  ```bash
  pre-commit run --all-files
  cd frontend && npm test -- --run
  cd frontend && npm run test:e2e -- --grep @critical  # se tocou seção
  pytest backend/tests -q                              # se tocou backend (E.7 parte C)
  ```
- **Baseline visual não muda em E.3-E.7.** Atualização **apenas** em
  E.8. Lanes E.3-E.7 rodam Playwright local com `--update-snapshots`
  para validar visualmente, mas **não comitam** os PNGs.
- **Hotspots `_shared.ts` e `_registry.ts`:** quando 2+ sub-lanes
  precisarem editar, usar protocolo CLAUDE.md §"Hotspots" (anunciar +
  esperar 2min + edit+commit+push em ≤5min).
- **Dinheiro nunca é float** (ADR-090): Parte C do E.7 toca pipeline;
  manter `Money.brl(...)` ou `Decimal(str(...))`.
- **Stateless rigoroso** (ADR-111): backend de E.7 não introduz cache
  in-memory; templates de `context`/`conclusion` são puros.

---

## 5. Coordenação com outras lanes v2 abertas

| Lane | Estado | Coordenação |
|---|---|---|
| **v2.5** `report-v2-score-dto` (Onda B) | ☐ aberta | **Absorvida em v2.E.7.** No primeiro commit de E.7, marcar v2.5 ✅ no BACKLOG referenciando o branch. Não pegar v2.5 em separado. |
| **v2.4** T2 Aportes (Onda B) | ☐ aberta | Paralela. Toca seções Tático, não S1/S2. Zero overlap. |
| **v2.6** cards/ legacy (Onda B) | ☐ aberta | Paralela. Toca `report/cards/`, não `report/charts/`. Zero overlap. |
| **v2.7** DnD Kanban (Onda C) | ☐ aberta | Paralela. |
| **v2.D.1+v2.8** Snapshot changelog (Onda D) | ☐ aberta | Paralela. Pipeline + render genérico, não toca charts. |
| **v2.9** LLM section_summaries (Onda C) | ☐ aberta (precisa ADR) | Tangencial — **se** mais tarde decidirmos LLM-driven `chart_conclusions`/`chart_contexts`, esta onda E entrega templates simples; v2.9 substitui depois. Não bloqueia. |
| **v2.10** PDF visual diff (Onda C) | ☐ aberta | **Valida** o trabalho. Quando entregue, vai usar baselines re-capturadas em E.8. |
| **v2.2b** Tático+USA baselines (Onda A residual) | ☐ aberta | Disjunto: v2.2b captura T1-T6 + U1-U4; E.8 captura S1+S2. Coordenar timing dos PRs apenas se mergeados na mesma janela. |

---

## 6. O que NÃO entrega

- ❌ Migrar charts fora de `/reports/**` (dashboard, telas internas em
  `frontend/src/components/charts/Mathom*.tsx`) — Recharts permanece
  vivo lá (ADR-037 com escopo restringido).
- ❌ Mudar lib do `WaterfallIfChart`, `PatrimonioDoughnutChart` —
  ficam em Recharts; podem virar lane v2.E.9 separada se
  produto pedir paridade neles também.
- ❌ Novos campos no E5 além de `score.context`/`score.conclusion`.
- ❌ LLM para gerar `chart_context`/`chart_conclusion` (fica para v2.9).
- ❌ Tocar `cards/` (escopo v2.6) ou `Kanban.tsx` (escopo v2.7).
- ❌ Mexer em sections fora de S1/S2 (T*, U*, S3-S10, APP_*).

---

## 7. Pickup protocol

1. `git fetch origin && git for-each-ref --sort=-committerdate --format='%(committerdate:iso) %(refname:short) %(subject)' refs/remotes/origin/agent/ | head -15`
   — confirma que `agent/report-v2-<sub-slug>/*` está livre.
2. `git worktree list` — confirma que ninguém local está na sua sub-lane.
3. `git checkout -b agent/report-v2-<sub-slug>/$(date +%Y%m%d-%H%M)`.
4. Leia este prompt + a seção §3.<sub-lane> específica + os arquivos
   listados na coluna "Toca" da tabela §2.2.
5. Rode os testes locais relevantes para entender o baseline antes de mudar.
6. Implemente em commits atômicos (1 lógica por commit).
7. PR para main, marca a checkbox correspondente em [BACKLOG.md](../BACKLOG.md)
   e referencia esta lane (`v2.E.<n>`) no título do PR.
