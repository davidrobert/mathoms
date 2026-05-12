---
id: CHG-2026-05-12-FEAT-PGBL-CARDS-RECONCILIATION
type: changelog-entry
date: "2026-05-12"
sprint: A12
adrs:
  - "[[ADR-196]]"
prs: [232]
commits: ["58fbdc3"]
summary: |
  feat(frontend): reconciliação dos cards PGBL S7×IRPF — Card A
  (`previdencia_pgbl`) degrada para modo informativo quando IRPF Full
  é authoritativo; ganha disclaimer no modo default. Resolve bug
  financeiro P0 de prescrição em workspace simplificado. ADR-196
  Decidida (A12).
tags:
  - type/changelog-entry
  - sprint/a12
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
---

# feat(frontend): reconciliação cards PGBL S7×IRPF (priorização condicional)

Implementa a lane separada deferida em [[ADR-189]] §6 — reconciliação
visual dos **dois cards PGBL** que coexistiam sem cross-link no
relatório premium:

- **Card A** (`previdencia_pgbl` em §S7) — prospectivo/prescritivo,
  baseado em fluxo PJ inferido pelo `flow_classifier`.
- **Card B** (`pgbl_capacidade` em §S_IRPF_OTIMIZACAO) —
  retrospectivo/declarado, baseado em IRPF Full ([[ADR-189]] · 4
  estados tipificados).

[[ADR-196]] **Decidida (A12)** no merge ([apps#232](https://github.com/davidrobert/mathoms/pull/232)).

## Bug financeiro P0 resolvido

`financial-planner` (G0) classificou como **P0/severidade alta** sob
Cerbasi/AUVP: Card A prescrevia "aporte sugerido R$ X/mês, economia
IR R$ Y/ano" mesmo em workspaces declarando IRPF pelo modelo
simplificado — regime onde PGBL **não gera dedução**. Usuário podia
aportar esperando benefício fiscal inexistente. Caso majoritário em
renda PF brasileira (G0: ~70-80% dos usuários).

## Co-design 2026-05-12

Três sign-offs paralelos antes do PR:

- **G0 (financial-planner):** veredito explícito Alternativa B
  (priorização condicional). Copy literal §4 da ADR aprovada
  (paralelismo lexical com Card B — "tabela regressiva", "horizonte",
  "taxa de administração", "INSS"). Janela authoritativa: IRPF
  `ano_base = N` para análise terminando em `N` ou `N+1`; gap ≥ 2
  anos → `default-defasado`. Defer alerta de divergência S7
  (aportado observado) > IRPF (declarado) para lane futura.
- **G2 (data-engineer):** Helper TS no frontend (Q1.a). Zero churn em
  backend, schema E5, goldens E5, OpenAPI snapshot. `primary_year`
  derivado de `fluxo_caixa.receita_despesa_mensal_detalhado.labels`
  (sem plumbing canônico em backend — débito anotado em ADR §5).
- **G4 (product-designer):** Aprovou B com ajustes — `feature →
  neutral` em modos informativos (Card A não compete com Card B
  autoritativo); supressão do grid de 4 KPIs em informativo (valores
  inline); cross-link via `<a href="#S_IRPF_OTIMIZACAO">` com
  `underline decoration-dotted` (funciona em HTML + PDF Playwright);
  `aria-label="Métrica não aplicável"` no "—" (aplicado também ao
  Card B oportunisticamente).

## Comportamento por modo

| IRPF | Card B estado | Modo Card A | Variante | Tamanho | Grid | Disclaimer |
|---|---|---|---|---|---|---|
| ausente | — | `default` | feature | full | sim | **sim (novo)** |
| defasado ≥ 2 anos | qualquer | `default-defasado` | feature | full | sim | **sim + nota** |
| auth | `capacidade_disponivel` | `informative-capacidade` | neutral | half | — | — |
| auth | `modelo_simplificado` | `informative-simplificado` | neutral | half | — | — |
| auth | `no_teto` | `informative-no-teto` | neutral | half | — | — |
| auth | `sem_renda_tributavel` | `informative-sem-renda` | neutral | half | — | — |

## Entregue

- **Helper puro (frontend):**
  - `frontend/src/lib/irpf/pgbl-card-strategy.ts` —
    `derivePrimaryYear(labels)`, `matchIrpfToPeriod(anos, primaryYear)`,
    `getPgblCardStrategy(irpfKpis, primaryYear) → { mode, anoBase,
    defasadoAnos }`, `isInformativeMode(mode)`.
- **Card (frontend):**
  - `frontend/src/components/report/cards/PrevidenciaPgblCard.tsx`
    refatorado. Aceita `mode?: PgblCardMode` (default `"default"`
    preserva compat legacy) + `anoBase?: number`. Switch sobre 6
    modos com copy literal aprovada por G0.
- **Section integration:**
  - `frontend/src/components/report/sections/S7IndependenciaSection.tsx`
    consome `useIrpfKpis` + deriva `primaryYear` de
    `fluxo_caixa.receita_despesa_mensal_detalhado.labels`, computa
    `strategy = getPgblCardStrategy(...)` e passa `mode` + `anoBase`
    ao card.
- **A11y oportunista:**
  - `frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx`
    — `aria-label="Métrica não aplicável"` no "—" (Card B), além do
    Card A (modos `informative-simplificado` e `informative-sem-renda`).

## Testes

- **Vitest helper** (`frontend/tests/lib/pgblCardStrategy.test.ts`):
  22 testes cobrindo `derivePrimaryYear`, `matchIrpfToPeriod`,
  `getPgblCardStrategy` (matriz de 9 ramos da §D1), `isInformativeMode`.
- **Vitest card** (`frontend/tests/components/PrevidenciaPgblCard.test.tsx`):
  10 testes cobrindo os 6 modos do Card A — variant + presença de
  copy literal + presença/ausência de disclaimer + presença do grid
  + cross-link âncora `#S_IRPF_OTIMIZACAO` + `aria-label` no "—".
- Suíte Vitest completa: **978 verde** (1 skip preexistente).
- Pre-commit: **Passed** (incl. code-style baseline sem regressão).

## Escopo preservado

- Backend `PrevidenciaAnalyzer` + `IRPFAnalyzer` **intactos** (ISP /
  [[ADR-097]] §D3 preservado).
- Schema `e5_analysis.schema.json` **intacto**.
- Goldens `tests/test_e5_golden_execution.py` **intactos**.
- OpenAPI snapshot **intacto**.
- Card B (`IrpfPgblCapacidadeCard`) **não muda** (4 estados ADR-189 +
  modulação ADR-195 preservados); única alteração é a11y.

## Não-objetivos (lane separada)

Ver [[ADR-196]] §6:

- VGBL vs PGBL distinção no `flow_classifier` — lane futura.
- Alerta de divergência S7 (aportado observado) > IRPF (declarado) —
  lane futura.
- Plumbing canônico de `analysis_period` server-side — pendente até
  UI ganhar seletor de período.
- Card unificado (Alternativa C) — defer indefinido.

## Débito identificado

- **Visual snapshot do S7 regrediu** (976×476 → 976×537 px) por causa
  do novo disclaimer no modo `default` — esperado e correto. Job
  "Frontend visual snapshots (relatório nativo)" do CI marcou
  failure não-blocking; gate principal "All checks green" passou.
  Regenerar baseline com
  `PW_VISUAL=1 npm run test:e2e -- --project=visual --grep "sections\." --update-snapshots`
  em lane follow-up (provavelmente bundle com próxima mudança em
  S7).
