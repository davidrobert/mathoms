---
id: A7.5
type: lane
title: "Cleanup final (deletar `config/` + bridges)"
sprint: A7
status: shipped
branch_slug: a7-5-cleanup
ship_date: "2026-04-27"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a7
  - status/shipped
---


# A7.5 — Cleanup final (deletar `config/` + bridges)

> Migrada de tabela em `## Sprint A7` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Onda:** 4 (bloqueante)
- **Depende de:** A7.1 + A7.2a + A7.2b + A7.3 + A7.4 ✅
- **Branch slug:** `a7-5-cleanup`
- **Paralelo com:** —

## Status (legado)

✅ entregue 2026-04-27 — branch `agent/a7-5-cleanup/20260427-1438`. `FileConfigStore` + `legacy_json_to_fiscal` deletados; `materialize_config` + helpers `_override_*` removidos; 5 paths de `config/*` adicionados a `dev/check_forbidden_paths.py` (`categorization.json`, `family_members.json`, `institutions.json`, `parametros_fiscais.json`, `taxas.json`); fixtures `parametros_fiscais.json` + `taxas.json` migradas para `tests/fixtures/legacy_configs/` (preserva goldens E5/E5.N). ``config/report_layout.yaml`` permanece em `config/` (source-of-truth do codegen + default blob). CONFIG_CUTOVER_PLAN.md arquivado.
