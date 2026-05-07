---
id: CHG-2026-05-06-FIX-PIPELINE
type: changelog-entry
date: "2026-05-06"
sprint: A11
adrs: ["[[ADR-161]]", "[[ADR-168]]"]
summary: |
  fix(pipeline): regras suggestion dormentes + carry-trade endividamento (W1-T02 + W1-T07 · 2026-05-06). - **fix(pipeline): regras suggestion dormentes + carry-trade endividamento (W1-T02 + W1-T07 · 2026-05-06):** Findings FP-001/2/3/9 do platform review.
tags:
  - type/changelog-entry
  - sprint/a11
---


# fix(pipeline): regras suggestion dormentes + carry-trade endividamento (W1-T02 + W1-T07 · 2026-05-06)

- **fix(pipeline): regras suggestion dormentes + carry-trade endividamento (W1-T02 + W1-T07 · 2026-05-06):**
  Findings FP-001/2/3/9 do platform review. **W1-T02 — regras Onda 8
  dormentes:** (a) FP-001 `rule_renda_passiva_real_baixa` ganha alias
  defensivo `if_pct ↔ progresso_if_pct` + `goals.renda_passiva_mensal_observada_brl`
  (snapshot real expõe `if_pct`, paridade com `IFProjection`); (b)
  FP-002 ponto forte "Caminho para IF" — `e5_analyzer_adapter` agora
  passa `goals={"if_pct": if_projection.if_pct}` para
  `PontosFortesAnalyzer` (alias `if_pct/progresso_pct` no analyzer);
  (c) FP-003 `rule_dolarizacao_atrasada` removida (USA modo deletado em
  ADR-168) de `ALL_RULES` + `KIND_TO_CATEGORY` + `VALID_SUGGESTION_KINDS`
  + ADR-161 §Follow-ups #1 atualizada. **W1-T07 — carry-trade
  endividamento (Cerbasi · Equilíbrio Financeiro):** FP-009
  `IFProjection.to_legacy_dict` emite `retorno_esperado_pct_aa` (provém
  de `IFProjectorConfig.retorno_real_anual_pct`); `rule_endividamento_perigoso`
  agora dispara via carry-trade quando `custo_medio_pct_aa >
  retorno_esperado_pct_aa + CARRY_TRADE_MARGIN_PP` (1pp constante
  nomeada). 25 unit tests novos em `tests/unit/pipeline/test_suggestion_rules.py`
  + e2e `tests/test_e5_to_suggestion_e2e.py` com snapshot real
  (`build_e5_output`, sem mocks).
