---
id: CHG-2026-05-06-DOCS-DECISIONS
type: changelog-entry
date: "2026-05-06"
sprint: A11
adrs: ["[[ADR-170]]", "[[ADR-171]]", "[[ADR-172]]", "[[ADR-173]]", "[[ADR-174]]", "[[ADR-175]]"]
summary: |
  docs(decisions,plan): ADR backfill Wave 1 + CLAUDE.md sync (W1-T03 + W1-T06 · 2026-05-06). - **docs(decisions,plan): ADR backfill Wave 1 + CLAUDE.md sync (W1-T03 + W1-T06 · 2026-05-06):** Backfill de 6 ADRs `Proposto` — ADR-170 (refresh tokens family-
tags:
  - type/changelog-entry
  - sprint/a11
---


# docs(decisions,plan): ADR backfill Wave 1 + CLAUDE.md sync (W1-T03 + W1-T06 · 2026-05-06)

- **docs(decisions,plan): ADR backfill Wave 1 + CLAUDE.md sync (W1-T03 + W1-T06 · 2026-05-06):**
  Backfill de 6 ADRs `Proposto` — ADR-170 (refresh tokens family-revocation, fecha SR-002),
  ADR-171 (Fernet rotation MultiFernet, fecha SR-003), ADR-172 (stuck-runs heartbeat,
  fecha SR-007), ADR-173 (LLM budget hard-stop + LLMCallLog universal, fecha SR-006/DE-013),
  ADR-174 (off-site backup R2 + restore drill, fecha SR-004/BB-007), ADR-175
  (prompt injection defense camadas, fecha SR-009). Cada uma vira `Decidido` no merge da
  lane W2/W3/W4 correspondente. CLAUDE.md ganha §"ADR Proposto antes de PR P0/P1" como
  política operacional (lição Trade-off 5). Sync de §Code style › Testes substitui
  referência a `test_e3_main_with_store_parity.py` (deletado em A6c.3) por
  `test_e3_golden_execution.py` + ponteiro para débito DE-005 em W6-T01.
