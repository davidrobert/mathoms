---
id: CHG-2026-06-12-SUGGESTION-LIFECYCLE-F1-F4
type: changelog-entry
date: "2026-06-12"
sprint: A25
lane: null
adrs: ["[[ADR-290]]"]
prs: [622, 623, 624, 626, 627]
breaking: false
summary: "PLAN-suggestion-lifecycle F1–F4 mergeados em main: supersede-per-run + thesis_key para Suggestion origin=llm (ADR-290 Decidido), prompt 1.4.0 com passthrough de escalar + whitelist de faixa legítima no validador ADR-279, ordering metodológico + caps de display nas 3 superfícies + cap de geração determinístico, e backfill internal_ops com runbook. Apply executado no dogfood via modo latest_batch (aprovado pelo owner após dry-run heurístico achar 0 duplicatas): 165 → 7 Pendentes (5 acionáveis, 0 danger; aceite ≤14 ✓), 158 Superseded soft. Pendência operacional: gate de estabilidade thesis_key ≥90% em 2 runs reais."
tags:
  - type/changelog-entry
  - area/backend
  - area/llm
  - area/produto
  - sprint/a25
---

# Ciclo de vida de sugestões do Parecer — F1–F4 em main

Execução de [[TRACK-a25-suggestion-lifecycle]] ([[PLAN-suggestion-lifecycle]],
[[ADR-290]] flippada para `Decidido (A25)`).

- **F1 (#622):** migration `adr290supersede` (thesis_key + superseded_at/
  by_run_id), `compute_suggestion_thesis_key` na escrita, service
  `suggestion_supersede.py` (B3/B4/B5/B6), telemetria KR4
  (`suggestions_created/superseded/skipped_dismiss/near_dup_candidates`),
  status `Superseded` (B7), docstring do modelo corrigido.
- **F2 (#623):** PROMPT_VERSION 1.4.0 (regras 12 passthrough de escalar +
  13 cap de geração), hints imperativos em `saude_balanco`/
  `independencia_financeira`, manifest 1.4 (invalida cache), whitelist de
  faixa legítima + `money_tokens_total`/`range_in_scalar_count` no
  validador ADR-279, eval determinístico.
- **F3 (#624):** `suggestionOrdering.ts` compartilhado (severidade → gate
  metodológico → sem-valor antes → impacto), InboxTab com cap de 12
  acionáveis + disclosures a11y, cards inline ≤3/seção, "Próximos passos"
  só acionáveis, truncamento determinístico 3/horizonte em
  `finalize_output`.
- **F4 (#626):** `internal_ops/suggestion_backfill.py` (dry-run default,
  workspace obrigatório, audit) + runbook `suggestion_backfill.md`.

**Achado do dry-run dogfood + apply:** 165 pendentes → 0 duplicatas pela
chave `(section_id, título normalizado)` — o LLM re-redige títulos a cada
run, então a heurística aprovada no plano não agrupa nada neste dataset.
Owner aprovou o modo `latest_batch` ("último parecer vence", follow-up
#627): apply executado em 2026-06-12 — 165 → **7 Pendentes (5 acionáveis,
0 danger)**, 158 Superseded (soft; rollback SQL no runbook). Aceite F4
(≤14 acionáveis) cumprido.
