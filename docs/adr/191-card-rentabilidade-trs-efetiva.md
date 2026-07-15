---
id: ADR-191
type: adr
title: "Card Rentabilidade do relatório expõe TRS efetiva — não retorno total"
status: Decidido
phase: A11.W5
date: "2026-05-11"
relates_to:
  - "[[ADR-076]]"
  - "[[ADR-090]]"
  - "[[ADR-129]]"
  - "[[ADR-143]]"
  - "[[ADR-161]]"
supersedes: []
superseded_by: []
amended_at: ["2026-07-15"]
aliases: ["ADR 191", "Card Rentabilidade TRS", "Renda passiva sobre patrimônio"]
tags:
  - area/report
  - area/frontend
  - area/methodology
  - phase/a11
  - status/decidido
  - type/adr
---

> **Emenda 2026-07-15 (cluster FP-03, onda R2 do [[PLAN-dogfood-report-fix]]):** distingue
> explicitamente **yield-alvo/TRS (5%)** de **taxa de retirada segura/SWR (4%)** entre as
> superfícies e corrige o rótulo da renda passiva estimada (era 5%, valor calculado a 4%).
> Ver §Emenda 2026-07-15 ao final.

## Contexto

O card **"Rentabilidade"** da seção S3 do relatório
([S3InvestimentosSection.tsx:91-100](../../frontend/src/components/report/sections/S3InvestimentosSection.tsx))
exibe hoje apenas o campo `ratios.rentabilidade_pct` (um número solto,
ex.: `3,25%`) sem ano-base, sem janela, sem comparativo, sem
explicação. Usuário relatou que **não consegue interpretar** o número
— pensa que é "retorno total da carteira" (renda + valorização), mas o
valor exposto é **TRS efetiva** (yield de renda passiva observada via
IRPF sobre patrimônio gerador), calculada por
`PassiveIncomeCalculator.calculate()` e aliasada por
`RatiosCalculator` como `rentabilidade_pct` por paridade histórica
com `analyze_ratios` legado.

Revisão multi-agente paralela (`product-designer` + `financial-planner`
+ `senior-cto` + `data-engineer` + `product-manager`, 2026-05-11)
confirmou três problemas independentes:

1. **Rótulo enganoso** — "Rentabilidade" induz leitura de retorno total
   (renda + capital gain). O dado mede yield, não retorno.
2. **Conteúdo incompleto** — falta unidade temporal (% a.a.), ano-base
   IRPF, defasagem em meses, comparativo com meta, tratamento honesto
   do estado `"N/D"`.
3. **Drift spec ↔ código** — [FORMULAS.md §Reserva de emergência](../reference/FORMULAS.md)
   linha 32 afirma que `custo_essencial_mensal_brl` existe alimentado
   por `scoring.json:reserva_emergencia._base_calculo.categorias_in`,
   mas o cálculo da métrica **não está implementado** (consumidores
   usam `despesa_mensal_media_brl` total). Métrica derivada Cerbasi
   "cobre N% das despesas essenciais via renda passiva" depende dessa
   base.

## Decisão

**Renomear conceitualmente o card na UI** e **enriquecer o DTO de
leitura** sem renomear campos internos do domínio. Decisões
estruturadas em 5 pontos:

### D1 — UI: rebranding do card

Título passa de `"Rentabilidade"` para algo que reflete o conceito real
("Renda passiva sobre patrimônio (TRS)" ou equivalente — execução cabe
ao `product-designer` na PR-B). Microcopy de 1 linha explicita o que é
TRS efetiva (yield observado de renda passiva sobre patrimônio gerador,
anualizada). Layout vai a full-width (`md:col-span-4`) com KPI hero +
comparativo com meta 5% + rodapé com ano-base IRPF e defasagem.

### D2 — Domínio: sem rename de `rentabilidade_pct`

O campo `FinancialRatios.rentabilidade_pct` (em
`pipeline/domain/services/ratios_calculator.py:59`) **permanece com o
nome atual**. Rename hard custaria 6+ consumers + goldens E5 + snapshot
OpenAPI + types frontend para ganho cosmético zero. Docstring inline
documenta que é alias histórico de `PassiveIncomeResult.trs_efetiva_pct`.

### D3 — DTO nested para contexto

`FinancialRatios` ganha campo aninhado `rentabilidade`:

```python
@dataclass(frozen=True)
class RentabilidadeRatio:
    valor_pct: Decimal | None
    ano_base: int | None
    defasagem_meses: int | None
    meta_pct: Decimal  # 5.0 default (config tipada)
    cobertura_despesa_essencial_pct: Decimal | None
    status: Literal["ok", "sem_irpf", "gerador_zero", "sem_dados_essencial"]
```

Serializa como `ratios.rentabilidade: {...}` no schema E5. Campo flat
`ratios.rentabilidade_pct` permanece como atalho de back-compat
(deprecated soft, sem prazo de remoção).

### D4 — Métrica derivada nova: cobertura essencial via renda passiva

`cobertura_despesa_essencial_pct = renda_passiva_mensal_brl /
custo_essencial_mensal_brl × 100`. Implementação:

1. Novo helper `compute_custo_essencial_mensal(despesas_por_categoria,
   categorias_in)` em `pipeline/domain/services/`. Lista `categorias_in`
   lida via `ConfigStore` de `scoring.json:reserva_emergencia._base_calculo.categorias_in`
   (já existe — 9 categorias).
2. `FluxoCaixaEnricher` popula `despesa_mensal_essencial_brl` no shape
   do fluxo (additive, não breaking).
3. `_Window` em `RatiosCalculator` lê o campo enriquecido. Sentinela
   `Decimal("0")` quando indisponível → produz
   `cobertura_despesa_essencial_pct = None` + status
   `"sem_dados_essencial"`.

**Bonus identificado, fora do escopo desta ADR:**
`EmergencyReserveCalculator` em [reserva_emergencia_calculator.py:87](../../pipeline/domain/services/reserva_emergencia_calculator.py)
usa `despesa_mensal_media` total quando metodologia exige essencial —
débito latente vs FORMULAS.md §Reserva. Issue separada rastreia o fix
(reuso do mesmo helper).

### D5 — Não-fazer

- **Sem comparação com CDI** no card. TRS efetiva é yield diversificado
  com tax-shield parcial (dividendos isentos PF); CDI é taxa nominal
  pré-IR de RF. Comparar induz mau comportamento ("se TRS<CDI, 100%
  Tesouro Selic é melhor?" — falso, ignora valorização e diversificação).
- **Sem retorno total da carteira** (yield + capital gain). Exigiria
  séries de NAV por holding ao longo do tempo — dado não calculado pelo
  pipeline E2/E3 (reconcilia fluxo de caixa, não NAV histórico). Fora
  de escopo. Re-abrir só com ADR própria + lane dedicada.
- **Sem comparação com meta Trinity 4%** no card. Trinity é SWR de
  depleção do principal; TRS efetiva é yield de fluxo. Incomparáveis.
  `trs_trinity_pct` em `PassiveIncomeConfig` permanece, para uso em
  projeções de IF (não neste card).

## Alternativas consideradas

- **Hard rename `rentabilidade_pct → trs_efetiva_pct`** — rejeitada
  (D2): custo cross-cutting alto, ganho cosmético.
- **DTO flat com 6 campos prefixados em `ratios`** — rejeitada (D3):
  polui namespace de ratios, dificulta evolução semântica.
- **Empurrar `custo_essencial_mensal` para sprint A12** — rejeitada
  (D4): a spec já existe em FORMULAS.md; gap é só implementação. Não
  empurrar débito de spec↔código quando o custo é ~50 LOC.
- **ADR cobre só decisões "não fazer"** — rejeitada: shape do DTO e
  fonte de dado essencial também merecem registro (escolhas com
  alternativas reais).

## Consequências

- **Schema E5** (`config/schemas/e5_analysis.schema.json`) ganha objeto
  `ratios.rentabilidade` declarado. Modo `warn` (default) tolera campo
  novo; W6-T01 (strict cutover) endereça `additionalProperties`
  globalmente.
- **Goldens E5** em runtime (`tests/test_e5_golden_execution.py`)
  validam via schema — não há JSON canônico estático, não exigem regen.
- **Snapshot OpenAPI** muda (campo novo no DTO) — diff esperado em
  `backend/tests/test_openapi_snapshot.py`; commit do diff via
  `make update-openapi-snapshot`.
- **Frontend** consome shape novo em PR-B (lane W5-T06). Card render
  full-width; empty state quando `status != "ok"` ou `defasagem_meses > 18`.
- **`FluxoCaixaEnricher`** ganha responsabilidade de essencial — débito
  histórico (../reference/FORMULAS.md prometia, código não entregava) fechado.

## Rastreabilidade

- Lane: [[A11.w5]] / Track: [[TRACK-a11-w5-t06-rentabilidade-card]]
- Inputs consolidados: revisão multi-agente 2026-05-11
  (`product-designer` + `financial-planner` + `senior-cto` +
  `data-engineer` + `product-manager`)
- Code paths: `pipeline/domain/services/{ratios_calculator,passive_income_calculator,fluxo_caixa_enricher}.py`,
  `config/schemas/e5_analysis.schema.json`,
  `frontend/src/components/report/sections/S3InvestimentosSection.tsx`
- Doc canônico: [FORMULAS.md §TRS efetiva e renda passiva](../reference/FORMULAS.md)
  (a criar no PR-A)

**Status:** `Decidido (A11.W5)` — flipped no merge do PR-A da lane W5-T06.
PR-B (rebrand UI) consome o shape novo.

## Emenda 2026-07-15 (FP-03) — yield-alvo (5%) × taxa de retirada segura (4%)

> Cluster **FP-03** da onda R2 do [[PLAN-dogfood-report-fix]]. Decisão de domínio do
> owner (2026-07-15), endossada após co-design `financial-planner`.

**Contexto do achado.** A revisão dogfood 2026-07-15 encontrou o mesmo rótulo "TRS/taxa de
retirada" carregando **5%** em algumas superfícies (card de Rentabilidade, rendimento da meta
patrimonial) e **4%** em outras (estimativa de renda passiva pela regra de retirada, persona,
motor de sugestões). Concretamente, a narrativa da renda passiva estimada era rotulada
`if_trs_pct` (5%) enquanto o **valor** era calculado a `taxa_retirada_segura_pct` (4%) —
rótulo e número discordavam na mesma frase (cluster CTO-04).

**Decisão (owner).** São **dois conceitos distintos, rotulados distinto** — nunca colapsar:

- **Yield-alvo / TRS efetiva (5%)** — retorno-alvo/observado da carteira geradora (acumulação).
  Vive no card de Rentabilidade e no rendimento da **meta** patrimonial
  (`goals.trs_pct`, `RentabilidadeConfig.meta_pct`). Já era a decisão original desta ADR (o card
  expõe yield, incomparável com Trinity — ver §Consequências acima).
- **Taxa de retirada segura / SWR (4%, regra dos 300 / Trinity ×25)** — taxa prudente de
  **decumulação** que dimensiona a meta de IF e a **estimativa de renda passiva** sobre o
  investível atual (`goals.taxa_retirada_segura_pct`, `if_projector`). Conservadora por
  desenho: superestimar prontidão de IF é a falha perigosa (colapsar em 5%/×20 encurta a meta
  ~20% vs ×25).

Isto **reverte o override FIN-005 (TRS=5%) na superfície de dimensionamento da meta** — o 4%
volta a reger o SWR/meta —, mantendo 5% apenas como yield-alvo descritivo.

**Consequência de código (cluster CTO-04).** A narrativa da renda passiva estimada passa a
rotular `taxa_retirada_segura_pct` (4%), casando rótulo↔valor
(`charts_narrator`/`summaries_narrator`; `taxa_retirada_segura_pct` exposto no modelo de
narrativa). O rendimento da meta patrimonial permanece rotulado com o yield-alvo (5%). Nenhum
cálculo vivo muda além do rótulo — `if_meta` vem de `goals.json` (não há divisor
`custo × 1/TRS` no motor); a recomendação ×25 é metodológica, aplicada no dimensionamento da
meta (wizard/goals), não em recomputação aqui.

**Aceite.** Nenhuma superfície rotula a mesma taxa como 4% e 5%; a estimativa de renda passiva
mostra o valor a 4% rotulado "retirada segura"; o card e o rendimento da meta mostram 5%
rotulado "yield/TRS". Sem bump de manifest do parecer nesta onda.
