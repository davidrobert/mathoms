---
id: CHG-2026-04-15-F65-ISOLATION-PARAM-TRIC
type: changelog-entry
date: "2026-04-15"
sprint: F65
summary: |
  Isolation paramétrica. - **Isolation paramétrica:** 27 tests cobrindo 9 domínios (workspace settings, members+accounts, categories, documents, vault, pipeline runs+reviews, reports, transactions, LLM config, notifications).
tags:
  - type/changelog-entry
  - sprint/f65
---


# Isolation paramétrica

- **Isolation paramétrica:** 27 tests cobrindo 9 domínios (workspace settings, members+accounts, categories, documents, vault, pipeline runs+reviews, reports, transactions, LLM config, notifications). 2 universos paralelos User A/B — `_assert_no_b_leak()` via signatures únicas. **0 vazamentos.**
