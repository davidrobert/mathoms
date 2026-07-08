---
id: CHG-2026-07-08-A32-L2-VOCABULARIO-E2LLM-CUTOVER
type: changelog-entry
date: "2026-07-08"
sprint: A32
lane: "[[A32.l2]]"
adrs: ["[[ADR-312]]", "[[ADR-286]]"]
prs: [828, 839, 840]
summary: |
  Fecha o gap de contrato E2-LLM deixado em aberto pela A32.l2 (#826): fallback `membro` no `BankStatement.from_e2_dict` (#828); ADR-312 Proposto→Decidido fechando a não-decisão adiada da ADR-286 (#839, #840) — writer E2-llm passa a canonical-only (`banco`/`tipo`), `required` do `e2_llm_artifact.schema.json` flipa, fallbacks permanentes (sem sunset) nos 3 readers descobertos sem cobertura (E4 adapter/gate ADR-244, síntese de fatura no preprocessor, `institution` de rows pré-A28.l8). Co-design `data-engineer` + `senior-cto`. Follow-up do plano DATA_LINEAGE fechado; runbook `schema_validation_strict_flip.md` atualizado com o novo `required`.
tags:
  - type/changelog-entry
  - sprint/a32
  - area/pipeline
  - area/data-lineage
---
