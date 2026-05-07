---
id: A7.6
type: lane
title: "Rules-as-code (dissolver `docs/methodology/`)"
sprint: A7
status: shipped
branch_slug: a7-6-rules-as-code
ship_date: "2026-04-27"
adrs: ["[[ADR-143]]", "[[ADR-145]]", "[[ADR-146]]", "[[ADR-147]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a7
  - status/shipped
---


# A7.6 — Rules-as-code (dissolver `docs/methodology/`)

> Migrada de tabela em `## Sprint A7` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Onda:** 2.5
- **Depende de:** A7.4 ✅ + ADR-143/145/146/147 (G1)
- **Branch slug:** `a7-6-rules-as-code`
- **Paralelo com:** A7.2a, A7.3

## Status (legado)

✅ entregue 2026-04-27 — 7 commits (branch `agent/a7-6-rules-as-code/20260427-1311`). 4 markdowns dissolvidos: regras universais em docstrings + ADRs (patrimonio_calculator · source_tier · reconciliation_service · parse_milhas_md_content); `BankAccount.source_tier` schema (Alembic z4a5b6c7d8e9 — colapsa heads pre-existing A7.2a/A7.2b); milhas migrator + bridge `<ws>/notes/`; novo §4.1 Domain glossary em ARCHITECTURE; `docs/methodology/` virou path proibido. 12 specs novos (3 ADR-145 anônimas + 9 ADR-146 tie-breaking + 2 ADR-147 bridge). Fix incidental: alembic guardrails (4 specs) voltam a verde.
