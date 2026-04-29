# Report Premium — Phase 0 Gap Inventory

> **Fonte:** execução da Fase 0 do [docs/REPORT_PREMIUM_PLAN.md](REPORT_PREMIUM_PLAN.md).
> **Produzido por:** agente dedicado (Opus 4.7 1M, worktree isolado, ~1h30 de discovery).
> **Data:** 2026-04-23.
> **Status:** ✅ RESOLVIDO — 13 Open Questions respondidas pelo usuário em 2026-04-23;
> decisões formalizadas em ADR-117, 121, 122, 123, ~~124~~. Fase 1 unlocked.
> Deltas aplicados ao plano — ver [REPORT_PREMIUM_PLAN.md §Deltas](REPORT_PREMIUM_PLAN.md).
>
> ⚠️ **Update 2026-04-29 (Direção E · Onda 3):** Modo Tático removido
> do relatório ([ADR-151](DECISIONS.md#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces)).
> Itens neste documento que mencionam `tatico.*`, T1-T6, KanbanItem,
> ReportNotes são **registro histórico**. Decisões originais (ADR-117/123)
> permanecem válidas para Modos Estratégico + USA.
>
> ⚠️ **Update 2026-04-24:** [ADR-124](DECISIONS.md#adr-124--scriptse6_renderpy-aposentado-em-favor-de-ssr-standalone-do-next) (e Q12 abaixo)
> foi superseded por [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).
> O renderer HTML server-side foi **descontinuado por completo** —
> `scripts/e6_render.py`, `scripts/e6/`, `pipeline/stages/e6.py` e
> endpoints HTML foram removidos (lane `adr-129-e6-kill`). Observations
> #2 (CSS standalone), #9 (4867 linhas Jinja2), Q9/Q12 e qualquer
> referência a "exportador standalone" neste documento ficam como
> **registro histórico** — não são mais ações pendentes.

---

## Executive summary

Comparei `EXEMPLO_DE_RELATORIO.html` (10 024 linhas, Chart.js + dark mode + kanban + score interativo, auto-contido) contra `/reports/[id]` atual (shell React migrado, sem capa, sem nav sticky, sem Chart.js, sem dark mode, sem kanban).

**Contagens:** Tabela A — 23 tokens CSS novos + reconciliar 4 divergências (base 13px vs 16px, `color-bg`, `color-text`, `color-row-hover`) + emitir ~30 aliases `--color-*` sobre tokens existentes. Tabela B — 32 primitivos mapeados: 6 existem (`PeriodToggle`, `ReportCard`, `SectionSummary`, `MonetaryValue`, `PontosFortesList`, `ReportSection`), 5 parciais, **21 novos**. Tabela C — 14 campos ausentes; **descoberta importante:** `financial_score_calculator`, `pontos_fortes_analyzer`, `if_projector`, `ratios_calculator` **já existem** em `pipeline/domain/services/`, Fase 6 é menor que o plano estimou. Tabela D — 11 atributos por-item novos no YAML + slots `cover:`/`navigation:` ausentes + APP_B/C/D/E têm só `id+title`.

**Maior risco:** `chart_conclusions` e `section_summaries` via LLM introduz primeira dependência Anthropic em E5 (hoje só E0/E1 chamam LLM). Requer cache Redis, prompt templates, ADR de determinismo parcial.

**Campos que provavelmente precisam de LLM:** `chart_conclusions[chart_id]`, `section_summaries[section_id]`, opcionalmente enriquecimento de `pontos_fortes[].descricao`. Todo resto é determinístico.

---

## 1. Tabela A — Gaps de token CSS

| # | Token (:root exemplar) | Status em `tokens.json` | Ação Fase 1 |
|---|---|---|---|
| 1 | `--color-primary` `#1A3A5C` | existe (`brand.primary`) | alias |
| 2 | `--color-secondary` `#1E6E8F` | existe (`brand.info`) | alias |
| 3 | `--color-accent` `#15803D` | existe (`brand.accent`) | alias |
| 4 | `--color-accent-bg` `#2DC653` | ausente | adicionar |
| 5 | `--color-danger` `#B91C1C` | existe | alias |
| 6 | `--color-warning` `#F4A261` | existe | alias |
| 7 | `--color-warning-text` `#B45309` | ausente | adicionar |
| 8 | `--color-neutral` `#457B9D` | existe | alias |
| 9 | `--color-light` `#A8DADC` | ausente (dark tem `#1E3A5F`) | adicionar light + alias dark |
| 10 | `--color-bg` `#F8FAFC` | divergência (light `surface.background`=`#FFFFFF`) | reconciliar |
| 11 | `--color-surface` `#FFFFFF` | existe | alias |
| 12 | `--color-text` `#1E293B` | divergência (`#0F172A`) | reconciliar |
| 13 | `--color-text-muted` `#64748B` | existe | alias |
| 14 | `--color-border` `#E2E8F0` | existe | alias |
| 15 | `--color-row-even` `#F8FAFC` | existe | alias |
| 16 | `--color-row-hover` `#EEF5FF` | divergência 1 byte (`#EFF6FF`) | reconciliar |
| 17 | `--color-row-total` `#EDF2F7` | ausente | adicionar |
| 18 | `--color-summary-bg` `#EFF6FF` | ausente (semântico) | adicionar |
| 19 | `--color-conclusion-bg` `#F8FAFC` | ausente (semântico) | adicionar |
| 20 | `--color-compare-neg` `#FEF2F2` | ausente | adicionar |
| 21 | `--color-compare-pos` `#F0FDF4` | ausente | adicionar |
| 22 | `--alert-{danger/warning/success/info}-{bg/text}` × light/dark | ausente (16 tokens) | adicionar 16 |
| 23 | `--font-display` / `--font-body` | existe (`typography.fonts.*`) | alias em `:root` |
| 24 | `--font-xs`..`--font-3xl` (8 níveis, px) | escalas divergem — exemplar 10/12/13/14/16/22/28/38px; token rem com base 16px | **decidir** (Open Q #5) |
| 25 | `--space-xs`..`--space-4xl` | existe (rem) | alias |
| 26 | `--space-card-sm/-md/-lg` (legacy) | ausente | adicionar aliases |
| 27 | `--space-section-gap` `20px` | ausente | adicionar |
| 28 | `--radius-badge` `10px` | ausente (tem `pill` e `card`) | adicionar |
| 29 | `--shadow-card` / `--shadow-card-hover` | existe | alias |
| 30 | `--badge-{green/red/yellow/blue/neutral}-{bg/text}` × 2 modos | ausente (10 tokens) | adicionar 10 |
| 31 | `--table-{even/hover/total/header}-bg` (dark) | ausente | adicionar 4 |
| 32 | `--card-feature-bg` gradient (dark) | ausente | adicionar |
| 33 | `--card-success-bg` gradient (dark) | ausente | adicionar |
| 34 | `--roadmap-bg` (dark) | ausente | adicionar |
| 35 | Cover gradient (`#0F2A44→#2E5D85`) | hardcoded no exemplar | tokenizar (`--cover-gradient`) ou inline no `ReportCover` |
| 36 | Subtítulo gradient (`A8DADC→4ADE80`) | hardcoded | idem |

**Total Fase 1:** ~35 tokens novos/aliases + reconciliar 4 divergências.

---

## 2. Tabela B — Gaps de primitivo UI

Legenda: **E** = existe; **P** = parcial; **F** = faltando.

| # | Componente | Status | Caminho proposto | Obs |
|---|---|---|---|---|
| 1 | `ReportCover` | F | `components/report/shell/ReportCover.tsx` | Hero + gradient + meta grid 4 cards |
| 2 | `ReportTopNav` | F | `.../shell/ReportTopNav.tsx` | Sticky, 3 grupos mode, IntersectionObserver |
| 3 | `ModeToggle` | F | `.../shell/ModeToggle.tsx` | Integra `ReportModeProvider` existente |
| 4 | `ThemeToggle` | F | `.../shell/ThemeToggle.tsx` | `data-theme` + localStorage |
| 5 | `SkipNav` | F | `.../shell/SkipNav.tsx` | A11y |
| 6 | `BackToTop`/`GoToBottom` | F | `.../shell/FloatingNav.tsx` | Debounce 100ms |
| 7 | `ExportToolbar` | F | `.../shell/ExportToolbar.tsx` | HTML/PDF/Copy |
| 8 | `Card` (variants) | P | `ReportCard.tsx` existe | Expandir para 11 variants |
| 9 | `CardTitle`/`CardSubtitle` | F | `.../ui/Card.tsx` | Extrair |
| 10 | `Alert` | F | `.../ui/Alert.tsx` | 4 severities × 2 modos |
| 11 | `Badge` | F | `.../ui/Badge.tsx` | 5 colors |
| 12 | `IconBadge` | F | `.../ui/IconBadge.tsx` | 24×24, 1-2 chars |
| 13 | `SectionDivider` | F | `.../ui/SectionDivider.tsx` | `::before/::after` gradient |
| 14 | `KpiCard`/`KpiGrid`/`KpiHero` | P | `PatrimonioKpiRow.tsx` isolado | Extrair primitivo |
| 15 | `KpiStrip` | F | `.../ui/KpiStrip.tsx` | 5 slots (`.proj-kpi-strip`) |
| 16 | `ScoreCard`+`ScoreBreakdownTable` | P | `scoreUtils.ts` + `ScoreGaugeChart.tsx` existem | Card composto faltando |
| 17 | `PontoForteItem` | P | `PontosFortesList.tsx` é lista+card combinados | Separar primitivo |
| 18 | `CollapsibleSectionHeader` | F | `.../ui/CollapsibleSectionHeader.tsx` | Chevron 28×28 |
| 19 | `SectionSummary` | E | existe | Auditar estilo vs exemplar |
| 20 | `TwoColCards`/`SplitCards` | F | `.../ui/SplitCards.tsx` | Min-height equalizado |
| 21 | `ComparisonBlock` | F | `.../ui/Comparison.tsx` | Before/after |
| 22 | `PriorityBadge`/`DeadlineBadge`/`EffortBadge` | F | `.../ui/badges/*.tsx` | Computam status de ISO |
| 23 | `ChartCanvas`+`ChartRegistry` | F | `.../charts/ChartCanvas.tsx` + `ChartRegistry.ts` | Dynamic SSR-off + theme hook |
| 24 | `ChartBar/StackedBar/Donut/Pie/Line/Combo/Waterfall/GaugeSemi/Bubble` | P | 7 charts existem em **Recharts/custom**, não Chart.js | Open Q #4 — reescrever ou coexistir |
| 25 | `ChartConclusion` | F | `.../charts/ChartConclusion.tsx` | Lê `chart_conclusions[id]` |
| 26 | `ChartNav` (dots+setas) | F | `.../charts/ChartNav.tsx` | Usado só em `chart-receita-despesa-mensal` |
| 27 | `PeriodToggle` | P | existe | Auditar API vs `data-period=3/6/12/ytd` |
| 28 | `Kanban`/`KanbanColumn`/`KanbanCard` | F | `.../ui/kanban/*.tsx` | `@dnd-kit/core` + localStorage |
| 29 | `Timeline` (T5) | F | `.../ui/Timeline.tsx` | `{data, ação, badge}` |
| 30 | `ChangelogList` | F | `.../ui/ChangelogList.tsx` | Border-left colorida + `.ciclo-badge` |
| 31 | `NotasCard` (T6) | F | `.../ui/NotasCard.tsx` | Textarea autosave 500ms + 3 botões (Open Q #1) |
| 32 | `NotasInsightsGrid` | F | `.../ui/NotasInsightsGrid.tsx` | 3 cards (score/cerbasi/período) com barras |

**Total:** 32 mapeados; 6 existem; 5 parciais; 21 novos.

---

## 3. Tabela C — Gaps de dado no `ReportAnalysisData`

Legenda origem: `E5-det` = regra determinística em service existente; `E5-new` = novo service; `LLM` = Anthropic; `client` = localStorage; `derive-TS` = no frontend. Esforço: **S** ≤4h, **R** 4-12h, **O** >12h.

| # | Campo | Hoje? | Origem | Esforço | Bloqueia |
|---|---|---|---|---|---|
| 1 | `score.valor` 0-10 | existe (`financial_score_calculator.py`) | — | — | — |
| 2 | `score.classificacao` (Excelente..Crítico) | existe | — | — | — |
| 3 | `score.componentes[]` | existe | — | — | — |
| 4 | `score.formula` (string) | ausente | E5-det | S | `ScoreCard` footer |
| 5 | `meta_if.progresso_pct` | parcial | E5-det (`if_projector.py`) | S | KpiHero Meta IF, proj-kpi-strip |
| 6 | `meta_if.gap_mensal` | ausente | E5-det | S | proj-kpi-strip |
| 7 | `meta_if.ano_alvo` (absoluto, não `prazo_anos`) | parcial | E5-det | S | `proj-kpi-year` |
| 8 | `projecao.kpi_strip[]` (5 slots) | ausente (dados espalhados) | E5-det agregador | S | S7 KpiStrip |
| 9 | `chart_conclusions[chart_id] -> str` | ausente | **LLM** ou template — Open Q #2 | R (LLM) / S (template) | `ChartConclusion` em 21 charts |
| 10 | `section_summaries[section_id] -> str` | parcial (hardcoded por seção hoje) | **LLM** ou template | R / S | `<SectionSummary>` em 9 seções |
| 11 | `pontos_fortes[].descricao` expandida | parcial (já existe, formato regra) | E5-det template ou LLM | S / R | S10 PontosFortesList |
| 12 | `cerbasi.presente_vs_futuro` (4 barras) | parcial (tem pct, falta `meta_futuro_pct_ideal` e barras plotáveis) | E5-det | S | NotasInsightsGrid, S10 |
| 13 | `tatico.kanban.itens[]` `{id, titulo, prioridade, prazo_iso, coluna, categoria, essencial}` | parcial (tem `tarefas + tarefas_status`) | E5-det ou derive-TS | S | T3 Kanban |
| 14 | `tatico.timeline[]` `{data_iso, acao, status}` | parcial (`proximos_15d`) | E5-det normalizer | S | T5 Timeline |
| 15 | `tatico.changelog[]` (diff t-1 vs t) | ausente | E5-new (`SnapshotChangelogBuilder` novo — requer acesso a `ArtifactStore` do snapshot anterior) | O | T0/T3 ChangelogList |
| 16 | `tatico.alertas[]` normalizado | parcial | E5-det | S | T4 |
| 17 | `capa.meta[]` 4× `{label, value}` | ausente como estrutura | derive-TS (compor no `ReportCover` de props existentes) | S | `ReportCover` |
| 18 | `comparisons[]` (before/after por card) | ausente | E5-new (mesmo service do #15) | O | Comparison em S1/S2/S3 (opcional — `enabled: false`) |
| 19 | `priority_badges.level` em S10/APP_E | parcial (`essencial: S/R/O`) | derive-TS (S→alta, R→media, O→baixa) | S | S10 tabela + APP_E |
| 20 | Decisão font-scale 13px vs 16px | — | humano (ADR) | — | Fase 1 inteira |

**Resumo:** bloqueios Fase 1-5 são todos determinísticos e curtos (S). Bloqueios Fase 6 reais: #9, #10 (dependem de decisão LLM), #15, #18 (requerem snapshot-diff — recomendo diferir).

---

## 4. Tabela D — Gaps no `report_layout.yaml`

### 4.1 Slots raiz ausentes

| # | Item | Ação |
|---|---|---|
| 1 | `cover:` (bloco raiz — hero, badge, meta 4 cards) | Adicionar chave com `{badge, title, subtitle, meta: [{label_key, value_key}]*4}` |
| 2 | `navigation:` (grupos + labels) | Adicionar `navigation.groups[].{label, section_ids[]}` |
| 3 | `footer:`/`export_toolbar:` flags | Booleanos no topo |

### 4.2 Atributos novos por section

| # | Atributo | Default | Propósito |
|---|---|---|---|
| 4 | `summary: bool` | `true` estratégico/USA | Renderiza `<SectionSummary>` |
| 5 | `divider_before: bool` | `false` primeira, `true` demais | `<SectionDivider>` |
| 6 | `collapsible: bool` | `false` strategic, `true` tactical | `<CollapsibleSectionHeader>` |

### 4.3 Atributos novos por chart

| # | Atributo | Default | Propósito |
|---|---|---|---|
| 7 | `conclusion: bool` | `true` | `<ChartConclusion>` |
| 8 | `context: bool` | `true` | `<p class="chart-context">` |
| 9 | `period_toggle: bool` | varia | `<PeriodToggle>` em `fluxo_mensal/receita_bar/despesas_doughnut/receita_despesa_mensal/impostos_pj` |
| 10 | `row: string` | já existe | Agrupa 2 charts |
| 11 | `height: number\|"auto"` | `"auto"` | Override default |

### 4.4 Atributos novos por card

| # | Atributo | Default | Propósito |
|---|---|---|---|
| 12 | `top_border: "danger"\|"accent"\|null` | `null` | `card-top-danger/accent` |
| 13 | `comparison_anchor_id: string\|null` | `null` | Puxa `comparisons[anchor_id]` |

### 4.5 Items ausentes no YAML

| # | Item | Ação |
|---|---|---|
| 14 | `S3.viagens` chart no `sections[id=S3].charts[]` (existe em `chart_canvas_map` mas não na lista) | Adicionar com `enabled: false` |
| 15 | APP_B/C/D/E sem `cards[]`/`charts[]` — só `id+title+enabled` | Expandir com cards (APP_B tem `{premissas_economicas, metodologias, fontes_dados, disclaimers}` no exemplar) — 10+ IDs novos |
| 16 | `tatico.sections` tem só `data_source: string`, sem `cards[]`/`charts[]` | Unificar schema (ver Observation #1) |
| 17 | `tatico.kpis[id=aportes_check]` sem sub-campos `destinos[]` | Estender spec |

---

## 5. Observations (out-of-scope, não consertados)

1. YAML tático tem schema divergente (só `data_source`) vs estratégico/USA (`cards[]`/`charts[]`). Unificar na Fase 5.
2. `design-tokens/build.py` **não emite CSS standalone** para `e6_render.py` — hoje as 2 fontes de CSS podem drift. Bug em potencial. Registrar como Phase 1 §3.1.2.
3. `S8` no YAML se chama "Previdência — PGBL e Fiscalidade"; exemplar e plano chamam "Tributário". Nomenclatura divergente.
4. `mariana_cenarios` e `mariana_cenarios_usa` = dois canvas IDs para o mesmo dado (S3 e U4). State drift potencial.
5. **Bug silencioso:** `MIGRATED_SECTIONS` em `ReportShell.tsx` só lista `APP_A`; APP_B/C/D/E estão `enabled: true` no YAML mas nunca renderizam (switch não tem case). Registrar para Fase 10.
6. `PatrimonioKpiRow.tsx` isolado em `components/report/kpi/` — pronto para virar primitivo `KpiGrid`+`KpiCard`.
7. 7 charts existentes usam Recharts/custom. Plano manda Chart.js. Open Q #4.
8. `dev/codegen_report_layout.py` precisa ser estendido antes da Fase 5 para refletir atributos novos em D.2-D.4.
9. `e6_render.py` tem 4867 linhas procedurais — Fase 11 Jinja2.
10. `NotasCard` + `Kanban` em localStorage são ok vs ADR-111 Stateless (client-only). Se futuramente persistir, tem que ir Redis via endpoint.
11. **Nenhuma LLM call em E5 hoje.** Adicionar (#9, #10 Tabela C) requer: Anthropic key no worker, cache Redis por snapshot hash, prompts em `config/prompts/`, fake por hash nos testes, ADR de determinismo parcial.
12. Font scale mismatch: exemplar 13px base, tokens 16px base. Open Q #5.
13. Worktree em branch `worktree-agent-a7aabded` (nome fora da convenção `claude/*`/`agent/*`). Não crítico.

---

## 6. Issues encontrados durante discovery (podem atrasar o plano)

1. **Services E5 subestimados como "novos" pelo plano.** `financial_score_calculator.py`, `pontos_fortes_analyzer.py`, `if_projector.py`, `ratios_calculator.py` **já existem** em `pipeline/domain/services/`. A Fase 6 é 30-40% menor que o plano estimou — apenas extensões a services existentes para a maioria dos campos. Exceções: `SnapshotChangelogBuilder` (#15, #18) é genuinamente novo.
2. **Bug silencioso em APP_B/C/D/E** (Observation #5) — `enabled: true` mas não renderiza. Afeta qualquer smoke test que compare a lista do YAML com o rendered output; Fase 10 precisa lidar com a discrepância retroativa.
3. **Dois sistemas de CSS paralelos** (Observation #2) — `design-tokens/build.py` não alimenta `e6_render.py`. Fase 1 §3.1.2 do plano conta com isso funcionando; hoje não funciona.
4. **Recharts vs Chart.js** (Observation #7, Open Q #4) — existe trabalho React duplicado. Decisão adiada pode virar dívida técnica se não resolvida no início da Fase 2.
5. **`ReportShell.MIGRATED_SECTIONS`** é hardcoded e diverge do YAML `enabled` — qualquer mudança no YAML que adicione seção nova precisa tocar 2 lugares. Fase 5 deve unificar.
6. **YAML `tatico`** tem schema diferente de estratégico/USA (só `data_source`). Sections T1-T6 hoje são hand-coded em `TaticoSections.tsx` — Fase 8 precisa decidir se tático vira data-driven como estratégico ou fica como está.

---

## 7. Open questions (✅ RESOLVIDO — ver ADRs 117/121/122/123/124)

**Respostas do usuário (2026-04-23):**
- Q1 → backend (ADR-123)
- Q2 → híbrido — templates para charts, LLM para sections (ADR-122)
- Q3 → backend (ADR-123)
- Q4 → manter Chart.js (ADR-117)
- Q5 → 13px default com override configurável (ADR-121)
- Q6 → diferir `comparisons`/`changelog` para v2
- Q7 → breakpoints: ≥1024 ambos, 768-1023 drawer, ≤767 topnav só
- Q8 → worktree externo para fases longas, shared para curtas
- Q9 → sim, JetBrains Mono no standalone
- Q10 → PR único para Fase 3
- Q11 → sem LLM em `pontos_fortes` por ora
- Q12 → `e6_render.py` aposentado (ADR-124)
- Q13 → ADRs 117/121/122/123/124

Lista original preservada abaixo para auditoria:

### 7.a Lista original das 13 perguntas

1. **`NotasCard` T6 — localStorage vs endpoint persistido?** Recomendo localStorage (Stateless ADR-111 §exceções), promover para endpoint quando houver >1 dispositivo/usuário.
2. **`chart_conclusions` + `section_summaries` — LLM, template ou input manual?** Recomendo híbrido: template para 21 charts (padrão previsível), LLM para 10 seções (narrativo varia). Abre ADR nova.
3. **`Kanban` T3 — persistência de drag-drop?** Recomendo localStorage + botão "Exportar estado" (copia JSON).
4. **Chart.js vs Recharts em `/reports/[id]`?** Hoje 7 charts em Recharts; plano manda Chart.js. Adiar decisão para início da Fase 2 — não bloqueia 1/3/5.
5. **Font-base 13px (exemplar) ou 16px (tokens)?** Recomendo 14px meio-termo + ajustar escalas; ADR nova.
6. **`comparisons[]`/`changelog[]` — Fase 6 ou diferir v2?** Recomendo diferir (`enabled: false` no YAML); entregar pós-Fase 12.
7. **`ReportToc` sidebar + `ReportTopNav` coexistem em que breakpoints?** Recomendo: ≥1024px ambos, 768-1023 sidebar vira drawer, ≤767 só topnav.
8. **Branch naming futuro:** `.claude/worktrees/*` (compartilha refs, risco de reset) ou `../fin-report-premium-phase<N>/` (isolado)? Recomendo isolado para fases longas (Fase 6), shared ok para curtas.
9. **`font-family mono` — adicionar `JetBrains Mono` no HTML standalone do exemplar também (paridade com MonetaryValue)?** Recomendo sim.
10. **Priorização Fase 3:** 27 primitivos em PR único ou sub-fases 3a+3b? Recomendo 3a (Card/Alert/Badge/IconBadge/Divider/KPI) + 3b (Score/Comparison/Collapsible/Kanban), cada ≤800 linhas.
11. **`pontos_fortes[].descricao` — enriquecer via LLM?** Analyzer atual já produz textos iguais ao exemplar — **sem gap real**. Confirmar que fica como está.
12. **`e6_render.py` pós-Fase 11:** continua exportador standalone (email/backup) ou aposenta em favor de SSR Next? Recomendo manter standalone (zero-dep) — confirmar.
13. **ADR number:** plano sugere 117-120; último real é ADR-116 (commit `d9593b7`). Confirmar que 117 está livre quando Fase 1 começar.

---

## 8. Próximo passo

Humano responde §7 (Open Questions) — registra decisões em `docs/DECISIONS.md` como ADR nova conforme necessário — e sinaliza para iniciar a Fase 1.

Fases 1/3/5 ficam unlocked com §7.1–2, 5, 7, 10, 13 respondidas.
Fase 6 precisa de §7.2, 6, 11.
Fase 2 precisa de §7.4, 9.
