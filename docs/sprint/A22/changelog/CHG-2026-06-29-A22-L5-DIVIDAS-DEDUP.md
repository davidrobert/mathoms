---
id: CHG-2026-06-29-A22-L5-DIVIDAS-DEDUP
type: changelog-entry
date: "2026-06-29"
sprint: A22
lane: "[[A22.l5]]"
adrs: ["[[ADR-301]]"]
prs: [689]
summary: |
  Dedup de dívida cross-IRPF + schema formal de `dividas` (F1-O3). dividas_dedup.py
  como EntityDedupPolicy (ADR-276) sobre o runner de A21: chave numero_contrato ⊳
  (tipo, credor_norm, desc_norm); cross-year une saldo_31_12; cross-declarante funde
  "casal" só ao centavo; warning saldo_nao_monotonico só p/ amortizável fixa sem
  indexador. Schema de `dividas` apertado de array-livre → required +
  additionalProperties:false (valida em warn). Bloco 3d no consolidador. 20 testes
  INV-D1..D8. Fecha o último double-count patrimonial (KR2/KR3). ADR-301 Decidido.
tags:
  - type/changelog-entry
  - sprint/a22
  - area/pipeline
  - area/data-lineage
---
