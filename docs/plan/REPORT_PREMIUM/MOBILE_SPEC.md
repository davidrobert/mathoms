# Spec mobile do Relatório Premium

> **Escopo:** comportamento do relatório nativo (rota `/reports/[id]`) em
> viewports `<767px`. Decisão de produto convergida em 2026-04-27 como
> resposta a [batch2.13](BACKLOG.md) e à decisão D3 de
> [track_report_a11y_finalize.md](agent_prompts/track_report_a11y_finalize.md).
>
> **Atualização (2026-04-29):** Modo Tático removido do relatório
> ([ADR-151](DECISIONS.md#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces),
> Direção E · Onda 3). Especificações mobile abaixo que mencionam
> T1-T6 são **registro histórico**. Spec mobile efetiva passa a cobrir
> apenas Modos Estratégico + USA.
>
> **Status:** spec only. Implementação fica em lane futura
> `report-mobile-impl` ([BACKLOG.md](BACKLOG.md)).
>
> **Persona:** product-designer + financial-planner. Decisões priorizam
> uso real (cliente Mathoms consultando o último relatório no metrô) e
> não tradução literal do desktop em telas menores.
>
> **Não-escopo:**
>
> - Print/PDF de qualquer dispositivo. Servidor renderiza em viewport
>   1280×1800 (Playwright headless) — PDF gerado em mobile mantém layout
>   desktop, intencionalmente. Justificativa: papel impresso e PDF são
>   leitura fixa de 1 página; spec de fluido em `<767px` quebraria a
>   paridade com `EXEMPLO_DE_RELATORIO.html`.
> - Modo edição. Tático (T1-T6) tem operações de Kanban/Notas que **não**
>   são otimizadas para mobile — ver §1.6 abaixo.
> - Tablet retrato (768-1023). Tratado como "desktop estreito" (sidebar
>   colapsa via `lg:` breakpoint, FloatingNav assume — comportamento
>   atual já é aceitável).

---

## 1. Decisões cross-cutting

### 1.1 Breakpoints

Mantemos a hierarquia Tailwind atual, com **`<767px` como único
breakpoint que ganha tratamento dedicado**:

| Range          | Token Tailwind | Uso                                   |
| -------------- | -------------- | ------------------------------------- |
| `<640px`       | (default)      | Mobile estreito (iPhone SE, Pixel 5). |
| `640-767px`    | `sm:`          | Mobile largo (iPhone Pro Max, foldables fechados). |
| `768-1023px`   | `md:`          | Tablet retrato — comportamento atual. |
| `1024-1279px`  | `lg:`          | Tablet paisagem / laptop pequeno.     |
| `≥1280px`      | `xl:`          | Desktop full — alvo de design.        |

A **fronteira mobile/desktop é `<767px`**, alinhada com a media query
existente em `frontend/src/app/globals.css:178` (Kanban DnD fallback,
v2.7). Tudo `≥768px` herda o desktop atual sem adaptação.

### 1.2 Tipografia

Escala global **87.5%** em `<767px`, aplicada via `data-report-scope`:

```css
@media (max-width: 767px) {
  [data-report-scope] {
    font-size: 14px; /* base 16px × 0.875 */
  }
}
```

Headings ajustam proporcionais (h1 38→28px, h2 24→20px, h3 18→16px).
Valores monetários **mantêm** `tabular-nums` + `font-mono`, mas font-size
reduz para 13-14px.

**Mínimo legível:** 12px. Nada abaixo disso, nem em legendas de chart
nem em footnotes.

### 1.3 Charts — fallbacks agregados

Charts são a maior fonte de overflow horizontal. Padrão de fallback por
tipo:

| Chart                          | Desktop (`≥768px`)                   | Mobile (`<767px`)                                     |
| ------------------------------ | ------------------------------------ | ----------------------------------------------------- |
| Donut/Pie (Recharts/Chart.js)  | Altura 288-320px, todas as fatias    | Altura 220px, top-7 + "outros" agregado se >8 fatias  |
| Bar stacked 12m                | 12 colunas + slide window (já existe)| Slide window default 6 meses                          |
| ReceitaDespesaMensal (groups)  | 12m + tooltip por stack + legenda    | 6m default; legenda chips → lista vertical            |
| Score gauge                    | 220×220 SVG                          | 180×180 SVG; breakdown table → 2 colunas (era 4)      |
| Waterfall IF                   | Largura full, ~12 barras             | Mesma largura, mas labels eixo X rotacionam 45°       |
| Top-N ativos                   | Top 15                               | Top 5 + link "ver completo no PDF"                    |

**Hover/tooltip**: Chart.js + Recharts têm comportamento touch razoável
(`events: ["click"]` mostra tooltip persistente). Não precisa de mudança
estrutural — só validar com Playwright `device.iPhone 13` em lane de
implementação.

### 1.4 Tabelas

Toda tabela com **>3 colunas** vira lista de cards em `<767px`. Padrão
recomendado:

```jsx
{/* Desktop */}
<div className="hidden md:block overflow-x-auto">
  <table>...</table>
</div>
{/* Mobile */}
<ul className="md:hidden grid gap-2">
  {rows.map((r) => (
    <li className="rounded border p-3">
      <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-sm">
        <dt>Categoria</dt><dd>{r.categoria}</dd>
        <dt>Valor</dt><dd className="font-mono tabular-nums">{r.valor}</dd>
      </dl>
    </li>
  ))}
</ul>
```

**Tabelas com ≤3 colunas mantêm formato `<table>`** — uma reserva
honesta. Ex: ScoreCard breakdown (3 cols), EquilibrioCerbasi (2 cols).

### 1.5 Cards de seção

Já estão corretos: `ReportSection` usa `grid gap-6 md:grid-cols-2` —
1 coluna em `<768px`. Nada a fazer.

Cards individuais com grids internos (`grid-cols-2 md:grid-cols-4`) —
revisar caso a caso, ver §3 abaixo.

### 1.6 Modo Tático em mobile

**Decisão:** Tático **fica acessível** mas com aviso visual de uso
otimizado para tablet/desktop. **Razões:**

- T1 Fluxo Operacional, T2 Aportes, T4 Alertas, T5 Próximos Passos,
  T6 Notas são leitura — caem no padrão geral.
- T3 Kanban tem fallback v2.7 já entregue (`globals.css:178`) — botões
  "→ Coluna" substituem DnD em touch.
- Esconder o tablist quebraria deep-links `?mode=tatico` que o usuário
  pode receber por e-mail/Slack.

**O que muda visualmente:**

- Sub-aba "Tático" no `ModeToggle` ganha tooltip "Otimizado para
  tablet/desktop" em hover/focus.
- Banner inline no topo de T3 Kanban: "Em telas pequenas, use os botões
  → Coluna abaixo de cada card".
- Sem mudança no roteamento.

### 1.7 Print/PDF

**Mantém layout desktop em qualquer dispositivo.** Servidor (Playwright
headless) renderiza com viewport `1280×1800`. Documentado em
[backend/app/services/pdf_renderer.py](../backend/app/services/pdf_renderer.py).

**Razão:** PDF é artefato fixo. Geração mobile-first quebraria paridade
visual com a referência `EXEMPLO_DE_RELATORIO.html` e produziria
documento sem charts (fallback agregado vira mentira em PDF). O usuário
mobile que precisa do PDF baixa e abre em qualquer leitor; o conteúdo
não-fluido é desejável.

`@media print` em `frontend/src/app/globals.css:184` continua sem
adaptação mobile-specific.

---

## 2. Auditoria — estado atual em `<767px`

Inspeção estática (sem Playwright headed) sobre os componentes em
`frontend/src/components/report/`. Lista representativa — não exaustiva.

### 2.1 Issues estruturais (layout/scroll)

1. **`ReportCover` com 4 meta-cards em `repeat(4, 1fr)` fixo**
   ([shell/ReportCover.tsx:147](../frontend/src/components/report/shell/ReportCover.tsx)) —
   em 375px de viewport cada card fica com ~75px e o texto quebra ou
   trunca. **Padding `60px 40px`** também é desperdício em mobile.
   Issue **estrutural P0**.
2. **Kanban com `gridTemplateColumns: "1fr 1fr 1fr"` hard-coded**
   ([ui/kanban/Kanban.tsx:238](../frontend/src/components/report/ui/kanban/Kanban.tsx)) —
   3 colunas sempre, em qualquer viewport. v2.7 só adicionou botões
   alternativos; o tabuleiro continua 3 colunas. Issue **estrutural P0**
   (já parcialmente mitigado).
3. **Tabelas com `overflow-x-auto`** (PatrimonioCategoriasCard,
   EstrategiaAporteCard, ContrafluxoCard, InvestimentosClasseCard,
   ReceitasFonteCard, OrcamentoProspectivoCard, EndividamentoCard,
   DiagnosticoComportamentalCard) — não quebram layout, mas forçam
   swipe horizontal cego ("a coluna 5 existe?"). Issue **estrutural P1**.

### 2.2 Issues estéticos (tipografia/espaçamento)

4. **Cover h1 em 38px (`--report-font-size-3xl`)** — em 375px ocupa 2
   linhas e empurra meta-cards para baixo do fold. Sumário executivo
   "primeira impressão" se perde. Issue **estético P1**.
5. **Charts com altura fixa 288-320px e `width: 100%`** — em 375px
   ficam quadrados (288×~315), tomam 1/3 da viewport. Várias seções
   (S1, S2, S3) empilham 3-4 charts seguidos = scroll de 1500px só de
   chart. Issue **estético P1**.
6. **Padding lateral do `<article>`: `px-10` (40px)** —
   ([ReportShell.tsx:373](../frontend/src/components/report/ReportShell.tsx))
   em 375px sobra 295px de conteúdo útil. `px-4` (16px) seria mais
   honesto em mobile. Issue **estético P2**.

### 2.3 Issues de informação (densidade)

7. **HeroKpiGrid 6 KPIs em `grid-cols-1 sm:grid-cols-2 xl:grid-cols-3`**
   ([kpi/HeroKpiGrid.tsx:36](../frontend/src/components/report/kpi/HeroKpiGrid.tsx)) —
   já é 1 coluna em `<640px`, **mas** 6 cards em coluna = scroll de
   ~1200px só para ver os KPIs. Sumário executivo deixa de ser sumário.
   Issue **informação P0**.
8. **Top-15 ativos em S3** — em mobile, lista com 15 entradas é ruído.
   Top-5 entrega 80% do valor (lei de Pareto aplicada à carteira).
   Issue **informação P1**.
9. **Donut com 12 fatias** (ex.: composição patrimonial em famílias com
   ativos diversos) — em 220px de altura mobile, fatias <3% viram
   slivers ilegíveis. Issue **informação P1**.

### 2.4 Surpresas positivas

- **`ReportSection` já usa `md:grid-cols-2`** — 1 col em mobile correto.
- **`HeroKpiGrid` já usa `sm:grid-cols-2`** — 2 cols mobile correto, só
  precisa reduzir font.
- **`FloatingNav` já tem detecção `(max-width: 1023px)`** — drawer mobile
  do TOC já funciona.
- **Cards `EndividamentoCard`, `ReservaEmergenciaCard`, etc.** usam
  `grid-cols-2 md:grid-cols-4` — degradação aceitável.
- **Kanban tem botões "→ Coluna"** — fallback DnD parcial entregue
  em v2.7.

---

## 3. Especificação por seção

### 3.1 Tabela de comportamento

| Seção / Componente               | Comportamento `<767px`                                                                       | Justificativa                                                                                                       |
| -------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Cover (`ReportCover`)**        | Padding `24px 16px` (era 60×40); h1 28px; meta-cards `repeat(2, 1fr)` (2 col); badge mantém. | Cover é primeira impressão; precisa caber em viewport sem ≥1 scroll para ver `Família + Período + Versão`.         |
| **ExecutiveSummarySection (Hero KPI 6)** | Mantém `sm:grid-cols-2` atual (2 col). Valor em 16px (era 22px); sub-label 11px.    | KPIs são âncora; user precisa varrer 6 sem scroll de 6×. 2 cols × 3 linhas cabem em 1 viewport iPhone 13.           |
| **PerfilFamiliaCard**            | 1 col (já tem `md:grid-cols-2`); avatar/iniciais reduzem 56→40px.                            | Perfil é contextual; densidade pode reduzir.                                                                        |
| **S1 — Patrimônio Estrutura**    | Charts 220px altura (era 288); `PatrimonioCategoriasCard` tabela vira lista de cards; `SectionSnapshotDiff` colapsa em accordion fechado por padrão. | Composição em mobile é leitura rápida; detalhe (changelog vs anterior) vai pra accordion.                          |
| **S2 — Fluxo de Caixa**          | `ReceitaDespesaMensalChart` slide window default 6m (era 12m); legenda agrupada vira lista vertical; `ReceitasFonteCard` tabela vira cards. | Touch tooltip OK em 6 colunas; 12 não dá hover precise. Legenda em 8 chips quebra em 4 linhas.                     |
| **S3 — Investimentos**           | Top-15 ativos → top-5 + nota "ver lista completa em S3 do PDF"; tabela alocação alvo vira cards (1 por classe); `EstrategiaAporteCard` tabela vira cards. | Top 15 em coluna é ruído; top 5 entrega ranking essencial.                                                          |
| **S4 — Real Estate**             | 1 col padrão; tabela imóveis vira cards (1 imóvel = 1 card).                                 | Sem complicação; tabela com 4-5 cols era prejudicada.                                                               |
| **S7 — Independência Financeira**| `WaterfallIfChart` mantém width full mas labels eixo X rotacionam 45°; cards de cenários (otimista/realista/pessimista) empilham 1 col. | Eixo X com 12 anos não cabe horizontal em 343px sem rotação.                                                        |
| **S8 — Previdência**             | `PrevidenciaPgblCard` `dl grid-cols-2 md:grid-cols-3` → mantém 2 col; tabelas viram cards.   | 2 col cabe em 375px (~150px cada).                                                                                  |
| **S9 — Riscos**                  | 1 col; `DiagnosticoComportamentalCard` tabela vira cards.                                    | Sem complicação.                                                                                                    |
| **S10 — Síntese**                | 1 col; gauge score 180×180 (era 220); breakdown table 2 cols (era 4).                        | Score é o último gancho — precisa caber sem scroll dentro do card.                                                  |
| **PlanoDeAcao**                  | 1 col; cards de decisão (P0/P1/P2) empilham; ações inline mantêm.                            | Lista é o formato natural; sem compressão necessária.                                                               |
| **T1 — Fluxo Operacional**       | Cards 2 cols (era `lg:grid-cols-4`) — mantém comparação visual.                              | Fluxo operacional é leitura crítica; 2 cols = pares contrastam (receita×despesa, etc.).                             |
| **T2 — Aportes**                 | Cards 1 col; tabela mensal de aportes vira cards.                                            | Lista é o uso natural ("o que aportei este mês?").                                                                  |
| **T3 — Tarefas (Kanban)**        | **Tabuleiro vira lista vertical agrupada por coluna** (a fazer / em andamento / concluído); cada item card-style; botões "→ Coluna" mantêm para mover. Banner topo "Em telas pequenas use os botões". | DnD em touch é frágil (long-press conflita com scroll); 3 colunas em 375px = ~110px cada, só ícones cabem.          |
| **T4 — Alertas**                 | 1 col padrão.                                                                                | Alerta é leitura.                                                                                                   |
| **T5 — Próximos Passos**         | 1 col padrão.                                                                                | —                                                                                                                   |
| **T6 — Notas**                   | 1 col; toolbar de markdown mantém em scroll horizontal próprio.                              | Notas são leitura/edição leve; toolbar swipeable é aceitável.                                                       |
| **U1-U4 — USA**                  | 1 col padrão; tabelas de custos viram cards.                                                 | Sem complicação especial.                                                                                           |
| **APP_A-E (Apêndices)**          | **Visíveis mas em accordion fechado por padrão.** Header clicável; primeira interação expande. | Apêndice é detalhe; usuário só consulta se precisar (`<details>` HTML semântico).                                  |
| **ReportTopNav**                 | Já correto: tablist condensa, links secundários vão para FloatingNav drawer (`<lg`).         | Comportamento atual aceitável; só validar tap targets ≥44×44px.                                                     |
| **FloatingNav (TOC drawer)**     | Já correto: `(max-width: 1023px)` ativa drawer.                                              | Funciona.                                                                                                           |
| **ExportToolbar**                | Sticky bottom; 2 botões (PDF / link) mantêm. Botão "Imprimir" oculto (`@media print` desabilita; user mobile dificilmente imprime). | Reduzir clutter.                                                                                                    |
| **ReportSourceStrip (rodapé)**   | Padding reduzido `12px 16px`; metadados quebram em coluna.                                   | Strip é informacional, não bloqueia.                                                                                |

### 3.2 Componentes não-críticos

Componentes herdam comportamento padrão (sem override mobile):

- `ReportCard`, `MonetaryValue`, `ScoreCard` (mantém renderização)
- `Timeline`, `NotasCard`, `Kanban` columns interno
- `SectionSummary` (texto fluido)
- `ReportPremissasBlock`

---

## 4. Priorização para implementação futura

### 4.1 P0 — bloqueia uso em mobile

| #   | Item                                    | Componente                                    | Esforço |
| --- | --------------------------------------- | --------------------------------------------- | ------- |
| P0.1 | Cover responsivo (padding + h1 + meta cols 4→2) | `shell/ReportCover.tsx` — substituir inline styles por className+breakpoint Tailwind | 2h |
| P0.2 | Kanban vira lista vertical agrupada em `<767px` (estende v2.7) | `ui/kanban/Kanban.tsx` — extrair `<KanbanList>` mobile sibling, swap por media query JS (`useMediaQuery` hook) ou container query | 3h |
| P0.3 | Tabelas com >3 cols viram lista de cards (8 cards afetados) | `cards/Patrimonio*`, `cards/Estrategia*`, `cards/Receitas*`, `cards/Contrafluxo*`, `cards/Investimentos*`, `cards/Orcamento*`, `cards/Endividamento*`, `cards/Diagnostico*` | 6h (45min × 8) |
| P0.4 | HeroKpiGrid font scale (16→14 base, 22→16 valor) em mobile | `kpi/HeroKpiGrid.tsx` — adicionar `text-sm sm:text-base` em wrapper, `text-base sm:text-2xl` no valor | 1h |

**Total P0:** ~12h.

### 4.2 P1 — degrada experiência

| #   | Item                                                                                | Componente                                  | Esforço |
| --- | ----------------------------------------------------------------------------------- | ------------------------------------------- | ------- |
| P1.1 | Tipografia base 87.5% global em `<767px` via `data-report-scope`                   | `frontend/src/app/globals.css` ou `tokens.css` | 0.5h |
| P1.2 | `ReportShell` `<article>` padding `px-4 md:px-10` (era `px-10` fixo)                | `ReportShell.tsx:373`                       | 0.5h |
| P1.3 | Charts altura responsiva (288→220 em mobile)                                        | `charts/_shared.ts` — função `useChartHeight(default)` que retorna height por viewport, ou CSS-only via `aspect-ratio` | 3h |
| P1.4 | Slide window default 6m em `<767px` para `FluxoMensalChart` + `ReceitaDespesaMensal`+`ReceitaBarChart` | 3 charts — passar `defaultWindow` via prop, default por media query | 2h |
| P1.5 | Donut top-N agregação ("outros") quando >8 fatias em mobile                         | `charts/PatrimonioDoughnutChart.tsx`, `charts/DespesasDoughnutChart.tsx` | 2h |
| P1.6 | Top-N ativos: limitar a 5 em mobile, link "ver completo no PDF"                     | `charts/NarrativeChartCard.tsx` consumidor (S3) | 1h |
| P1.7 | RDMLegend chips → lista vertical em mobile                                          | `charts/RDMLegend.tsx`                       | 1h |
| P1.8 | Banner topo T3 Kanban "Em telas pequenas use botões → Coluna"                       | `sections/TaticoSections.tsx` — `T3TarefasSection` | 0.5h |
| P1.9 | Tooltip Tático "Otimizado para tablet/desktop" no `ModeToggle`                      | `shell/ModeToggle.tsx` ou `ReportActions.tsx` | 0.5h |

**Total P1:** ~11h.

### 4.3 P2 — nice-to-have

| #   | Item                                                                          | Componente                                       | Esforço |
| --- | ----------------------------------------------------------------------------- | ------------------------------------------------ | ------- |
| P2.1 | Apêndices APP_A-E em `<details>` colapsado por padrão em mobile               | `sections/ApendicesSections.tsx` + `ApendiceASection.tsx` | 1.5h |
| P2.2 | `SectionSnapshotDiff` colapsado por padrão em mobile                          | `SectionSnapshotDiff.tsx`                         | 0.5h |
| P2.3 | `WaterfallIfChart` rotação 45° eixo X em mobile                               | `charts/WaterfallIfChart.tsx`                     | 0.5h |
| P2.4 | ScoreCard gauge 220→180 em mobile + breakdown 4→2 cols                        | `ui/ScoreCard.tsx`                                | 1h |
| P2.5 | ExportToolbar oculta botão "Imprimir" em mobile                               | `shell/ExportToolbar.tsx`                         | 0.25h |
| P2.6 | ReportSourceStrip rodapé padding reduzido + stack vertical                    | `ReportSourceStrip.tsx`                           | 0.25h |
| P2.7 | Validação tap targets ≥44×44px em ReportTopNav, FloatingNav, ExportToolbar   | Auditoria + ajustes                               | 1.5h |
| P2.8 | Spec Playwright `device.iPhone 13` para 4 fluxos críticos (cover→S1→T3→PDF)   | `frontend/tests/e2e/reports/mobile.@critical.spec.ts` (novo) | 4h |
| P2.9 | Snapshots visuais mobile (24 sections × {light, dark} = 48 PNGs)              | extends `sections.snapshots.visual.spec.ts` com viewport mobile | 2h + CI run |

**Total P2:** ~11h + CI run.

### 4.4 Total estimado

- **P0+P1+P2:** ~34h ≈ 2-5 dias de trabalho ativo (1 agente).
- **Pickup sugerido:** P0 + P1 em uma onda (~23h, lane única). P2 em
  follow-ups oportunísticos.

---

## 5. Ordem de implementação sugerida (lane `report-mobile-impl`)

1. **Slice 1 — fundação** (P1.1 + P1.2 + P0.4): tokens + globals + scale.
   ~2h. Validação visual leve.
2. **Slice 2 — cover + nav** (P0.1 + P1.9 + P2.5): primeira impressão.
   ~3h.
3. **Slice 3 — charts** (P1.3 + P1.4 + P1.5 + P1.6 + P1.7 + P2.3 + P2.4):
   maior fonte de overflow. ~10h. Pode ser sub-paralelizado por chart.
4. **Slice 4 — tabelas → cards** (P0.3): mecânico, repetitivo.
   ~6h. **Pode ser paralelizado** por card (8 agentes em worktrees).
5. **Slice 5 — Tático Kanban** (P0.2 + P1.8): lista vertical agrupada
   estende v2.7 sem regressão. ~3.5h.
6. **Slice 6 — apêndices + acessórios** (P2.1 + P2.2 + P2.6 + P2.7):
   acabamento. ~3h.
7. **Slice 7 — testes mobile** (P2.8 + P2.9): gate empírico.
   ~6h + CI run.

Cada slice termina com `pre-commit run --all-files` + `pytest backend`
(se tocar fixtures) + `cd frontend && npm test -- --run`.

---

## 6. Aceitação

A lane `report-mobile-impl` pode dar como concluída quando:

1. Todos os P0 entregues em `main`.
2. Todos os P1 entregues em `main`.
3. Spec Playwright `mobile.@critical.spec.ts` passa em CI (P2.8).
4. Snapshots visuais mobile commitados (P2.9) — 48 PNGs em
   `frontend/tests/e2e/reports/__screenshots__/`.
5. Validação humana smoke em iPhone real ou Chrome DevTools com device
   emulation: cover→S1→S2→T3→Apêndice→PDF.
6. **Não-aceito como sucesso:** "funciona em DevTools 375px" sem
   validação em device real ou snapshot CI.

---

## 7. Referências

- Decisão fonte: D3 em [agent_prompts/track_report_a11y_finalize.md](agent_prompts/track_report_a11y_finalize.md)
- Backlog item: [batch2.13](BACKLOG.md)
- Renderer único pós ADR-129: [DECISIONS.md ADR-129](DECISIONS.md)
- Plano-mãe: [plan/REPORT_PREMIUM/_README.md §17.10](plan/REPORT_PREMIUM/_README.md)
- Fallback Kanban v2.7 (base): `frontend/src/app/globals.css:178`
- A11y checklist: [REPORT_A11Y_CHECKLIST.md](REPORT_A11Y_CHECKLIST.md)
