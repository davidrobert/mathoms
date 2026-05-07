---
id: CHG-2026-04-15-F65-SYSTEMIC-FALLBACK-LE
type: changelog-entry
date: "2026-04-15"
sprint: F65
summary: "Systemic fallback-leak fix. - **Systemic fallback-leak fix:** BUG-004 só strippava CPF; auditoria detectou `full_name`/`short_name`/`birth_date` do founder vazando via `_convert_members_js"
tags:
  - type/changelog-entry
  - sprint/f65
---


# Systemic fallback-leak fix

- **Systemic fallback-leak fix:** BUG-004 só strippava CPF; auditoria detectou `full_name`/`short_name`/`birth_date` do founder vazando via `_convert_members_json_to_schemas` + export cru em `_export_family_members` para tenant vazio. Fix: `_NEUTRAL_PLACEHOLDER_NAMES` por role + export retorna `{"membros": {}}` para workspace sem members
- Bug colateral: factory `make_member(role="responsavel")` não passava schema; corrigido para `"titular"`
