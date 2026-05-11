---
id: CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-PIPELINE
type: changelog-entry
date: "2026-05-11"
sprint: A12
lane: "[[A12.cat-learning-loop]]"
adrs:
  - "[[ADR-186]]"
prs: [194]
commits: ["ab69414"]
summary: |
  feat(pipeline): CategorizationRulesV2 com ordem de match estável,
  sticky manual e enforcement de mês fechado — A12.P2 (ADR-186 Decidida).
tags:
  - type/changelog-entry
  - sprint/a12
  - area/pipeline
  - area/categorization
  - area/methodology
---

# feat(pipeline): CategorizationRulesV2 + sticky/mês-fechado enforce (A12.P2)

P2 do plano CAT_LEARNING_LOOP entrega o motor de match no pipeline E4.
[[ADR-186]] **Decidida** no merge.

**Entregue:**

- `CategorizationRulesV2` value object frozen em
  `pipeline/domain/services/categorization_service.py` (`template_keywords`
  + `learned_rules`).
- `LearnedRule` dataclass + sort estável
  `(priority desc, len(keyword) desc, created_at asc)`.
- Adapter `e4_categorizer_adapter.py` lê `categorization_rules` do
  workspace, popula `LearnedRule`, e cria/atualiza
  `TransactionOverride(source="rule", rule_id=...)` para auditoria.
- **Sticky manual:** `TransactionOverride(source="manual")` nunca é
  atropelado por regra.
- **Mês fechado:** re-categorização retroativa recusada em meses com
  `report_publication` viva ([[ADR-187]] integrado).
- Goldens E4 verdes (paridade legacy garantida).
- Benchmark: match ≤2× tempo atual em workspace com 100 regras.

Pré-requisito P3 (Backend API).
