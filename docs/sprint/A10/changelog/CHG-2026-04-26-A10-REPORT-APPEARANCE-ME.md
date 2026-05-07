---
id: CHG-2026-04-26-A10-REPORT-APPEARANCE-ME
type: changelog-entry
date: "2026-04-26"
sprint: A10
adrs: ["[[ADR-109]]", "[[ADR-121]]"]
commits: ["fa1b4ef", "35eee5f", "710ae15", "fc74ab3", "db6cf6f"]
summary: |
  Report Appearance Menu — refinement [ADR-121](DECISIONS.md#adr-121--typography-base-13px-com-override-configurável) Fase 4 (2026-04-26) — ✅. - **Report Appearance Menu — refinement [ADR-121](DECISIONS.md#adr-121--typography-base-13px-com-override-configurável) Fase 4 (2026-04-26) — ✅:** Funde `FontSc
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Appearance Menu — refinement [ADR-121](DECISIONS.md#adr-121--typography-base-13px-com-override-configurável) Fase 4 (2026-04-26) — ✅

- **Report Appearance Menu — refinement [ADR-121](DECISIONS.md#adr-121--typography-base-13px-com-override-configurável) Fase 4 (2026-04-26) — ✅:**
  Funde `FontScaleToggle` (3 botões "Compacto/Normal/Confortável") e
  `ReportThemeToggle` (Light/Dark) em um único `<AppearanceMenu/>` com
  botão trigger `Aa` que abre popover. Mudanças:
  - Default `useReportFontScale` `"compact"` → `"normal"` — 13px era
    mesquinho para tabela monetária com `tabular-nums` (padrão fintech
    moderno opera 14-16px).
  - Passos `13/15/17px` → `14/16/18px`. 4px entre extremos torna a
    diferença perceptível (antes 2px era imperceptível — origem da
    queixa "aparentemente esses botões não fazem nada").
  - Labels "Compacto/Normal/Confortável" trocados por ícone `Aa` em
    3 tamanhos progressivos dentro do popover (padrão Medium/NYT/Apple
    Books). Tooltip com nome textual mantido para a11y.
  - `transition: font-size 180ms ease-out` em `[data-report-scope]` para
    feedback visual imediato.
  - Top-nav reduz 2 controles para 1; abre espaço para futuras prefs de
    leitura no mesmo popover (line-height, largura de coluna, modo print).

  Arquitetura **inalterada** — continua local + localStorage
  (`mathoms:report:font-scale`). Reading-time prefs (fonte, tema,
  line-height) seguem padrão da indústria: ficam inline na superfície de
  leitura, não em `/settings`. ADR-121 ganhou subseção
  "Refinamento UX (2026-04-26)" — não é ADR nova. `FontScaleToggle.tsx`
  e `ReportThemeToggle.tsx` deletados (único consumer era `ReportShell`).
  Lane: [`report-appearance-menu`](BACKLOG.md#lanes-abertas-agora--pickup-table).
  Prompt: [`track_report_appearance_menu.md`](agent_prompts/track_report_appearance_menu.md).

- **Report Premium UI v2 — Onda F (Hero KPI + Cover identity) ✅ 5/5
  (2026-04-26):** polish completo do topo do relatório estratégico,
  alinhando com `EXEMPLO_DE_RELATORIO.html`. **v2.F.1** trocou 4 KPIs
  uniformes por 6 com hierarquia (`fa1b4ef`); **v2.F.2** reposicionou
  o conjunto para sumário executivo dedicado fora de S1 (`35eee5f`);
  **v2.F.3a/b/c** entregou cover identity (título estático + família
  no badge/meta-card + PDF filename) executada por **3 agentes
  paralelos em worktrees isoladas** com contrato API firmado no plano
  §17.8 — `710ae15` backend, `fc74ab3` PDF filename, `db6cf6f`
  frontend cover. Zero conflito (arquivos disjuntos). Cross-check com
  `EXEMPLO_DE_RELATORIO.html:1379-1419` (8 KPIs com `kpi-hero`) e
  `:1281-1305` (cover) identificou que o hero atual não respondia à
  pergunta central ("quando ficamos independentes?") e o cover soava
  contábil/operacional ("Fechamento Abril 2026") com período
  triplicado. Decisões finais sintetizadas após review cruzado de
  financial-planner (Perini/Cerbasi/AUVP) + product-designer (a11y/
  hierarquia/densidade), em `docs/plan/REPORT_PREMIUM/_README.md` §§17.6-17.8:

  - ✅ **v2.F.3c** — PDF filename composto no backend
    ([download_pdf.py](backend/app/application/report/download_pdf.py)
    via header `Content-Disposition`). Helpers `slugify_family`,
    `extract_period_yyyymm`, `compose_pdf_filename` em `_common.py`.
    Slug ASCII-safe (`Gonçalves d'Ávila` → `goncalves-d-avila`).
    Padrão: `mathoms-planejamento-{slug-familia}-{YYYY-MM}.pdf`.
    Fallback gracioso: sem surname omite slot; sem período cai em
    `generated_at`. Envolvido em `sanitize_filename` (defesa
    anti-injeção; whitelist `[A-Za-z0-9._-]` preserva hífens). 4
    testes novos; 24 passed em `test_reports.py`. `ExportToolbar` no
    frontend só dispara `window.print()` ou `onDownloadPdf` injetado,
    sem gerar nome.

  - ✅ **v2.F.3b** — Frontend cover refresh
    ([ReportCover.tsx](frontend/src/components/report/shell/ReportCover.tsx)
    +
    [ReportShell.tsx](frontend/src/components/report/ReportShell.tsx)).
    Título estático `Planejamento Financeiro` (descarta
    `displayTitle` dinâmico — brand nav passa a usar `reportTitle`);
    subtítulo estático `Pessoal e Patrimonial`; badge dinâmico
    `Relatório · Família {Surname}` ou fallback `Relatório
    Patrimonial`; meta-cards reordenados (Família condicional,
    Período de referência em pt-BR `jan 2023 — abr 2026` com em-dash
    U+2014, Gerado em pt-BR, `Mathoms v{N}` lido de `package.json`).
    Helper exportado `formatPeriodCoverPtBR()` em
    [format.ts](frontend/src/lib/format.ts). Tipo TS
    `workspace_family_surname?: string | null` em `ReportResponse`.
    9 testes novos; 603 passed (1 skipped).

  - ✅ **v2.F.3a** — Backend expõe `workspace_family_surname:
    Optional[str] = None` em `ReportResponse` (lookup escalar
    `select(Workspace.family_surname).where(Workspace.id == workspace_id)`
    em `application/report/get_report.py`); snapshot OpenAPI
    atualizado (ADR-109); 2 testes (com surname → "Silva"; sem →
    `None`); 1328 testes backend passed. **Lista
    (`list_reports`) não alterada** (escopo era GET singular; lista
    devolve `null` no campo opcional para clientes que não usam).

  - ✅ **v2.F.2** — `ExecutiveSummarySection` (container não-numerado,
    fora da TOC seccional, `id="sumario-executivo"`) wrapping
    `HeroKpiGrid`, renderizado no `ReportShell` entre
    `ReportPremissasBlock` e `PerfilFamiliaCard`, gated por
    `mode==="estrategico"`. Paridade com
    `EXEMPLO_DE_RELATORIO.html:1376` (`<section id="kpis">` antes de
    `secao-1`). `S1PatrimonioSection` deixa de importar `HeroKpiGrid`
    e seu prop `ratios` (não usado fora do hero); volta a ser focada em
    estrutura+composição (3 charts + 4 cards). Score continua duplicado
    propositalmente entre hero (mini KPI) e S1 (gauge `ScoreCard`) —
    leitura em 5s × breakdown completo. Refactor de posicionamento
    puro, zero mudança de componente, dado ou contrato DTO. Vitest 593
    passed.

  - ✅ **v2.F.1** — `HeroKpiGrid` substitui `PatrimonioKpiRow`. 6 KPIs
    em 2 linhas (3-3 em xl, 2-2 em sm-md, empilhados em sm).
    **Linha 1** — onde estou: Patrimônio Líquido · **Investível
    (HERO)** · Reserva (semáforo verde≥6m / warning 3-6m / red <3m).
    **Linha 2** — para onde vou: Taxa de Poupança · **Independência
    Financeira (HERO composto)** · Score. Card de IF funde
    Meta+Gap+Prazo numa narrativa única (% atingido + progress bar +
    prazo em anos + gap em R$ vermelho), em vez dos 3 cards paralelos
    do exemplo. Custo de Vida e Renda Mensal **não entram** no hero —
    são inputs de fluxo, vivem em S2; aparecem só como contexto inline
    em sub-labels (Reserva em meses, etc.). `KpiTone` estendido com
    `"warning"` (`var(--brand-warning)`) — additivo, sem breaking
    change para consumers existentes (UiDevPlayground, demais
    sections). Lane puramente frontend, zero mudança de contrato DTO.
    `PatrimonioKpiRow.tsx` removido. Vitest 593 passed; ESLint clean
    em `src/`; pre-commit verde.
