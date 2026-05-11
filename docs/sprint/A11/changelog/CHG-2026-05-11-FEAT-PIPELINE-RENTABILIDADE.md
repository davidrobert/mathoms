---
id: CHG-2026-05-11-FEAT-PIPELINE-RENTABILIDADE
type: changelog-entry
date: "2026-05-11"
sprint: A11
lane: "[[A11.w5]]"
adrs:
  - "[[ADR-191]]"
summary: |
  feat(pipeline): card Rentabilidade — TRS efetiva enriquecida + cobertura
  essencial via renda passiva (PR-A do track T06 · ADR-191 Decidido).
tags:
  - type/changelog-entry
  - sprint/a11
  - area/report
  - area/methodology
---

# feat(pipeline): card Rentabilidade — TRS efetiva + cobertura essencial (ADR-191 §D3/D4)

PR-A do track [TRACK-a11-w5-t06-rentabilidade-card](../tracks/a11-w5-t06-rentabilidade-card.md)
encerra três problemas independentes do card S3 "Rentabilidade":

1. **Rótulo enganoso** — domínio agora expõe shape aninhado `ratios.rentabilidade`
   com `status` enum (`ok|sem_irpf|gerador_zero|sem_dados_essencial`), permitindo
   UI rebrandear sem rename interno (D2 — `rentabilidade_pct` flat preservado).
2. **Conteúdo incompleto** — DTO ganha ano-base IRPF, defasagem em meses, meta
   5% configurável e **cobertura essencial via renda passiva**
   (`renda_passiva_mensal / custo_essencial_mensal × 100`).
3. **Drift spec ↔ código** — fecha gap de 7 meses: `custo_essencial_mensal_brl`
   prometido em [FORMULAS.md](../../../reference/FORMULAS.md) linha 32 agora
   é calculado, via 9 categorias canônicas declaradas em
   `scoring.json:reserva_emergencia._base_calculo.custo_essencial_mensal.categorias_in`.

**Entregue:**

- `pipeline/domain/services/essential_expense_calculator.py` (novo) — helper
  puro `compute_custo_essencial_mensal(despesas, categorias_in)` com 12 unit tests.
- `FluxoEnricherConfig.from_configs(categorization, scoring)` lê `categorias_in`
  e popula `despesa_mensal_essencial` em `FluxoCaixaEnriched` + `Janela12m`.
- `RatiosCalculator(RentabilidadeConfig)` constrói `FinancialRatios.rentabilidade`
  aninhado com 4 status; flat `rentabilidade_pct` mantido por back-compat.
- `config/schemas/e5_analysis.schema.json` declara `ratios.rentabilidade` com
  6 properties tipadas + enum de status (modo `warn` tolera campo novo;
  W6-T01 strict cutover trata depois).
- [FORMULAS.md §TRS efetiva e renda passiva](../../../reference/FORMULAS.md)
  publicado — fórmula canônica + relação com Trinity 4% + "não-fazer" do D5.
- [[ADR-191]] flippa para `Decidido (A11.W5)` no merge deste PR.

**Decisões fechadas (não rediscutir — ADR-191 §D5):**

- Sem CDI no card (yield diversificado ≠ taxa nominal RF).
- Sem retorno total da carteira (sem NAV histórico; fora de escopo).
- Sem Trinity 4% no card (SWR de depleção ≠ yield de fluxo).
- Sem rename `rentabilidade_pct` no domínio (custo cross-cutting alto).

**Fora de escopo desta PR (lanes/issues separadas):**

- PR-B (rebrand UI do card S3, full-width, KPI hero, empty state por status).
- Fix do `EmergencyReserveCalculator` para reusar `compute_custo_essencial_mensal`
  (issue separada — risco em `score.componentes[]`).
- Plumbing `despesa_essencial_historico` 12m em snapshot real (consumer da
  regra `lifestyle_creep` em [[ADR-161]]).
- Cruzar impostos não-PJ (IPTU/IPVA/IRPF) com origem do lançamento.

**Testes:** 60 unit (essencial + ratios + enricher) + suite completa
(1973 pytest pipeline) + 1875 backend, todos verdes pós-mudança.
