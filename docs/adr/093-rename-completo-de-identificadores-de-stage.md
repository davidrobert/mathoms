---
id: ADR-093
type: adr
title: "Rename completo de identificadores de stage (Opção A)"
status: Decidido
phase: "F9 · sub-fases 9.0–9.6 entregues"
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 093"]
tags:
  - area/ops
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 85
---

# ADR-093 — Rename completo de identificadores de stage (Opção A)

**Status:** Decidido (F9 · sub-fases 9.0–9.6 entregues) — F9.0 ✅ (2026-04-24) · F9.1 ✅ (2026-04-25) ·
**F9.2 T1 ✅ (2026-04-25)** — `STAGE_REGISTRY` keys descritivas +
`resolve_stage_name`/`to_legacy_stage_name` helpers + compat reverso;
T2-T5 (substituição de strings literais em call-sites) abertas como
follow-ups incrementais · **F9.3 ✅ (2026-05-05)** — migration validada e testada ·
**F9.5 ✅** (#720) · **F9.6 ✅ (2026-07-06)** (#799 — writers descritivos + labels) ·
**F9.4 ✅ (2026-07-06)** — `git mv scripts/e*.py` → nomes descritivos (W6-T03)
**Data:** 2026-04-19 • **Plano:** Fase 9 inteira

> **Nota (2026-05-05):** F9.3 fechada — `q5r6s7t8u9v0` sincronizado com `STAGE_RENAME_MAP`
> (add E1.6/remove E6/E6-final); pre-check aborta em stage desconhecido; 5 testes em
> `backend/tests/test_stage_rename_migration.py`; runbook em `docs/reference/runbooks/f9_3_alembic_upgrade.md`.

**Contexto:** Os identificadores legados (`"E0-audit"`, `"E1.5c"`, `"E2-faturas"`,
`"E5"`, `"E7-apply"`…) são posicionais e opacos sem contexto. Aparecem em
código (strings literais), DB (coluna `pipeline_artifacts.stage`), logs,
flags de CLI (`--from E3`), dashboards. O mapeamento para nomes descritivos
é 1:1, documentado em `STAGE_RENAME_MAP` (ADR-087) — mas renomear em produção
exige coordenação entre código, DB, dev-ops e docs.

**Decisão:** Aplicar **Opção A — rename em bloco** em 7 sub-fases (Fase 9 do plano):

1. **9.0** ✅ (2026-04-24) — Auditoria: `dev/audit_stage_references.py`
   (ferramenta reutilizável) + resumo durável em
   [`docs/archive/audits/f9_audit_20260424.md`](../archive/audits/f9_audit_20260424.md);
   3468 ocorrências mapeadas em 6 categorias, zero blockers. Testes
   `test_covers_all_legacy_names` + `test_is_bijective` em
   `tests/unit/pipeline/test_stage_spec.py` garantem `STAGE_RENAME_MAP`
   exaustivo e bijetivo.
2. **9.1** ✅ (2026-04-25) — `git mv pipeline/stages/e*.py → *descriptive*.py`
   (14 wrappers). Imports atualizados em `pipeline/orchestrator.py`,
   `pipeline/__init__.py` e tests. `pipeline/stages/e2.py` (shim
   compartilhado, fora do mapa) e `pipeline/stages/e7.py`
   (`run_crossval` + `run_apply` agrupados) deferidos para F9.6.
3. **9.2** — Substituir strings literais em Python um arquivo por vez,
   com `pytest` entre cada.
4. **9.3** — Alembic migration `q5r6s7t8u9v0_rename_stage_identifiers`:
   `UPDATE pipeline_artifacts SET stage = <new> WHERE stage = <old>` +
   idem para `pipeline_stage_logs`. Upgrade+downgrade testados
   (`test_stage_rename_migration.py`, 5 testes).
5. **9.4** ✅ (2026-07-06) — `git mv scripts/e*.py → *descriptive*.py`
   (9 módulos; não-1:1: `e2_extract.py` → `extract_bank_documents.py`
   cobre `extract_invoices`+`extract_statements`; pacote `scripts/e2/`
   de parsers permanece). Alias `e_reset.py --from X` tornou-se N/A —
   CLI standalone descontinuada em ADR-212.
6. **9.5** — Guardrail: `tests/unit/pipeline/test_no_legacy_stage_names.py`
   (parametrizado por todos os legados) com soft-fail default + hard-fail
   via `MATHOMS_ENFORCE_STAGE_RENAME=1`.
7. **9.6** — Remover `MaterializationBridge`, `_init_config()` global, aliases.

**Mapa canônico** (fonte de verdade: `pipeline.stage_spec.STAGE_RENAME_MAP`):

```
E0-audit    → audit_documents        E2-extratos → extract_statements
E0-unlock   → unlock_documents       E2-llm      → extract_with_llm
E0-route    → route_documents        E3          → reconcile_transactions
E1          → extract_members        E4          → categorize_transactions
E1.5        → extract_baseline       E5          → analyze_finances
E1.5c       → consolidate_baseline   E5.N        → generate_narratives
E2-faturas  → extract_invoices       E6          → render_report
                                     E7-crossval → validate_cross
                                     E7-review   → review_finances
                                     E7-apply    → apply_review
                                     E6-final    → render_final_report
                                     E5-revised  → analyze_finances_revised
```

**Procedimento em produção** (pré-migration):
1. Backup obrigatório (`sqlite3 mathoms.db .dump > backup.sql`).
2. Verificar: `SELECT DISTINCT stage FROM pipeline_artifacts` — nenhum
   nome fora do mapa (investigar antes de prosseguir).
3. Deploy do código pós-Fase 9.2 com alias compat.
4. `alembic upgrade head`.

**Consequências:**
- ✅ Nomes descritivos em logs/dashboards — engenheiro novo entende sem consultar tabela.
- ✅ Mapa exaustivo testado bloqueia divergência silenciosa.
- ⚠️ Queries hardcoded externas (Grafana, Retool) quebram — comunicar antes.
- ⚠️ Uma janela de manutenção para migration — `pipeline_artifacts` pode ser grande.
- ❌ Aliases de compat em `e_reset.py` são técnica-debt temporária.

**Artefatos:** `pipeline/stage_spec.py::STAGE_RENAME_MAP`,
`backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py`,
`backend/tests/test_stage_rename_migration.py`,
`tests/unit/pipeline/test_no_legacy_stage_names.py`,
`_scratch/audit_stage_references.py`.
