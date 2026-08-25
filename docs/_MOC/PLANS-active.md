---
type: moc
title: PLANS-active — Planos canônicos abertos
aliases: ["PLANS-active", "plans-active"]
---

# PLANS-active — Planos canônicos abertos

> **Editorial curto.** Status, contagens e lanes: [`PLAN_PROGRESS`](_generated/PLAN_PROGRESS.md).

## Olhar primeiro

| Plano | Por que importa agora |
|---|---|
| [`PLAN-launch-trust`](../plan/LAUNCH_TRUST/_README.md) | Três frentes launch-blocking: confiabilidade do número (F1), produção (F2 — **OWNED** desde o closure da A11, absorveu o residual owner-gated do platform-review), Parecer defensável (F3→planner-review). |
| [`PLAN-report-premium`](../plan/REPORT_PREMIUM/_README.md) | Superfície principal de produto. |
| [`PLAN-llm-prompts-hardening`](../plan/LLM_PROMPTS_HARDENING/_README.md) | LGPD/ADR-090/telemetria nos 9 prompts LLM — A17/A18/A20. |
| [`PLAN-data-lineage`](../plan/DATA_LINEAGE/_README.md) | Lineage fim-a-fim (forward+reverso) legível por LLM + fonte plugável (`SourceAdapter`/`SourceRef`) + extração limpa. Gate F0 abre 4 ADR (278-281) + emenda ADR-146; nenhuma lane abre antes de B1–B8. **Sprints A23–A27; corrente A26** (Ondas 0–5 shipped). |
| [`PLAN-suggestion-lifecycle`](../plan/SUGGESTION_LIFECYCLE/_README.md) | Inbox `/acao` com 158 sugestões acumuladas (dogfood): supersede-per-run + `thesis_key` + valores determinísticos no parecer + cap/ordering. Gate F0 abre ADR-290. **Origem A25 (`done`); F1–F4 shipped**, gate de estabilidade thesis_key pendente. |
| [`PLAN-go-shell`](../plan/GO_SHELL/_README.md) | Caminho 1 do [[ADR-150]] (shell Go + Python subprocess). **F0 pré-requisitos ✅ concluída 2026-07-02** (A3.store [[ADR-303]] · A3.cli #737 · otel #738 · benchmark gate PASSA 413ms≤500ms; resta só A3.codegen, ancorado a F1). F1+ (PR Go) segue bloqueada pelos gatilhos da ADR-150 (revisita 2027-Q2 / 100 workspaces). |
| [`PLAN-ledger-integrity`](../plan/LEDGER_INTEGRITY/_README.md) | **`draft`.** Conservação do razão E3/E4 (origem: certificação `ledger-certify` r2, [[LEDGER-CERTIFY-active]]). Owna LC-01 (ledger de contagem, [[ADR-347]] Proposto) + LC-03; **roteia** LC-02 → lane própria `depends_on` A39.l9 (co-autoria ADR-346 step 4b) e LC-04/LC-05 → [[PLAN-data-lineage]]. Prioridade≠ordem: LC-01 1º por estar desbloqueado, LC-02 mais material mas gated. |
| [`PLAN-competitive-pierre`](../plan/COMPETITIVE_PIERRE/_README.md) | [[A43]]: MCP/OAuth read-only para ChatGPT+Codex. |
| [`PLAN-deterministic-authority`](../plan/DETERMINISTIC_AUTHORITY/_README.md) | **`draft`.** Remediação r6: fato > rótulo LLM; destrava o gate da A40. |
| [`PLAN-ci-trust`](../plan/CI_TRUST/_README.md) | 64 bypasses/17d no Ruleset + falso-vermelho de instrumento no gate required + nightly off 72d. Onda 0 = detector pós-merge + ADR de merge-protection. |

## Pausados relevantes

| Plano | Pausado em | Razão |
|---|---|---|
| `PLAN-i18n` | 2026-04-?? | Aguardando produto definir locales prioritários. [plan/I18N/_README.md](../plan/I18N/_README.md). |

## Encerrados

- [`PLATFORM_REVIEW_PLAN-2026-07-08.md`](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) — ✅ `done` 2026-07-08; residual owner-gated → [[PLAN-launch-trust]] §F2.
- [`P1_STRUCTURAL-2026-07-28.md`](../archive/P1_STRUCTURAL-2026-07-28.md) — ✅ 2026-04-17; superseded; arquivado 2026-07-28.
- [`PLAN-cenarios-estresse`](../plan/CENARIOS_ESTRESSE/_README.md) — ✅ `done` 2026-06-29 ([[ADR-168]]); in-place (`id` linkado por A8-4).
- [`PRODUCT_PLAN-2026-04-15.md`](../archive/PRODUCT_PLAN-2026-04-15.md).
- [`CONFIG_CUTOVER_PLAN-2026-04-27.md`](../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md).
- [`GOALS_JSON_CUTOVER_PLAN-2026-05-07.md`](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md).
- [`DOC_REORG_PLAN-2026-05-07.md`](../archive/DOC_REORG_PLAN-2026-05-07.md).

## Convenções

- Status canônico: frontmatter de `plan/<SLUG>/_README.md`.
- Plano novo: crie `docs/plan/<UPPER_SLUG>/_README.md` conforme [`note-plan.schema.json`](../_schemas/note-plan.schema.json) e adicione aqui.
