---
id: RULE-alocacao-alvo-7-classes
type: domain-rule
concept: "Alocação-alvo (7 classes AUVP)"
methodology: [auvp]
canonical_adr: "[[ADR-141]]"
enforcer_modules:
  - pipeline/domain/services/investimentos_classes_analyzer.py
formula_ref: "FORMULAS.md#alocação-auvp"
tags:
  - type/domain-rule
  - methodology/auvp
---

# RULE — Alocação-alvo (7 classes AUVP)

**Conceito.** Alocação-alvo dos investimentos em 7 classes canônicas AUVP: `rf_pos`, `rf_pre`, `rf_ipca`, `acoes_br`, `acoes_int`, `fiis`, `caixa`. Rebalanceamento default: por aporte (princípio Diagrama do Cerrado) — o próximo aporte vai para a classe mais subalocada.

**Por quê.** A AUVP **não é** "fundamentalista + FIIs" como o schema v1 reduzia (4 buckets) — é alocação multi-classe + rebalanceamento por aporte. Colar RF pré/pós/IPCA num único bucket ou misturar ações BR com internacionais perde o que é distintivo da metodologia, e impede o KPI `desvio_max_pct` (sinaliza onde alocar o próximo aporte).

**Doutrina canônica.** Definida em [ADR-141](../../adr/141-goal-alocacao-alvo-schema-v2-7-classes-auvp.md) (schema v2 **em produção** — v1→v2 fechado na emenda A12.alocacao-v2, 2026-07-08). Migração v1→v2: `renda_fixa_pct` → 50% pos / 25% pré / 25% IPCA; `imoveis_reits_pct` → `fiis_pct`; `liquidez_usd_pct` → 70% `acoes_int_pct` + 30% `caixa_pct`. Modo simples (4 buckets) pode ser oferecido como toggle para patrimônios <R$100k, mas a fonte de verdade é v2.

**Enforcer.**
- [`pipeline/domain/services/investimentos_classes_analyzer.py`](../../../pipeline/domain/services/investimentos_classes_analyzer.py) — `InvestimentosClassesAnalyzer` classifica por keywords configuráveis. Schema v2 **em produção**: backend serializa via `pipeline_adapter._serialize_alocacao_goal`; frontend (`plano/alocacao/page.tsx`) consome o `derived` do backend (o `alocacaoBucketMapper` v1 foi deletado).

**Fórmula.** Ver [FORMULAS.md §Alocação (AUVP)](../FORMULAS.md#alocação-auvp) — `desvio_classe_pct = atual_pct − alvo_pct`, `desvio_max_pct = MAX(|desvio_classe_pct|)`. Não somar desvios (zero-soma).

**Metodologias.** AUVP (Raul Sena) — Diagrama do Cerrado, rebalanceamento por aporte mensal em vez de venda + recompra.
