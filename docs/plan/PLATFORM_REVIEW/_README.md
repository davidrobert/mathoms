---
id: PLAN-platform-review
type: plan
title: Platform Review Plan — 2026-05-06
status: in_progress
created_at: 2026-05-06
last_review: 2026-07-08
sprint_origem: A11
sprint_atual: A11
sprints_envolvidas: [A11]
paused_at: null
pause_reason: null
adrs_canonical: []
tags:
  - type/plan
  - status/in-progress
---

# Platform Review Plan — 2026-05-06

> **Origem:** revisão multi-agente conduzida em 2026-05-06 com 6 especialistas
> (orquestrador `senior-cto` + 5 subagents paralelos: `data-engineer`,
> `financial-planner`, `product-designer`, `sre-devops`, `build-vs-buy`).
> Detalhes em `_scratch/review-2026-05-06/` (gitignored — findings
> individuais + consolidação).
>
> **Total bruto:** 138 findings (DE=22, FP=22, PD=26, SR=28, BB=22, CTO=18).
> **Após dedupe:** ~118 únicos. **Distribuição:** P0=21, P1=51, P2=44, P3=12.
>
> **Não conflita com lanes ativas:** verificado contra `git worktree list` +
> `origin/agent/*` <48h (in-flight: A8.4 cleanup, incremental-globals,
> apendice-b-premissas, fix-plano-decisions-imports).
>
> **Coverage gaps explícitos:** stages E0 (audit/unlock/route),
> E1.5c (consolidate_baseline), E7-crossval e E7-apply ficaram com
> cobertura indireta. Próxima revisão (Q3 2026) prioriza esses stages.
>
> **Modo de closure A11 ([[ADR-228]]):** sprint fecha em modo
> **code-complete** — 32 tasks em `main` + ADRs 170-175 `Decidido`.
> 5 tasks (W3-T02, W4-T01, W4-T02, W4-T03, W4-T05) têm `operational_gate`
> adicional (G1-G5) rastreado em ADR-228, prazo 7d corridos pós-cutover
> `app.mathoms.ai`. Drills operacionais **não bloqueiam** encerramento
> da sprint.

---

## NEXT UP

Tasks com `status=ready` e sem deps. Pegue qualquer uma como pickup imediato.

| ID | Title | Effort | Severity | Owner agent | Why now |
|----|-------|--------|----------|-------------|---------|
| ~~**W1-T01**~~ ✅ | Tokens fantasma + Tailwind classes inexistentes (CSS gate) | M | P0 | product-designer | DONE 2026-05-06 (PR #95) |
| ~~**W1-T02**~~ ✅ | Suggestion regras dormentes — fix XS de FP-001/FP-002/FP-003 | XS | P0 | financial-planner | DONE 2026-05-06 (PR #98) — alias defensivo + adapter + dead rule removida |
| ~~**W1-T03**~~ ✅ | CLAUDE.md inconsistência (parity test path) — sync com realidade | XS | P0 | senior-cto | DONE 2026-05-06 (PR #94) |
| ~~**W1-T04**~~ ✅ | PDF concurrency semaphore (`asyncio.Semaphore(2)`) | XS | P0 | sre-devops | DONE 2026-05-06 (PR #97) — `MATHOMS_PDF_CONCURRENCY=2` + singleton lazy |
| ~~**W1-T05**~~ ✅ | SECRET_KEY fail-fast em prod (model_validator) | XS | P0 | sre-devops | DONE 2026-05-06 (PR #97) — `model_validator` rejeita defaults/sqlite em prod |
| ~~**W1-T06**~~ ✅ | ADR backfill (6 ADRs proposed para SR-002/004/003/007/006/009) | S | P1 | senior-cto | DONE 2026-05-06 (PR #94) — 6 ADRs em status Proposto |
| ~~**W1-T07**~~ ✅ | Endividamento `retorno_esperado_pct_aa` emitido pelo IFProjector | S | P1 | financial-planner | DONE 2026-05-06 (PR #98) — `to_legacy_dict` + carry-trade trigger |
| ~~**W1-T08**~~ ✅ | Schema E5 — declarar `cenarios_conjuge` formal + outros blocos não declarados | S | P1 | data-engineer | DONE 2026-05-06 (PR #96) — bloco formal + 18 outros top-level shallow |

**Wave 1 ✅ entregue · Wave 2 ✅ entregue 2026-05-20** (6/6: PRs [#359](https://github.com/davidrobert/mathoms/pull/359), [#361](https://github.com/davidrobert/mathoms/pull/361), [#344](https://github.com/davidrobert/mathoms/pull/344)+[#346](https://github.com/davidrobert/mathoms/pull/346), [#368](https://github.com/davidrobert/mathoms/pull/368), [#369](https://github.com/davidrobert/mathoms/pull/369), [#367](https://github.com/davidrobert/mathoms/pull/367)) — destrava **Wave 3** (5 tasks P0: refresh tokens, Fernet rotation, LLM budget, email infra, prompt injection defense).

**Próximos pickups ready agora:**

- **W6-T01 residual** (sub-schemas E4 + wire ADR-090) — flip strict shipou via A24.l7 ([[ADR-284]]); split E4 + codegen + wire compliance seguem pickup (wire flip write-side exige ADR `Proposto` antes).
- **W5** — frontend/metodologia; **re-verificação factual concluída 2026-07-08 (spike W5, pós-A33)**: W5-T01 residual entregue 2026-07-08 (scope=col + ProgressBar + reduced-motion; resta só o que acopla com W5-T02/W1-T01), **W5-T02 fechada 2026-07-08** (migração dos 2 charts residuais + emenda [[ADR-139]], [PR #883](https://github.com/davidrobert/mathoms/pull/883)), W5-T03 válida como escrita, W5-T04 parcial (sub-PR #2 obsoleto — [[ADR-239]]/[[ADR-240]]), W5-T05 parcial (numerador `investivel_efetivo` ✅). W5 permanece pickup real nas demais tasks, com escopo reduzido anotado por task (§Wave 5).
- **Owner-gated (não são pickup de agente):** W3-T02 (Resend EU), W4-T02 residual (token Coolify = A20 L4), W4-T01 residual (off-site R2, ADR-228 G2/G3).

> **Reconciliação 2026-07-06** — auditoria factual pós-A28 (sprint `paused` desde
> 2026-05-20; muito do escopo shipou via A20/A21/A24/A27): W3-T01, W3-T04, W4-T04,
> W6-T04, W6-T06 fechados; W6-T03 fechado 2026-07-06 (F9.4); W4-T01, W4-T02, W6-T01 parciais com residual
> anotado; W6-T02 destravado. Statuses do Index abaixo refletem a evidência
> (PR/ADR citados por linha). Residual real da sprint: 3 itens owner-gated +
> W4-T03/W4-T05 (Sentry/status page) + W5 residual + W6-T02/T05/T07.
>
> **Reconciliação 2026-07-08 (sessão de closure A11)** — W6-T02 done 2026-07-06
> ([[ADR-307]], PRs #796/#797); W6-T05 done pós-A11 (A32.l5 tombstone [[ADR-311]] +
> A33.l6 retention+prune [PR #844](https://github.com/davidrobert/mathoms/pull/844);
> residual fora da task: flip `prune_mode=delete` em PR próprio, após dry-run em
> prod); W6-T07 done pós-A11 (A33.l9 [PR #855](https://github.com/davidrobert/mathoms/pull/855),
> [[ADR-285]] `Decidido (A33.l9)`; Frente 2 boy-scout é convenção contínua).
> Residual real da sprint: **5 itens owner-gated** (W3-T02 Resend · W4-T01
> off-site R2 · W4-T02 Coolify · W4-T03 Sentry · W4-T05 status page) +
> **W5 residual** (escopo reduzido por task, ver §Wave 5) + **W6-T01 residual**
> (sub-schemas E4 + wire ADR-090). ADRs do DoD: 170/171/172/173/175 `Decidido`;
> ADR-174 segue `Proposto` (off-site R2 não construído — flip não merecido).

---

## Index

| ID | Title | Wave | Status | Owner | Severity | Effort | Deps |
|----|-------|------|--------|-------|----------|--------|------|
| W1-T01 | Tokens fantasma + CSS gate | 1 | done | product-designer | P0 | M | — |
| W1-T02 | Suggestion regras dormentes (FP-001/2/3) | 1 | done | financial-planner | P0 | XS | — |
| W1-T03 | CLAUDE.md sync (parity test) | 1 | done | senior-cto | P0 | XS | — |
| W1-T04 | PDF concurrency semaphore | 1 | done | sre-devops | P0 | XS | — |
| W1-T05 | SECRET_KEY fail-fast prod | 1 | done | sre-devops | P0 | XS | — |
| W1-T06 | ADR backfill (6 ADRs proposed) | 1 | done | senior-cto | P1 | S | — |
| W1-T07 | Endividamento `retorno_esperado_pct_aa` | 1 | done | financial-planner | P1 | S | — |
| W1-T08 | Schema E5 cenarios_conjuge formal | 1 | done | data-engineer | P1 | S | — |
| W2-T01 | DE-003 PII em pipeline_artifacts (Fernet hooks) | 2 | done | data-engineer | P0 | M | W1-T06 (ADR-170) |
| W2-T02 | SR-001/013 Security headers + CORS strict | 2 | done | sre-devops | P0 | S | W1-T05 |
| W2-T03 | SR-005 CVE + gitleaks + GH secret scanning | 2 | done | sre-devops | P0 | S | — |
| W2-T04 | SR-007 Stuck-runs detector + heartbeat | 2 | done | sre-devops | P0 | S | W1-T06 (ADR-172) |
| W2-T05 | DE-002 + DE-008 extract_with_llm incremental + PROMPT_VERSION | 2 | done | data-engineer | P1 | S | — |
| W2-T06 | DE-009 STAGE_TO_DIR/SUFFIX descriptive aliases | 2 | done | data-engineer | P1 | S | — |
| W3-T01 | SR-006 + DE-013 LLM budget hard-stop + LLMCallLog populada | 3 | done (2026-07-02, [PR #718](https://github.com/davidrobert/mathoms/pull/718)) | data-engineer + sre-devops | P0 | M | W1-T06 (ADR-173) ✅, W2-T05 ✅ |
| W3-T02 | BB-001 + SR-008 Email Resend + verify + password reset | 3 | ready (owner-gated: aprovação Resend EU) | sre-devops | P0 | L | W1-T06 ✅ |
| W3-T03 | SR-002 JWT 15min + refresh 7d + family revocation | 3 | done (2026-06-09, PR #584) | sre-devops + senior-cto | P0 | L | W1-T06 (ADR-170) ✅ |
| W3-T04 | SR-003 Fernet rotation real (MultiFernet) | 3 | done (2026-07-02, [PR #718](https://github.com/davidrobert/mathoms/pull/718)) | sre-devops | P0 | M | W1-T06 (ADR-171) ✅ |
| W3-T05 | SR-009 Prompt injection defense (sanitize + adversarial fixtures) | 3 | shipped | sre-devops + data-engineer | P0 | M | W1-T06 (ADR-175) |
| W4-T01 | SR-004 + BB-007 Off-site backup R2 + restore drill | 4 | parcial — drill dump→restore em CI ✅ (A21.l9, [PR #538](https://github.com/davidrobert/mathoms/pull/538)); off-site R2 segue owner-gated ([[ADR-228]] G2/G3) | sre-devops | P0 | M | — |
| W4-T02 | SR-010 Coolify webhook + SHA-pinned images + dev.9 | 4 | parcial — SHA pinning ✅ (A20.L2, [PR #510](https://github.com/davidrobert/mathoms/pull/510)); Coolify webhook = A20 L4, owner-gated (token) | sre-devops | P0 | M | W2-T03 |
| W4-T03 | SR-011 + BB-015 Sentry SaaS EU + frontend hookup | 4 | blocked | sre-devops | P1 | S | — |
| W4-T04 | SR-018 Rate limit endpoints LLM/upload/pipeline | 4 | done (2026-07-02, [PR #720](https://github.com/davidrobert/mathoms/pull/720) — `services/rate_limit.py` aplicado a upload + pipeline_run) | sre-devops | P1 | M | — |
| W4-T05 | BB-002 + SR-017 + SR-028 Status page + alertas + drill | 4 | blocked | sre-devops | P1 | M | W4-T03 |
| W5-T01 | A11y onda — scope=col + role=progressbar + aria-label charts + reduced-motion | 5 | residual entregue 2026-07-08 — scope=col em todos os `<th>` (default no primitivo TableHead + 23 arquivos literais), primitivo `<ProgressBar/>` + adoções (IFHero, ReservaEmergencia; EquilibrioCerbasi = role="img" por ser distribuição), reduced-motion global; ficam por design: gate axe critical+serious (D1), aria-label dos 2 Recharts (acopla W5-T02), baselines visuais (W1-T01) | product-designer | P1 | S | W1-T01 |
| W5-T02 | PD-004 + BB-011 Recharts → Chart.js residual em S1 | 5 | done (2026-07-08, [PR #883](https://github.com/davidrobert/mathoms/pull/883) — 2 charts migrados p/ `ChartDonut`/`ChartWaterfall` + emenda datada na [[ADR-139]]; dep `recharts` permanece p/ consumidores fora de `/reports/**`) | product-designer | P1 | M | W5-T01 |
| W5-T03 | MonetaryValue migration (PD-006/010/011/012/013) | 5 | válida (pendente) — 18 call-sites do inventário seguem no código + novos fora dele (re-verificado 2026-07-08, spike W5) | product-designer | P1 | M | W1-T01 |
| W5-T04 | FP-004 ADR-161 enrichment (5 sub-PRs paralelos) | 5 | parcial — sub-PR #5 ✅ via W1-T02 (#98); #2 obsoleto (superseded [[ADR-239]]/[[ADR-240]]); #1/#3/#4 válidos (re-verificado 2026-07-08, spike W5) | financial-planner | P1 | L | W1-T07 |
| W5-T05 | FP-010-12-17 Goal IF v2 cutover (3 PRs sequenciais) | 5 | parcial — numerador `investivel_efetivo` + toggle `imoveis_no_if` per-workspace ✅ (#321/#331/#332, ADR-142/222/223); resta `if_meta_liquida` + emissão v2 ([[ADR-140]] segue Roadmap) (re-verificado 2026-07-08, spike W5) | financial-planner | P1 | L | — |
| W6-T01 | DE schema hardening (E5 strict + 7 sub-schemas E4 + ADR-090 wire compliance) | 6 | parcial — flip strict entregue via A24.l7 ([[ADR-284]] + runbook); sub-schemas E4 + wire compliance residual | data-engineer | P1 | L | — |
| W6-T02 | MLOps universal hooks (DE-001/004/008/019 — meta-ADR) | 6 | done (2026-07-06, [[ADR-307]] `Decidido` — [PR #796](https://github.com/davidrobert/mathoms/pull/796) + [PR #797](https://github.com/davidrobert/mathoms/pull/797); nightly de extração LLM = follow-up F2 da ADR) | data-engineer | P1 | L | W3-T01 ✅ |
| W6-T03 | F9.4/F9.5/F9.6 stage rename cleanup + ALLOWED_PREFIXES | 6 | ✅ — F9.5 ✅ (#720); F9.6 código ✅ 2026-07-06 (writers E2/E2-llm/E6-parecer + labels de progresso cortados p/ descritivo; `ALLOWED_PREFIXES` sem `pipeline/stages/` e `scripts/`); F9.4 ✅ 2026-07-06 (rename `scripts/e*.py` → nomes descritivos, 9 módulos; `e2_extract.py` → `extract_bank_documents.py` cobre invoices+statements). Residual fora de escopo: limpeza eventual do `STAGE_RENAME_MAP` (compat reverso CLI/HTTP/DB permanece por design) | data-engineer | P2 | M | — |
| W6-T04 | Doc hygiene (BACKLOG split + CHANGELOG retention + CLAUDE.md slim) | 6 | done ([PR #111](https://github.com/davidrobert/mathoms/pull/111) mergeado) | senior-cto | P2 | M | W1-T03 |
| W6-T05 | DE-017 + DE-010 Pipeline artifacts retention + cascade-on-delete | 6 | done (pós-A11 — A32.l5 tombstone [[ADR-311]] + A33.l6 retention+prune [PR #844](https://github.com/davidrobert/mathoms/pull/844); cascade FK descartado por design; residual fora da task: flip `prune_mode=delete`) | data-engineer | P2 | M | — |
| W6-T06 | CTO-001 ADR-150 decisão (Caminho 1 / rejeitada / adiada) | 6 | done — Caminho 3 via [PR #110](https://github.com/davidrobert/mathoms/pull/110); superado por evento: [[ADR-150]] flip `Decidido` 2026-07-03 (#759, gatilho 4) e F1 entregue (#780→#792) | senior-cto | P1 | S decidir + L se Caminho 1 | — |
| W6-T07 | CTO-015 `services/` taxonomy — split por natureza (ADR-285) + drenagem boy-scout p/ `application/` | 6 | done (pós-A11 — A33.l9 [PR #855](https://github.com/davidrobert/mathoms/pull/855); [[ADR-285]] `Decidido (A33.l9)` + emenda 2026-07-08; Frente 2 boy-scout segue como convenção contínua) | senior-cto | P3 | M | ADR-285 |

---

## Quick Wins

Tasks `effort ∈ {XS, S}`, `severity ∈ {P0, P1}`, `deps=∅`, alto ROI:

- **W1-T02** Suggestion regras dormentes — XS, ativa Perini "300" + Caminho IF + remove dead rule.
- **W1-T03** CLAUDE.md sync — XS, elimina confusão semente.
- **W1-T04** PDF semaphore — XS, previne OOM em prod.
- **W1-T05** SECRET_KEY fail-fast — XS, vulnerability bypass closure.
- **W1-T07** retorno_esperado_pct_aa — S, ativa carry-trade rule (Cerbasi).
- **W1-T08** Schema E5 cenarios_conjuge formal — S, fecha gap ADR-166.

Soma: **6 tasks Quick Wins** desbloqueiam 4 P0 + 2 P1 em <2 dias dev total.

---

## Wave 1 — Hot patches + ADR backfill (Sprint imediato, ~5 dias dev)

> **Goal:** corrigir P0 latentes em main que outros agentes detectaram.
> Estabelecer baseline de ADR coverage para destravar W2+.

### [W1-T01] Tokens fantasma + Tailwind classes — gate validação CSS

- **id:** W1-T01
- **owner_agent:** product-designer
- **deps:** —
- **severity:** P0
- **effort:** M (~1.5 dias)
- **status:** done (2026-05-06, branch `agent/w1t01-css-tokens-gate/20260506-2119`)
- **related_findings:** PD-001, PD-002, PD-005, PD-023
- **paired_doc_task:** W6-T04 (CLAUDE.md §Design System patch propondo aliases)
- **risk:** mudança de CSS global — visual regression baselines podem precisar update.
- **rollback_plan:** revert do PR + revert dos baselines.
- **files_touched:**
  - `design-tokens/tokens.json` (adicionar aliases ou novos tokens)
  - `frontend/src/styles/tokens.css` (regenerado via `design-tokens/build.py`)
  - `frontend/src/components/report/ui/ComparisonItemsBlock.tsx`, `SnapshotChangelogList.tsx`
  - `frontend/src/components/report/sections/{S7IndependenciaSection,PlanoDeAcao/PlanoDeAcaoSection}.tsx`
  - `frontend/src/components/report/cards/Top15AtivosCard.tsx`
  - `frontend/src/app/(app)/plano/_components/{IFHeroCard,PlanoKpiRow}.tsx`
  - `frontend/src/app/(app)/acao/_components/SuggestionCard.tsx`
  - `dev/check_css_var_references.py` (NOVO — gate de validação)
  - `.pre-commit-config.yaml` (hook novo)
- **acceptance_criteria:**
  - [x] `dev/check_css_var_references.py` falha se algum `var(--xxx)` em `frontend/src/**` não existe em `frontend/src/styles/tokens.css`/`globals.css`.
  - [x] Hook pre-commit aplicado.
  - [x] Tokens definidos: `--semantic-danger` (alias para `loss`), `--semantic-success` (alias para `gain`), `--semantic-warning` (alias para `alert`), `--brand-secondary` (alias para `neutral`).
  - [x] Tailwind classes `brand-500/400` substituídas por `[var(--brand-info)]`/`[var(--brand-accent)]`.
  - [ ] Visual baselines atualizadas (cover×2 + S1×2 + /plano×2 = 6 PNGs) — DIFERIDO para W5-T01 (a11y onda).
  - [x] Smoke test Vitest: `<ComparisonItemsBlock items={[{delta_signal: "down"}]}/>` aplica `var(--semantic-danger)` no estilo da célula Δ (em `frontend/tests/components/report/snapshotChangelog.test.tsx`).

### [W1-T02] Suggestion regras dormentes — fix XS

- **id:** W1-T02
- **owner_agent:** financial-planner
- **deps:** —
- **severity:** P0
- **effort:** XS (~3h)
- **status:** done (2026-05-06, combined PR with W1-T07)
- **related_findings:** FP-001, FP-002, FP-003
- **paired_doc_task:** ADR-161 §Follow-ups #1 (Pipeline E5 enrichment) marca FP-001/2/3 ✅
- **files_touched:**
  - `pipeline/domain/services/suggestion_rules.py` (FP-001 alias defensivo + FP-003 remover dead rule)
  - `pipeline/domain/services/pontos_fortes_analyzer.py` (FP-002 ler `goals.if_pct`)
  - `pipeline/domain/services/e5_analyzer_adapter.py` (FP-002 passar `goals={"if_pct": ...}`)
  - `pipeline/domain/types/suggestion.py` (FP-003 remover `dolarizacao_atrasada` de KIND_TO_CATEGORY)
  - `backend/app/models/suggestion.py` (FP-003 sync VALID_SUGGESTION_KINDS + VALID_SUGGESTION_CATEGORIES)
  - `tests/unit/pipeline/test_suggestion_rules.py` + `tests/test_e5_to_suggestion_e2e.py` (NOVOS)
- **acceptance_criteria:**
  - [x] Teste e2e em `tests/test_e5_to_suggestion_e2e.py` usa snapshot real produzido por `build_e5_output` (não mock).
  - [x] Regra `rule_renda_passiva_real_baixa` dispara para workspace fictício com `if_pct≥50`.
  - [x] Pontos fortes "Caminho para IF" aparece para workspace com `if_pct≥20`.
  - [x] `rule_dolarizacao_atrasada` ausente de `ALL_RULES`.
  - [x] ADR-161 §Follow-ups atualizada com este item ✅ (ADR-168 é USA modo removal — ADR canônica das regras é 161).

### [W1-T03] CLAUDE.md sync — parity test inconsistência

- **id:** W1-T03
- **owner_agent:** senior-cto
- **deps:** —
- **severity:** P0
- **effort:** XS (~30min)
- **status:** done (2026-05-06, PR #94)
- **related_findings:** CTO-009, DE-005
- **files_touched:**
  - `CLAUDE.md` (§Code style › Testes — atualizar referência)
- **acceptance_criteria:**
  - [x] Linha 121 não cita `tests/test_e3_main_with_store_parity.py` (deletado em A6c.3).
  - [x] Cita pattern atual: `tests/test_e3_golden_execution.py` + nota explicando que goldens com baseline-snapshot foram descontinuados em A6c.3.
  - [x] Adiciona ponteiro para DE-005 (este plano, W6-T01) — recriação de baselines snapshot é débito explícito.

### [W1-T04] PDF concurrency semaphore

- **id:** W1-T04
- **owner_agent:** sre-devops
- **deps:** —
- **severity:** P0
- **effort:** XS (~1h)
- **status:** done (2026-05-06)
- **related_findings:** BB-009
- **files_touched:**
  - `backend/app/services/pdf_renderer.py` (asyncio.Semaphore + env config)
  - `backend/app/core/config.py` (setting novo `MATHOMS_PDF_CONCURRENCY=2`)
  - `backend/tests/test_pdf_renderer.py` (regression: 5 simultaneous → 2 ativos)
- **acceptance_criteria:**
  - [x] `MATHOMS_PDF_CONCURRENCY` configurável (default 2).
  - [x] Teste valida que 5 chamadas simultâneas a `render_pdf` resultam em max 2 ativos via Semaphore.
  - [x] Comentário em pdf_renderer.py linha 14-16 atualizado para refletir implementação.

### [W1-T05] SECRET_KEY fail-fast em prod

- **id:** W1-T05
- **owner_agent:** sre-devops
- **deps:** —
- **severity:** P0
- **effort:** XS (~1h)
- **status:** done (2026-05-06)
- **related_findings:** SR-022, SR-021
- **files_touched:**
  - `backend/app/core/config.py` (`@model_validator(mode="after")`)
  - `backend/tests/test_config_prod_gates.py` (NOVO — testa que prod rejeita defaults)
- **acceptance_criteria:**
  - [x] `Settings(ENVIRONMENT="production", SECRET_KEY="dev-secret-key-change-in-production")` levanta `RuntimeError`.
  - [x] `Settings(ENVIRONMENT="production", SECRET_KEY="x"*16)` levanta `RuntimeError` (< 32 chars).
  - [x] `Settings(ENVIRONMENT="production", DATABASE_URL="sqlite+aiosqlite:///mathoms.db")` levanta `RuntimeError`.
  - [x] Dev defaults continuam funcionando.

### [W1-T06] ADR backfill (6 ADRs proposed)

- **id:** W1-T06
- **owner_agent:** senior-cto
- **deps:** —
- **severity:** P1
- **effort:** S (~3-4h)
- **status:** done (2026-05-06, PR #94)
- **related_findings:** CTO-004, CTO-013
- **files_touched:**
  - `docs/DECISIONS.md` (6 ADRs novas: ADR-170 a ADR-175)
- **acceptance_criteria:**
  - [x] **ADR-170** Refresh tokens (HS256 + httpOnly cookie + family revocation) — para fechar SR-002.
  - [x] **ADR-171** Fernet rotation operacionalização (MultiFernet) — para fechar SR-003.
  - [x] **ADR-172** Stuck-runs detector + last_heartbeat_at — para fechar SR-007.
  - [x] **ADR-173** LLM budget enforce + LLMCallLog populada — para fechar SR-006/DE-013.
  - [x] **ADR-174** Off-site backup com R2 + restore drill — para fechar SR-004/BB-007.
  - [x] **ADR-175** Prompt injection defense camadas — para fechar SR-009.
  - [x] Cada ADR status `Proposto` com link para finding original.
  - [x] CLAUDE.md §"ADRs → docs/DECISIONS.md" recebe parágrafo explicando "ADR Proposto antes de PR de implementação P0/P1".
  - [x] `python3 dev/build_adr_toc.py --inline` regenerado.
  - [x] `python3 dev/check_adr_anchors.py` + `validate_adr_format.py` verdes.

### [W1-T07] Endividamento `retorno_esperado_pct_aa`

- **id:** W1-T07
- **owner_agent:** financial-planner
- **deps:** —
- **severity:** P1
- **effort:** S (~4h)
- **status:** done (2026-05-06, combined PR with W1-T02)
- **related_findings:** FP-009
- **files_touched:**
  - `pipeline/domain/services/if_projector.py` (`to_legacy_dict` adiciona retorno_esperado_pct_aa + campo dataclass)
  - `pipeline/domain/services/suggestion_rules.py` (FP-009 — `CARRY_TRADE_MARGIN_PP=1.0` constante + comparar custo > retorno + 1pp)
  - `tests/unit/pipeline/test_suggestion_rules.py` + `tests/test_e5_to_suggestion_e2e.py` (regression e2e)
- **acceptance_criteria:**
  - [x] `IFProjection.to_legacy_dict()` emite `retorno_esperado_pct_aa: float` (== `IFProjectorConfig.retorno_real_anual_pct`; alinhamento com retorno ponderado da carteira fica para FP-004).
  - [x] Trigger carry-trade do `rule_endividamento_perigoso` dispara em snapshot real.
  - [x] Teste e2e com cenário: dívida 25%a.a. + retorno_esperado 12% → regra dispara.

### [W1-T08] Schema E5 cenarios_conjuge + outros blocos formais

- **id:** W1-T08
- **owner_agent:** data-engineer
- **deps:** —
- **severity:** P1
- **effort:** S (~6h)
- **status:** done
- **related_findings:** DE-006 (parcial — só cenarios_conjuge nesta task), ADR-166
- **files_touched:**
  - `config/schemas/e5_analysis.schema.json` (declarar `cenarios_conjuge`, outros blocos top-level)
  - `tests/test_schema_validation.py` (test positivo + test negativo)
- **acceptance_criteria:**
  - [x] `e5_analysis.schema.json` declara `cenarios_conjuge` formal (matching ADR-166 + Pydantic em `cenarios_conjuge_analyzer.py`).
  - [x] Schema valida payload real produzido por `build_e5_output`.
  - [x] Test negativo: payload sem `cenarios_conjuge` quando esperado → falha validation em `strict` mode.

---

## Wave 2 — Pipeline + DB hardening (Sprint +1, ~7 dias dev) ✅ entregue 2026-05-20

> **Goal:** Fechar P0 de pipeline (PII, stuck runs) e gates de CI (security
> headers, CVE scan). Wave 2 só inicia após **todas as P0 da Wave 1**
> mergearem em main (`wave_gate: w1_p0_done`).
>
> **Status:** ✅ 6/6 tasks ([[ADR-231]] · [[ADR-232]] · [[ADR-230]] · [[ADR-172]] · [[ADR-233]] · W2-T06) — destrava Wave 3.

### [W2-T01] DE-003 PII em pipeline_artifacts (Fernet hooks)

- **deps:** W1-T06 ([[ADR-170]] ✅ + sub-ADR [[ADR-231]] para PII storage encryption)
- **owner:** data-engineer (consultar sre-devops em vault.py)
- **severity:** P0 · **effort:** M
- **status:** done (2026-05-20, [PR #359](https://github.com/davidrobert/mathoms/pull/359)) — [[ADR-231]] `Decidido (Sprint A11.W2)`
- **related_findings:** DE-003
- **files_touched:** `backend/app/services/crypto.py` (NOVO), `backend/app/services/db_artifact_store.py`, `backend/app/core/config.py`, `dev/migrate_encrypt_existing_artifacts.py` (NOVO), `docs/adr/231-pii-encryption-pipeline-artifacts.md` (NOVO), 3 test files (`test_crypto_artifact.py`, `test_db_artifact_store_pii_encryption.py`, `test_migrate_encrypt_existing_artifacts.py`).
- **acceptance_criteria:**
  - [x] content_json em todos os stages (write-all-by-default) escreve sentinel `{"_encrypted": true, "v": 1, "kid": "<sha256[:8]>", "ct": "<base64>"}`; read decrypts.
  - [x] Backfill migration idempotente (`dev/migrate_encrypt_existing_artifacts.py` com --dry-run default, batch 500 + cursor).
  - [x] `kid` (key fingerprint) destrava W3-T04 progress tracking sem decrypt-probe.
  - [x] Kill switch `MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS` (default True); read sempre decripta sentinel (compat revert).
  - [x] Schema validation roda **antes** de encrypt (preserva ADR-212 PR3 contract).
  - [x] Auth portability (ADR-109) intacta — `backend/tests/test_auth_portability.py` verde.
- **risk:** chave Fernet rotation pendente (W3-T04) — coordenar timing.
- **rollback_plan:** flag `MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS=false` força no-op em writes novos; reads continuam decriptando histórico (one-way rollback documentado em ADR-231 §D4).

### [W2-T02] SR-001/013 Security headers + CORS strict

- **deps:** W1-T05
- **owner:** sre-devops · **severity:** P0 · **effort:** S
- **status:** done (2026-05-20, [PR #361](https://github.com/davidrobert/mathoms/pull/361)) — [[ADR-232]] `Decidido (Sprint A11.W2)`
- **related_findings:** SR-001, SR-013
- **files_touched:** `backend/app/middleware/security_headers.py` (NOVO), `backend/app/api/csp_report.py` (NOVO), `backend/app/main.py`, `backend/tests/test_security_headers.py` (NOVO), `backend/tests/test_csp_report.py` (NOVO), `docs/adr/232-security-headers-cors-strict.md` (NOVO).
- **acceptance_criteria:**
  - [x] CSP report-only ativo com `report-uri` apontando `${API_PREFIX}/csp-report`.
  - [x] HSTS `max-age=31536000; includeSubDomains` em toda resposta.
  - [x] X-Frame-Options `DENY`, X-Content-Type-Options `nosniff`, Referrer-Policy `strict-origin-when-cross-origin`.
  - [x] Permissions-Policy nega accelerometer/camera/geolocation/gyroscope/magnetometer/microphone/payment/usb.
  - [x] CORS `allow_methods` + `allow_headers` whitelist explícita (sem wildcards) — `expose_headers=["X-Trace-Id"]`, `max_age=600`.
  - [x] Endpoint `POST /v1/csp-report` com payload cap 8KB + log estruturado.
  - [x] Headers presentes em respostas 2xx/4xx/5xx (`setdefault` preserva overrides explícitos por router).

### [W2-T03] SR-005 CVE + gitleaks + GH secret scanning

- **deps:** —
- **owner:** sre-devops · **severity:** P0 · **effort:** S
- **status:** done (2026-05-20, [PR #344](https://github.com/davidrobert/mathoms/pull/344) + [PR #346](https://github.com/davidrobert/mathoms/pull/346)) — [[ADR-230]] Decidido (Sprint A11.W2)
- **related_findings:** SR-005, SR-019
- **files_touched:** `.github/workflows/security.yml` (NOVO), `.pre-commit-config.yaml` (hook gitleaks), `.gitleaks.toml` (NOVO), `docs/reference/runbooks/security_gates.md` (NOVO), `docs/adr/230-security-gates-ci.md` (NOVO)
- **acceptance_criteria:**
  - [x] Trivy filesystem-scan bloqueia HIGH/CRITICAL ([[ADR-230]] §D2; image-scan diferido para W4-T02).
  - [x] Trivy IaC config-scan (Dockerfile + compose + workflows) bloqueia HIGH/CRITICAL.
  - [x] pip-audit roda em `backend/requirements.txt` + `requirements.txt`.
  - [x] npm audit roda em `frontend/` com HIGH+ blocking (prod) e informativo (dev).
  - [x] gitleaks no pre-commit + workflow (`--log-opts="--all"`) com allowlist `.gitleaks.toml`.
  - [x] GH secret scanning habilitado via runbook — instruções `gh api -X PUT repos/davidrobert/mathoms/secret-scanning --field enabled=true` em `docs/reference/runbooks/security_gates.md` §"GitHub Secret Scanning"; passo manual do owner (estado não declarativo no repo); não bloqueia closure (rastreado como item de runbook).
  - [x] Schedule semanal sábado 03:00 UTC abre Issue label `security` em failure.
  - [x] SLO documentado: CRITICAL ≤72h, HIGH ≤14d ([[ADR-230]] §D5).
  - [x] Runbook `docs/reference/runbooks/security_gates.md` cobre triagem + override + push-protection follow-up.

### [W2-T04] SR-007 Stuck-runs detector + last_heartbeat_at

- **deps:** W1-T06 (ADR-172)
- **owner:** sre-devops · **severity:** P0 · **effort:** S
- **related_findings:** SR-007
- **files_touched:** `backend/alembic/versions/<NOVO>_pipeline_runs_heartbeat.py`, `backend/app/models/pipeline_run.py`, `backend/app/tasks/pipeline_task.py`, `backend/app/tasks/celery_beat_schedule.py`
- **acceptance_criteria:** PipelineRun ganha `last_heartbeat_at`; stage start atualiza; beat task `fin.detect_stuck_runs` (5min) marca runs órfãs como `failed` com `failure_reason=heartbeat_timeout` + Notification + métrica.

### [W2-T05] DE-002 + DE-008 extract_with_llm incremental + PROMPT_VERSION

- **deps:** —
- **owner:** data-engineer · **severity:** P1 · **effort:** S (escopo reduzido)
- **related_findings:** DE-002, DE-008
- **files_touched:** `pipeline/stages/extract_with_llm.py`, `pipeline/llm/schemas/{e1_members,e15_baseline,e2_llm}.py`, `dev/check_prompt_version_bumped.py` (NOVO)
- **acceptance_criteria:** extract_with_llm respeita ctx.incremental; 4 prompts LLM (e1_members, e15_baseline, e2_llm, parecer_planejador) declaram PROMPT_VERSION; gate CI falha se diff em prompt sem bump.
- **escopo_alterado:** 2026-05-13 — `review_finances` removido do escopo (será substituído pelo stage `parecer_planejador` em [PLANNER_REVIEW](../PLANNER_REVIEW/_README.md) Ato 4); `e7_review.py` schema deprecated junto. PROMPT_VERSION gate e `extract_with_llm` incremental permanecem (W3-T01 LLMCallLog continua usando esse gate).
- **delivered:** 2026-05-20 — [[ADR-233]] Proposto (formato canônico semver puro + tolerância para `<slug>-v<semver>` legado); `pipeline/stages/extract_with_llm.py` aplica `filter_to_incremental` após `_find_unprocessed_docs`; `prompt_version` propagado no payload dos 3 stages (extract_members, extract_baseline, extract_with_llm); 3 prompts (`e1_members`, `e15_baseline`, `e2_llm`) declaram `PROMPT_VERSION = "1.0.0"`; gate `dev/check_prompt_version_bumped.py` + hook pre-commit operacional (auto-detecta arquivos em `pipeline/llm/prompts/` e `pipeline/llm/schemas/` com a constante). Testes em `tests/pipeline/test_extract_with_llm_incremental.py` + `tests/dev/test_check_prompt_version_bumped.py` (6 + 25 casos).

### [W2-T06] DE-009 STAGE_TO_DIR/SUFFIX descriptive aliases

- **deps:** —
- **owner:** data-engineer · **severity:** P1 · **effort:** S
- **status:** done — 9 aliases descritivos (`extract_members`, `extract_baseline`, `consolidate_baseline`, `extract_invoices`, `extract_statements`, `extract_with_llm`, `reconcile_transactions`) + par `E2-informe-aluguel`/`extract_informe_aluguel` (sufixo novo `-2_informe_aluguel.json`) adicionados em `_STAGE_TO_SUFFIX`. Teste `test_legacy_descriptive_parity` itera `STAGE_RENAME_MAP.items()` e valida sufixo idêntico para legacy + descritivo (skip documentado: `E0-unlock`/`E0-route` sem artifact, `E1.6` nasceu descritivo via ADR-157). `_STAGE_TO_DIR` fora de escopo — foi deletado em ADR-213.
- **related_findings:** DE-009
- **files_touched:** `pipeline/artifact_store.py`, `tests/unit/pipeline/test_artifact_stores.py`, `CLAUDE.md` (tabela §Convenções de naming).
- **acceptance_criteria:** ✅ `_STAGE_TO_SUFFIX` cobre todos os pares de `STAGE_RENAME_MAP` com artifact; teste itera `STAGE_RENAME_MAP` e valida paridade; consumers (`e3_reconciler_adapter`, `e4_categorizer_adapter`, `e3_serialization.generate_legacy_filename`) podem chamar `stage_suffix(descritivo)` sem `KeyError`.

---

## Wave 3 — Auth + LLM ops + Email (Sprint +2, ~12 dias dev)

> **Goal:** Fechar dependências externas críticas (email + Sentry — buy
> decisions) + auth completo + LLM budget. Wave 3 só inicia após Wave 2
> mergeada (`wave_gate: w2_done`). **Status:** ☐ ready (w2_done ✅ 2026-05-20).

### [W3-T01] SR-006 + DE-013 LLM budget hard-stop + LLMCallLog populada

- **deps:** W1-T06 (ADR-173), W2-T05
- **owner:** data-engineer + sre-devops
- **severity:** P0 · **effort:** M
- **files_touched:** `pipeline/llm/litellm_client.py` (hook + budget check), `backend/app/services/llm_budget_service.py` (NOVO), `backend/app/repositories/llm_call_log_repository.py`
- **acceptance_criteria:** toda chamada LLM persiste LLMCallLog; pre-call check budget vs `monthly_llm_budget_usd`; soft-warn 80%, hard-stop 110%; cache 60s Redis para query.

### [W3-T02] BB-001 + SR-008 Email Resend + verify + password reset

- **deps:** W1-T06, build-vs-buy approval (Resend EU)
- **owner:** sre-devops
- **severity:** P0 · **effort:** L
- **files_touched:** `backend/app/services/email/__init__.py` (Protocol + adapters), `backend/app/api/auth.py` (endpoints novos), `backend/app/models/email_verification_token.py`, `backend/app/models/password_reset_token.py`, migrations Alembic
- **acceptance_criteria:** Resend integrado com SPF/DKIM/DMARC; signup envia email-verify; `/auth/forgot-password` + `/auth/reset-password`; rate limit 5/h por IP; templates de email em PT-BR.
- **operational_gate (G1, [[ADR-228]]):** verify SPF/DKIM/DMARC nos DNS de `mathoms.ai` em produção + email-canary chegando em 3 provedores (Gmail/Outlook/iCloud) sem spam. Rastreado em ADR-228, não bloqueia closure code-complete da Sprint A11.

### [W3-T03] SR-002 JWT 15min + refresh 7d + family revocation

- **deps:** W1-T06 (ADR-170)
- **owner:** sre-devops + senior-cto
- **severity:** P0 · **effort:** L
- **status:** done (2026-06-09, [PR #584](https://github.com/davidrobert/mathoms/pull/584)) — [[ADR-170]] `Decidido (Sprint A11.W3)` com seção de emendas (payload mantém `{sub, exp, tv}` — ADR-109; cookie path `/api/v1/auth`; teto absoluto 30d; grace window 60s; CSRF via header custom; `token_version_at_issue` faz tv bump revogar a família). Flag `MATHOMS_AUTH_REFRESH_FLOW` default off; access em memória ficou como débito registrado na ADR. Changelog: `docs/sprint/A11/changelog/CHG-2026-06-09-FEAT-AUTH-REFRESH-TOKENS.md`.
- **files_touched:** `backend/app/core/security.py` (intacto — payload preservado), `backend/app/api/auth.py`, `backend/app/models/refresh_token_family.py`, `backend/app/services/refresh_token_service.py` (hoje `backend/app/application/auth/refresh_session.py`, Frente 2 [[ADR-285]]) + `refresh_rate_limit.py`, `frontend/src/lib/api/core.ts` interceptor 401
- **acceptance_criteria:** access 15min payload mínimo; refresh 7d httpOnly cookie + Secure + SameSite=Lax; family-based revocation; reuse detection invalida família; frontend interceptor 401 → refresh transparente; backward-compat por 1 release com flag.

### [W3-T04] SR-003 Fernet rotation real (MultiFernet)

- **deps:** W1-T06 (ADR-171)
- **owner:** sre-devops
- **severity:** P0 · **effort:** M
- **files_touched:** `backend/app/services/vault.py`, `backend/app/tasks/rotate_fernet_secrets.py` (NOVO), `docs/reference/runbooks/fernet_rotation.md` (NOVO)
- **acceptance_criteria:** MultiFernet aceita `MATHOMS_FERNET_KEYS=new,old`; Celery task re-encripta secrets; runbook documenta procedure passo-a-passo; staging rotation drill.

### [W3-T05] SR-009 Prompt injection defense

> **✅ Shipped em A21.l6** (federada por [[PLAN-launch-trust]] §F3-O3 — lanes
> [[A21.l5]] decidiu [[ADR-175]] + [[A21.l6]] implementou). 4 camadas no
> choke-point único `LLMService.call` + reconciliação `parecer_distiller`.
> Layer 3 (strict schema) tem **finding de audit** registrado em [[A21.l6]]:
> só 2/10 schemas usam `extra="forbid"` — flip dos 3 `allow` é follow-up.

- **deps:** W1-T06 (ADR-175)
- **owner:** sre-devops + data-engineer
- **severity:** P0 · **effort:** M
- **files_touched:** `pipeline/llm/litellm_client.py`, `pipeline/llm/prompts/_sanitization.py` (NOVO), `tests/test_prompt_injection_defense.py` (NOVO), `backend/app/services/parecer_distiller.py`
- **acceptance_criteria:** strip de unicode invisível, ANSI, padrões prompt-leak; system prompt clausula explícita; allowlist Pydantic strict; regression test adversarial determinístico; telemetria `mathoms.llm.input_sanitized`.

---

## Wave 4 — Production readiness (Sprint +3, ~10 dias dev)

> **Goal:** dev → prod cutover (`dev.mathoms.ai` ✅ → `app./api.mathoms.ai`).
> Wave 4 só inicia após Wave 3 mergeada + W4-T01 backup off-site
> validado em drill.

### [W4-T01] SR-004 + BB-007 Off-site backup R2 + restore drill

- **deps:** W1-T06 (ADR-174)
- **severity:** P0 · **effort:** M · **owner:** sre-devops
- **files_touched:** `dev/backup_postgres.sh` (NOVO), `dev/restore_drill.sh` (NOVO), `backend/app/services/storage/r2_adapter.py` (NOVO), `docs/reference/runbooks/disaster_recovery.md` (NOVO)
- **acceptance_criteria:** cron daily pg_dump → gpg encrypt → R2 (eu-central); 5 query-canário em restore drill; RPO=24h documentado; staging drill executado e registrado em RUNBOOK §4.
- **operational_gate (G2, [[ADR-228]]):** restore drill **em produção** (pg_dump real → R2 → reconstrução de DB → 5 queries-canário com row counts esperados); RPO/RTO medidos pós-go-live. Rastreado em ADR-228; staging drill da acceptance_criteria não substitui o gate operacional.

### [W4-T02] SR-010 Coolify webhook + SHA-pinned + dev.9

- **deps:** W2-T03
- **severity:** P0 · **effort:** M · **owner:** sre-devops
- **files_touched:** `.github/workflows/deploy.yml` (NOVO build-and-push GHCR), `docker-compose.prod.yml` (referenciar SHA tags), `docs/reference/runbooks/coolify_deploy.md` (NOVO)
- **acceptance_criteria:** GHCR push tag `sha-<commit>`; Coolify webhook em main após CI verde; smoke remoto pós-deploy com curl /health; rollback automático se falha.
- **operational_gate (G3, [[ADR-228]]):** webhook real disparando em push pra `main` → imagem SHA-pinned sobe em `app.mathoms.ai` → `/health` responde 200 → rollback automático provado com falha sintética. Rastreado em ADR-228, depende de cutover prod.

### [W4-T03] SR-011 + BB-015 Sentry SaaS EU + frontend hookup

- **deps:** —
- **severity:** P1 · **effort:** S · **owner:** sre-devops
- **files_touched:** `backend/requirements.txt` (sentry-sdk), `backend/app/core/sentry.py` (NOVO), `frontend/sentry.client.config.ts` (NOVO), `backend/app/components/ErrorBoundary.tsx` (hookup)
- **acceptance_criteria:** Sentry EU region; before_send hook strip PII (compatível com `_redact()` ADR-110); SDK em backend + frontend + Celery; release tracking via SHA; alert rule >2x burn rate.
- **operational_gate (G4, [[ADR-228]]):** erro canário intencional (`raise RuntimeError("sentry-canary")`) chegando no projeto Sentry EU **em produção** com PII strippado + alert disparando em Slack/oncall. Rastreado em ADR-228, depende de tráfego prod.

### [W4-T04] SR-018 Rate limit endpoints LLM/upload/pipeline

- **deps:** —
- **severity:** P1 · **effort:** M · **owner:** sre-devops
- **files_touched:** `backend/app/services/rate_limit.py` (NOVO), decorators em routers `/upload`, `/pipeline/start`, `/reports/.../regenerate-summaries`, `/auth/login`
- **acceptance_criteria:** Redis SET NX + TTL pattern; limits configuráveis por endpoint; testes unitários + integration; falha aberta documentada.

### [W4-T05] BB-002 + SR-017 + SR-028 Status page + alertas + drill

- **deps:** W4-T03
- **severity:** P1 · **effort:** M · **owner:** sre-devops
- **files_touched:** Instatus signup + status.mathoms.ai DNS, `docs/reference/runbooks/alerts/<N>.md` (NOVO), UptimeRobot setup
- **acceptance_criteria:** UptimeRobot 5min /health; Instatus free com 3 services (api, app, ops); Sentry alertas wired com burn rate rules; drill incidente executado e registrado.
- **operational_gate (G5, [[ADR-228]]):** drill full-chain em produção — UptimeRobot detecta down sintético → Instatus atualiza status → oncall recebe page → postmortem rascunho em ≤24h. Rastreado em ADR-228, depende de prod pública.

---

## Wave 5 — Frontend + Methodology (Sprint +4, ~10 dias dev)

> **Goal:** UX polish, a11y compliance, metodologia financeira completa.
> Wave 5 paraleliza com Wave 6 — depende só de Wave 1.

### [W5-T01] A11y onda — scope=col + role=progressbar + aria-label charts + reduced-motion

- **deps:** W1-T01
- **severity:** P1 · **effort:** S · **owner:** product-designer
- **status:** scoped — track histórico `agent_prompts/track_w5t01_a11y.md`
- **files_touched:** 13 arquivos com `<th>`, IFHeroCard, EquilibrioCerbasiCard, Kpi, charts Recharts, globals.css
- **related_findings:** PD-007, PD-014, PD-015, PD-021
- **acceptance_criteria:** axe-core sobe para `moderate` em a11y.@critical.spec.ts e mantém verde; primitivo `<ProgressBar/>` extraído.

> **Re-verificação factual 2026-07-08 (spike W5, pós-A33): PARCIAL.**
> Coberto por outras entregas: `aria-label` de charts entregue para os
> migrados a Chart.js na Onda v2.E ([[ADR-139]] — primitivo `ChartCanvas`
> emite `role="img"` + `aria-label`), fechando 3 dos 5 charts do inventário
> (ReceitaDespesaMensal, ReceitaBar, DespesasDoughnut) + FluxoMensal;
> `role="progressbar"` já existia em ReservaEmergenciaCard (lote A,
> pré-plano); cards novos nascem com `scope="col"` (ProventosYieldCard,
> CoberturaSegurosCard). Resta (verificado no código): `scope="col"` em
> **0/13** arquivos do inventário do track; `role="progressbar"` ausente em
> IFHeroCard/EquilibrioCerbasiCard/Kpi e primitivo `<ProgressBar/>`
> inexistente; `prefers-reduced-motion` ausente em `globals.css`
> (`.animate-indeterminate` sem media query); gate axe segue
> `critical+serious` (decisão D1 em `tests/e2e/helpers/axe.ts`) — flip para
> +`moderate` pendente; `aria-label` dos 2 Recharts residuais acopla com
> W5-T02. Baselines visuais diferidas de W1-T01 (6 PNGs) seguem pendentes aqui.

> **Residual entregue 2026-07-08 (sessão de closure A11).** `scope="col"`
> em todos os cabeçalhos de coluna: default no primitivo `TableHead`
> (`ui/table.tsx`, antes do spread — override possível) + 23 arquivos com
> `<th>` literal; `scope="row"` pré-existente preservado
> (CoberturaSegurosCard). Primitivo `<ProgressBar/>` criado em
> `ui/ProgressBar.tsx` (role="progressbar", aria-valuenow/min/max com
> clamp, `ariaLabel` obrigatório) e adotado em IFHeroCard +
> ReservaEmergenciaCard (site do padrão de referência, dedupado);
> EquilibrioCerbasiCard é distribuição empilhada presente/futuro — não
> progresso rumo a alvo — então recebeu `role="img"` + aria-label
> descritivo; microbars de `Kpi.tsx` mantidos `aria-hidden` (decorativos,
> valor textual adjacente). `prefers-reduced-motion: reduce` global em
> `globals.css` (0.01ms + 1 iteração — `animationend` dispara e skeleton/
> indeterminate permanecem visíveis estáticos). **Segue pendente por
> design:** gate axe mantido `critical+serious` (D1 não reaberta);
> `aria-label` dos 2 Recharts residuais acopla com W5-T02; baselines
> visuais (6 PNGs) seguem diferidas de W1-T01.

### [W5-T02] PD-004 + BB-011 Recharts → Chart.js residual S1

- **deps:** W5-T01
- **severity:** P1 · **effort:** M · **owner:** product-designer
- **files_touched:** `frontend/src/components/report/charts/{PatrimonioDoughnutChart,WaterfallIfChart}.tsx`
- **acceptance_criteria:** ambos migram para `<ChartDonut>`/`<ChartWaterfall>` primitives Chart.js; aria-label declarados; baselines visuais atualizados; bundle size -150kb confirmado.

> **Re-verificação factual 2026-07-08 (spike W5, pós-A33): VÁLIDA como escrita.**
> `PatrimonioDoughnutChart.tsx` e `WaterfallIfChart.tsx` seguem importando
> `recharts` (dep `recharts@^3.8` viva no `package.json`); primitives
> `ChartDonut`/`ChartWaterfall` existem desde ADR-117 (pré-plano) — o custo
> residual é só a migração dos 2 componentes de S1. **Correção factual vs
> Trade-off 1:** [[ADR-139]] já flippou `Decidido (Onda v2.E concluída)` em
> 2026-04-26 e lista estes 2 charts como fora de escopo intencional
> ("pode virar v2.E.9") — o fechamento desta task deve entrar como **emenda
> datada** na ADR-139, não como novo flip de status.

> **FECHADA 2026-07-08 ([PR #883](https://github.com/davidrobert/mathoms/pull/883)).** Ambos os charts migraram para
> `ChartDonut`/`ChartWaterfall` com `aria-label` descritivo (via
> `ChartCanvas` `role="img"`); emenda datada registrada na [[ADR-139]]
> (§"Emenda — fechamento do resíduo v2.E.9"); `.recharts-wrapper` removido
> do `report-print.css` e helpers Recharts órfãos de `charts/_shared.ts`.
> **Escopo ajustado vs acceptance original:** bundle -150kb NÃO se
> materializa neste PR — `recharts` permanece no `package.json` para os 5
> consumidores fora do relatório (`Mathom{Area,Bar,Pie}Chart` +
> `plano/_dashboard/{Pie,Bar}ChartCard`, ADR-037); remoção da dep é escopo
> futuro. Baselines visuais S1 regeneradas via workflow_dispatch no runner
> Linux (procedimento TESTING.md §visual regression).

### [W5-T03] MonetaryValue migration

- **deps:** W1-T01
- **severity:** P1 · **effort:** M · **owner:** product-designer
- **status:** scoped — track histórico `agent_prompts/track_w5t03_monetary_value.md`. Inventário concreto: 9 wrappers monetários + 9 toLocaleString = 18 call-sites (excede estimativa de 11).
- **files_touched:** 11+ cards/components (Endividamento, Reserva, IRPF×4, EstrategiaAporte, SupportGoalsRow, KPICard etc.)
- **related_findings:** PD-006, PD-010, PD-011, PD-012, PD-013
- **acceptance_criteria:** todos consomem `<MonetaryValue size="kpi"/>`; sem `font-mono text-Xxl tabular-nums` redundante; sem `toLocaleString()` direto em strings monetárias; `formatCurrency()` usado quando precisa string.

> **Re-verificação factual 2026-07-08 (spike W5, pós-A33): VÁLIDA como escrita.**
> Os 18 call-sites do inventário do track (9 wrappers `font-mono …
> tabular-nums` + 9 `toLocaleString` monetários) **seguem presentes** no
> código (drift de linhas; `CategoriesTab.tsx` virou
> `config/_categories/CategoryRow.tsx`). Nenhuma sprint recente cobriu o
> escopo. Código novo já adota o alvo (`size="kpi"` em HeroGapProtecaoCard,
> AlocacaoAtualVsAlvoCard) e surgiram **novos** call-sites monetários com
> `toLocaleString` fora do inventário (ProtectionList, InferredRisksCard,
> StressScenarioCard) — re-inventariar no pickup.

### [W5-T04] FP-004 ADR-161 enrichment (5 sub-PRs)

- **deps:** W1-T07
- **severity:** P1 · **effort:** L (~7-10 dias paralelizáveis) · **owner:** financial-planner
- **status:** scoped — track histórico `agent_prompts/track_w5t04_adr161_enrichment.md`. Sub-PR #5 (renda_passiva_real_baixa) recomendado primeiro como gate de validação; #2 (seguros) maior valor para usuário final mas custo alto (paralelizar em background).
- **files_touched:** `pipeline/domain/services/{cash_flow_builder,instituicoes_por_membro_analyzer,fluxo_caixa_enricher}.py`, novo `WorkspaceInsurance` model + migration + endpoints, `MarketRate` IPCA reader
- **acceptance_criteria:** 5 regras dormentes (`taxa_poupanca_caindo`, `seguros_insuficientes`, `concentracao_instituicao`, `lifestyle_creep`, `renda_passiva_real_baixa`) disparam em snapshot real; teste e2e em `tests/test_e5_to_suggestion_e2e.py`.

> **Re-verificação factual 2026-07-08 (spike W5, pós-A33): PARCIAL** (1 de 5
> regras ativa; sub-PR #2 com premissa obsoleta).
>
> - **Sub-PR #5 (`renda_passiva_real_baixa`) — essencial JÁ ENTREGUE** via
>   W1-T02 ([PR #98](https://github.com/davidrobert/mathoms/pull/98)): regra
>   dispara com snapshot real (`renda_passiva_mensal_observada_brl` emitido
>   por `e5_serialization`; coberto em `tests/test_e5_to_suggestion_e2e.py`).
>   Resta só o gate e2e full-pipeline (E1.6+E5) descrito no track.
> - **Sub-PRs #1/#3/#4 — VÁLIDOS:** `taxa_poupanca_trimestral_historico`,
>   `patrimonio.por_instituicao` (valores BRL; hoje só lista de nomes em
>   `instituicoes_por_membro`) e `inflacao.acumulada_pct_no_periodo` + IPCA
>   reader seguem ausentes do E5 (grep 2026-07-08: campos só aparecem em
>   `suggestion_rules.py`); as 3 regras seguem dormentes.
> - **Sub-PR #2 (WorkspaceInsurance) — OBSOLETO na premissa:** dados de
>   seguro passaram a vir de apólices extraídas de documentos
>   ([[ADR-239]]/[[ADR-240]] — card S_PROTECAO entregue em A19.l1, PRs
>   #430–#436; ativação end-to-end em A28.l6,
>   [PR #783](https://github.com/davidrobert/mathoms/pull/783)). O gap "alta
>   renda sem cobertura vida" já é sinalizado no relatório pelo S_PROTECAO
>   (KPI E/F). Re-scope se retomar: alimentar `snapshot.seguros.vida_invalidez`
>   a partir do `protecao_analyzer`/apólices — **não** criar model novo. A
>   suggestion `seguros_insuficientes` segue dormente.

### [W5-T05] FP-010-12-17 Goal IF v2 cutover (3 PRs sequenciais)

- **deps:** —
- **severity:** P1 · **effort:** L (~5-7 dias) · **owner:** financial-planner
- **status:** scoped — track histórico `agent_prompts/track_w5t05_goal_if_v2.md`. Caminho recomendado: cutover agora (Trade-off 2 ratificado); override `imoveis_no_if` por workspace fica fora desta lane (débito ADR-142).
- **files_touched:** `pipeline/domain/services/if_projector.py`, `pipeline/domain/services/passive_income_calculator.py`, `pipeline/domain/services/patrimonio_calculator.py`, `backend/app/services/goal_service.py`, frontend `useGoalIF.ts`
- **acceptance_criteria:** PR-A IFProjector emite v1+v2 lado-a-lado (additive); PR-B Frontend lê v2 (v1 fallback); PR-C drop v1 (controlled breaking); `progresso_if` muda denominador para `if_meta_liquida`; toggle `imoveis_no_if` por workspace.

> **Re-verificação factual 2026-07-08 (spike W5, pós-A33): PARCIAL.**
>
> - **JÁ ENTREGUE** (lanes ADR-142/[[ADR-222]]/[[ADR-223]], Sprint A12+):
>   numerador v2 — `IFProjector.project(investivel=investivel_efetivo)` em
>   produção ([PR #321](https://github.com/davidrobert/mathoms/pull/321)) —
>   fecha FP-012; toggle `imoveis_no_if` virou **override por workspace** com
>   UX de banner (PRs #331/#332; default `false` por ADR-223) — foi além do
>   escopo do track, que consumia só o global de `pipeline.json`.
> - **Resta** (verificado no código): denominador `if_meta_liquida` —
>   zero hits no repo; `IFProjectorConfig` sem `renda_passiva_atual_mensal_brl`;
>   `goal.if.v2.schema.json` segue **candidato sem consumidores**; [[ADR-140]]
>   segue `Roadmap`; PR-A/B/C (additive → frontend v2 → drop v1) não
>   iniciados. Nota: `useGoalIF.ts` (files_touched acima) nunca existiu no
>   código — frontend lê `goals.if_pct` direto (HeroKpiGrid,
>   S7IndependenciaSection); ajustar escopo no pickup.

---

## Wave 6 — Tech debt cleanup (Sprint +5, ~12 dias dev)

> **Goal:** Hardening de schemas, MLOps, F9 cutover, doc hygiene.
> Wave 6 paraleliza com Wave 5 — depende parcial de Wave 3 (W6-T02 → W3-T01).

### [W6-T01] Schema hardening (E5 strict + 7 sub-schemas E4 + ADR-090 wire)

- **deps:** W1-T08
- **severity:** P1 · **effort:** L · **owner:** data-engineer
- **status:** scoped — track histórico `agent_prompts/track_w6t01_schema_hardening.md`. 3 sub-PRs sequenciais (Foundation codegen → E4 split + read-side compat → strict cutover).
- **related_findings:** DE-006, DE-007, DE-014, DE-018, DE-020, DE-021, DE-012, DE-005
- **files_touched:** `config/schemas/*.schema.json` (7 novos para E4 split + e5_narrativas + e7_review + e7_crossval), `pipeline/domain/services/*_serialization.py` (gravar Decimal string), `dev/backfill_money_decimal.py` (NOVO)
- **acceptance_criteria:** schemas declaram top-level strict; `e7_review.schema.json` + `e5_narrativas.schema.json` + `validate_cross.schema.json` auto-gerados de Pydantic; ADR-090 wire compliance em todos os 5 schemas monetários; modo `strict` flippado como default.

### [W6-T02] MLOps universal hooks (meta-ADR + lane única)

- **deps:** W3-T01
- **severity:** P1 · **effort:** L · **owner:** data-engineer
- **related_findings:** DE-001, DE-004, DE-008, DE-019
- **files_touched:** `pipeline/llm/litellm_client.py` (cache + log + budget unified), `tests/test_llm_drift.py` (NOVO)
- **acceptance_criteria:** ADR-NNN "MLOps universal hooks" Decidido; LLMService.call sempre persiste LLMCallLog; cache opt-in universal com TTL 7d invalidado por PROMPT_VERSION; drift test com fixture-expected-output em CI nightly.

### [W6-T03] F9.4/F9.5/F9.6 stage rename cleanup

- **deps:** W2-T06 ✅ — paridade legacy ↔ descritivo de `_STAGE_TO_SUFFIX` estabelecida; W6-T03 destravado (status `ready`).
- **severity:** P2 · **effort:** M · **owner:** data-engineer
- **related_findings:** DE-015, CTO-006
- **files_touched:** `scripts/e*_*.py` (rename), `tests/unit/pipeline/test_no_legacy_stage_names.py` (ALLOWED_PREFIXES tightening), `pipeline/stage_spec.py` (eventual STAGE_RENAME_MAP cleanup)
- **acceptance_criteria:** F9.4 scripts renomeados; F9.5 `MATHOMS_ENFORCE_STAGE_RENAME=1` flag em CI; F9.6 ALLOWED_PREFIXES reduzido a whitelist mínima (4 paths).

### [W6-T04] Doc hygiene

- **deps:** W1-T03
- **severity:** P2 · **effort:** M · **owner:** senior-cto
- **status:** in_progress — [PR #111](https://github.com/davidrobert/mathoms/pull/111) aberto com auto-merge squash. Entregues: `dev/build_subagent_catalog.py`, `dev/check_subagent_catalog.py`, hook pre-commit, `.github/workflows/branch-cleanup.yml`, `docs/agent_prompts/archive/`. **Adiados** para follow-up dedicado: split BACKLOG (<500 linhas) + archive CHANGELOG pré-A6 (varredura por sprint).
- **related_findings:** CTO-002 (parcial), CTO-007 (atendido), CTO-008 (atendido), CTO-014 (atendido)
- **files_touched:** split de BACKLOG.md em `docs/SPRINTS/<sprint>.md`, archive de CHANGELOG.md pré-A6, `dev/build_subagent_catalog.py` (NOVO), `dev/check_subagent_catalog.py` (NOVO), `.github/workflows/branch-cleanup.yml` (NOVO), CONTRIBUTING.md
- **acceptance_criteria:** BACKLOG.md < 500 linhas; CHANGELOG.md últimos 90d; agent_prompts/archive/; subagent catalog auto-gerado; script branch-cleanup mensal.

### [W6-T05] Pipeline artifacts retention + cascade

> **✅ done (pós-A11, reconciliado 2026-07-08).** Entregue por A32.l5
> (invalidação destrutiva/tombstone, [[ADR-311]]) + A33.l6
> ([PR #844](https://github.com/davidrobert/mathoms/pull/844)): coluna
> `retention_until` + índice parcial, beat diário `fin.prune_pipeline_artifacts`
> (modo `dry_run` default), services `artifact_prune`/`artifact_retention`.
> Cascade FK Document→pipeline_artifacts foi **descartado por design** na
> A33.l6 (lifecycle coberto pelo tombstone ADR-311; FK segue `SET NULL`).
> Residual fora da task: flip `prune_mode=delete` em PR próprio, gated por
> relatório dry-run lido em prod (delete efetivo é irreversível).

- **deps:** —
- **severity:** P2 · **effort:** M · **owner:** data-engineer
- **status:** done — ver blockquote acima. Track histórico `docs/sprint/W6/tracks/w6t05-artifacts-retention.md` (consumed). Escopo original: 5 PRs sequenciais (estrutura → backfill schema_version → write path → prune task → cascade test).
- **related_findings:** DE-010, DE-011, DE-017, DE-022
- **files_touched:** Alembic migration adicionando `retention_until` + cascade FK, `backend/app/tasks/prune_artifacts.py` (NOVO), `backend/app/services/document_pipeline_sync.py` (delete_by_document_id cascade)
- **acceptance_criteria:** retention configurável (90d run-scoped, NULL workspace-scoped); celery beat task daily; FK ON DELETE CASCADE para Document → pipeline_artifacts; schema_version bumpado em writes.

### [W6-T06] CTO-001 ADR-150 decisão final

- **deps:** —
- **severity:** P1 · **effort:** S decidir + L se Caminho 1 · **owner:** senior-cto
- **status:** in_progress — [PR #110](https://github.com/davidrobert/mathoms/pull/110) aberto com auto-merge squash. **Decisão: Caminho 3 (Adiar)** — ADR-150 → `Roadmap`. Skeleton Go (~70 LOC) mantido dormente; revisita 2027-Q2 OU 100 workspaces ativos pagantes (o que vier primeiro). Trade-off 6 resolvido sem ação adicional.
- **files_touched:** `docs/DECISIONS.md` ADR-150 status, `services/` ou `pipeline-service/` (depende decisão)
- **acceptance_criteria:** sessão CTO + senior-cto + sre-devops decide Caminho 1 / rejeitada / adiada; ADR-150 atualizada; se Caminho 1: lane A6h aberta com 3 PRs; se rejeitada: skeleton Go deletado.

### [W6-T07] CTO-015 `services/` taxonomy — split por natureza + drenagem boy-scout

> **✅ done (pós-A11, reconciliado 2026-07-08).** Frente 1 entregue na A33.l9
> ([PR #855](https://github.com/davidrobert/mathoms/pull/855) — subpacotes
> `security/`, `storage/`, `documents/`, `internal_ops/`); [[ADR-285]]
> `Decidido (A33.l9)` com emenda 2026-07-08 (`classification/` autônomo +
> Frente 2 iniciada com `refresh_token_service` → `application/auth/`).
> Frente 2 (drenagem boy-scout) segue como convenção contínua, sem gate de
> fechamento — não é pendência de sprint.

- **deps:** [[ADR-285]] (Proposto 2026-06-09). **Gate de pickup (Frente 1):** ≤1 PR
  ativo tocando `backend/app/services/` — em 2026-06 há 5+ PRs em voo; abrir o
  split agora garante conflito de rebase cross-cutting.
- **severity:** P3 · **effort:** M (Frente 1) + contínuo (Frente 2) · **owner:** senior-cto
- **origem:** finding **CTO-015** (avaliação senior-cto 2026-06-09): recomendação
  "quebrar `services/` em subpacotes por domínio" **recusada** — duplicaria a
  taxonomia de domínio que já existe em `application/<domain>/` (R15/ADR-101).
  Rationale completo em [[ADR-285]].
- **Frente 1 (lane futura):** subpacotes por natureza técnica (`security/`,
  `storage/`, `pipeline/`, `documents/`); 1 subpacote por PR com shim de
  re-export temporário; codemod final de imports em PR separado.
- **Frente 2 (boy-scout, sem gate de fechamento):** lane que já toca
  `*_service.py` de domínio avalia drenar a lógica de use-case para
  `application/<domain>/`, deixando em `services/` só adapter fino.
- **acceptance_criteria (Frente 1):** 4 subpacotes criados; shims removidos no PR
  final; 5 patch-strings dotted de testes atualizados; `pytest backend/tests -q`
  verde; OpenAPI snapshot sem diff; entrada em `STATELESS_AUDIT.md` §2 se path
  de singleton lazy mudar; ADR-285 flippa `Decidido` no merge do 1º subpacote.

---

## Trade-offs registrados (decisões CTO)

### Trade-off 1 — Charts S1: Recharts vs Chart.js

- **Posição A (product-designer PD-004):** Migrar para Chart.js (paridade visual + a11y + bundle).
- **Posição B (build-vs-buy BB-011):** Manter (tech-debt rastreável, já tem ADR-139).
- **Decisão CTO:** Migrar (Posição A prevalece).
- **Razão:** ADR-139 já é precedente para single-engine; a11y gap em S1 é P1 sem outra mitigação; bundle -150kb é benefício colateral.
- **Implementação:** Lane W5-T02. ADR-139 status atualizada para "Decidido (executado em W5-T02)".
- **Nota factual (2026-07-08, spike W5):** [[ADR-139]] já flippou `Decidido (Onda v2.E concluída)` em 2026-04-26, preservando os 2 charts como residual intencional ("v2.E.9"). W5-T02 deve registrar **emenda datada** na ADR-139 ao fechar — não um novo flip de status.
- **Executado (2026-07-08, [PR #883](https://github.com/davidrobert/mathoms/pull/883)):** emenda datada registrada na [[ADR-139]] (`amended_at: ["2026-07-08"]` + §"Emenda — fechamento do resíduo v2.E.9"); status permaneceu `Decidido`, sem flip — conforme a nota factual acima.

### Trade-off 2 — Goal IF v2: cutover agora vs adiar

- **Posição A (financial-planner FP-010):** Lane "Goal IF v2 cutover" agora — 4 findings correlatos (FP-010/11/12/17).
- **Posição B (CTO conservador):** v2 schema é breaking; coordenar timing com frontend.
- **Decisão CTO:** Aceitar Posição A com mitigação — dividir em 3 PRs sequenciais (additive → frontend reads v2 → drop v1).
- **Implementação:** Lane W5-T05.

### Trade-off 3 — F9 cutover pace

- **Posição A (data-engineer DE-015):** Tightening progressivo de ALLOWED_PREFIXES em PRs incrementais.
- **Posição B (CTO CTO-006):** Fechar F9.4/F9.5/F9.6 antes de F7 produção (urgência).
- **Decisão CTO:** Sincronizar — DE-015 é o "como" + CTO-006 é o "quando". Alinhados em W6-T03.

### Trade-off 4 — MonetaryValue migration scope

- **Posição A (product-designer PD-010):** Single chore para 11 call-sites.
- **Posição B (CTO):** PD-013/011/012 são correlatos. Sub-lanes paralelizáveis.
- **Decisão CTO:** Aceitar Posição A — single lane W5-T03 (effort M, 1 PR).

### Trade-off 5 — Velocidade vs Disciplina arquitetural (meta)

- **Observação:** Sprints recentes (A8.4, A9, Onda 8) entregaram alta velocidade mas com follow-ups latentes (FP-001/2/3, PD-001/2/23 são todos pós-merge defects).
- **Decisão CTO:** Política nova "ADR Proposto antes de PR de implementação P0" — ~30min/feature de overhead, previne dead code shipping. Documentado em CTO-004 + W1-T06 + CLAUDE.md patch (§Ações sugeridas).
- **Não compromete velocidade total** — apenas exige raciocínio arquitetural antes da implementação.

### Trade-off 6 — Pipeline-service Caminho 1 (Go vs status quo Python)

- **Posição A (status quo):** Python pipeline-service skeleton; Celery in-process.
- **Posição B (ADR-150 Caminho 1):** Go shell via subprocess; HTTP boundary real.
- **Decisão CTO:** **Não decidir continua sendo a pior opção.** W6-T06 força decisão em sessão CTO — pode resultar em rejeitar Caminho 1 (formalizar status quo) ou aceitar e abrir lane A6h. Status atual `Proposto` permanente é o problema.

---

## Coverage matrix

| Stage | DE | FP | PD | SR | BB | CTO | Status |
|-------|----|----|----|----|----|----|------|
| **E0** (audit/unlock/route) | indir. | — | — | indir. | BB-010 | — | ⚠️ gap |
| **E1** (extract_members) | DE-003 | FP-002 | — | SR-009 | — | — | ✅ |
| **E1.5** (extract_baseline) | DE-003,010 | — | — | SR-009 | — | — | ✅ |
| **E1.5c** (consolidate_baseline) | indir. | indir. | — | — | — | — | ⚠️ |
| **E1.6** (extract_irpf_full) | DE-021,022 | FP-006 | PD-004 | — | — | — | ✅ |
| **E2-extratos/faturas** | DE-014,012 | — | — | — | BB-010 | — | ✅ |
| **E2-llm** | DE-002,008 | — | — | SR-009 | — | — | ✅ |
| **E3** (reconcile) | DE-005,012 | — | — | — | — | — | ⚠️ partial |
| **E4** (categorize) | DE-014 | FP-015 | — | — | — | — | ✅ |
| **E5** (analyze) | DE-005,006 | múltiplos | PD-006 | — | — | — | ✅ pesado |
| **E5.N** (narratives) | DE-007 | FP-019 | PD-016 | — | — | — | ✅ |
| **E7-crossval** | DE-007 | — | — | — | — | — | ⚠️ thin |
| **E7-review** (LLM) | DE-002,007 | — | — | SR-009 | — | — | ✅ |
| **E7-apply** | DE-007 | — | — | — | — | — | ⚠️ thin |

**Gaps explícitos:** E0 stages, E1.5c, E7-crossval, E7-apply. Recomendação:
**próxima revisão (Q3 2026)** prioriza esses 4 stages.

---

## CLAUDE.md patches

> Propostas em diff format. **Não aplicar diretamente.** Agente humano
> revisa, aplica em commit dedicado de doc, dispara `pre-commit run`.

### Patch 1 — Sync §Code style › Testes (W1-T03)

```diff
@@ §Code style › Testes
- **Goldens de paridade** (Caminho B): legado ↔ novo, tolerância `0.01` BRL
-   em whitelist monetária. Padrão: `tests/test_e3_main_with_store_parity.py`.
+ **Goldens de execução** (pós-A6c.3): runs canônicos com schema validation
+   em `tests/test_e{3,4,5}_golden_execution.py`. Goldens de paridade
+   legado↔novo (Caminho A vs Caminho B) foram descontinuados em A6c.3
+   quando Caminho A foi removido. Para regression de output exato,
+   ver `docs/plan/PLATFORM_REVIEW/_README.md` §W6-T01 (re-construir baselines snapshot).
```

### Patch 2 — Adicionar §"ADR Proposto antes de PR P0/P1" (W1-T06)

```diff
@@ §ADRs → docs/DECISIONS.md (após cheat-sheet)
+ ### Política operacional
+
+ **Toda task P0/P1 com escopo arquitetural** (modelo de DB, contrato API,
+ fornecedor externo, política de segurança, mudança em invariante crítico)
+ **DEVE abrir ADR `Proposto` antes do PR de implementação.** PR de
+ implementação referencia ADR explicitamente e flippa para `Decidido (Sprint XX.Y)`
+ no merge. Custo: ~30min/feature. Ganho: rastreabilidade arquitetural,
+ menos dead code shipping (lição aprendida 2026-05 — ver
+ `docs/plan/PLATFORM_REVIEW/_README.md` §Trade-off 5).
```

### Patch 3 — Adicionar §Hotspots: limite agente humano 5 worktrees (W6-T04)

```diff
@@ §Hotspots de documentação (final)
+ ### Limite de worktrees ativas
+
+ Agente humano não deve manter mais que **5 worktrees ativas** simultaneamente
+ (regra de produtividade — diff cognitivo entre 18 simultâneas é proibitivo).
+ Quando exceder: arquivar worktrees não-prioritárias via
+ `git worktree remove <path>` + commit/push do progresso (pelo menos WIP).
+ Política em `.github/CONTRIBUTING.md` §Worktrees.
```

### Patch 4 — Adicionar §Subagentes (W6-T04, auto-gerado)

```diff
@@ §Subagentes especializados
- # Lista hardcoded dos 6 subagents
+ <!-- Esta lista é auto-gerada por dev/build_subagent_catalog.py -->
+ <!-- Para editar, modifique .claude/agents/<nome>.md e rode: -->
+ <!-- python3 dev/build_subagent_catalog.py --inline -->
+ <!-- BEGIN auto-gen catalog -->
+ ...lista preservada com prefix de auto-gen...
+ <!-- END auto-gen catalog -->
```

### Patch 5 — CODEOWNERS para human review obrigatório (W4-T04 ou complementar)

```diff
@@ Adicionar arquivo .github/CODEOWNERS (NOVO)
+ # Paths que exigem human reviewer (não auto-merge):
+ /backend/app/services/vault.py @davidrobert
+ /backend/app/core/security.py @davidrobert
+ /backend/app/middleware/tenancy_context.py @davidrobert
+ /backend/app/api/auth.py @davidrobert
+ /backend/alembic/versions/ @davidrobert
+ /dev/check_*.py @davidrobert
+ /.github/workflows/ @davidrobert
+ /CLAUDE.md @davidrobert
```

---

## Ações sugeridas

Antes de pegar W2+, executar:

1. **Aplicar W1 inteira** — todas as 8 tasks `ready` em paralelo (1 owner cada).
2. **Aplicar Patches CLAUDE.md** após W1 mergear.
3. **Verificar fix de findings** — Quick Wins (W1-T02, T03, T04, T05) devem fechar
   findings PD-001/002/005/023 (cluster tokens), FP-001/002/003 (cluster regras
   dormentes), CTO-009 (CLAUDE.md), BB-009 (PDF capacity), SR-022 (SECRET_KEY).
4. **Auditar próximo trimestre** — re-rodar `track_platform_review.md` em Q3 2026
   focado nos gaps E0/E1.5c/E7-crossval/E7-apply.

---

## Histórico

- **2026-05-06** — plano criado a partir de revisão multi-agente (138 findings consolidados em 32 tasks).
- **2026-05-07** — orquestração Wave 5 + Wave 6 (8 tasks unblocked em paralelo). 6 tasks com track docs criados em `docs/agent_prompts/track_w{5,6}t*.md` (W5-T01/T03/T04/T05, W6-T01/T05). 2 tasks executadas: W6-T04 (PR #111 — subagent catalog auto-gen + branch-cleanup) e W6-T06 (PR #110 — ADR-150 → Roadmap, Caminho 3). 3 tasks permanecem bloqueadas (W5-T02 dep W5-T01, W6-T02 dep W3-T01, W6-T03 dep W2-T06).
- **2026-06-09** — sync de status Wave 3 (stale desde w2_done ✅ 2026-05-20): W3-T01/T04 `blocked`→`ready`, W3-T02 `ready (owner-gated: Resend)`, **W3-T03 pickup → in_progress** (implementação ADR-170, co-design sre-devops: payload mantém `{sub, exp, tv}` com emenda na ADR, cookie path `/api/v1/auth`, teto absoluto 30d, grace window 60s anti-falso-positivo de reuse, CSRF via header custom). Registrado finding **CTO-015** (W6-T07): split de `services/` por natureza técnica (ADR-285 Proposto) + drenagem boy-scout para `application/`; recomendação "split por domínio" recusada.
- **2026-06-09 (noite)** — **W3-T03 entregue** ([PR #584](https://github.com/davidrobert/mathoms/pull/584)): refresh tokens httpOnly com family revocation; [[ADR-170]] flippada `Decidido (Sprint A11.W3)` com emendas; supersedure bidirecional [[ADR-057]] ↔ [[ADR-170]]. Wave 3 restante: W3-T01/T04 `ready`, W3-T02 `ready (owner-gated)`.
- **2026-07-08 (noite, sessão de closure A11)** — reconciliação W6 contra entregas pós-A11: **W6-T05 done** (A32.l5 tombstone [[ADR-311]] + A33.l6 retention+prune #844; cascade descartado por design; residual fora da task = flip `prune_mode=delete` em PR próprio) e **W6-T07 done** (A33.l9 #855; ADR-285 `Decidido`). Lanes A11 (w3/w4/w5/w6/report-publication), `lanes.md` e SPRINTS-active §A11 sincronizadas com o Index. Residual consolidado da sprint: 5 owner-gated (W3-T02, W4-T01/T02 restos, W4-T03, W4-T05) + W5 residual + W6-T01 residual. ADR-174 é a única do DoD ainda `Proposto` (flip não merecido sem off-site R2 real).
- **2026-07-08** — **spike docs-only de re-verificação factual da Wave 5** (follow-up nomeado no fechamento da A33): W5-T01 **parcial** (aria-label de charts coberto p/ Chart.js via Onda v2.E; scope=col 0/13, progressbar, reduced-motion e gate axe moderate pendentes), W5-T02 **válida** (2 charts seguem Recharts; ADR-139 exige emenda, não flip), W5-T03 **válida** (18 call-sites do inventário intactos + novos fora dele), W5-T04 **parcial** (sub-PR #5 ✅ via W1-T02 #98; #2 obsoleto por [[ADR-239]]/[[ADR-240]]; #1/#3/#4 válidos), W5-T05 **parcial** (`investivel_efetivo` + `imoveis_no_if` per-workspace ✅ #321/#331/#332; `if_meta_liquida`/emissão v2 pendentes, ADR-140 `Roadmap`). Saldo: **0 tasks da onda fecharam integralmente** — W5 segue viva com escopo reduzido anotado por task; não arquivar.
- **2026-07-08 (noite)** — **W5-T01 residual entregue** (sessão de closure A11): `scope="col"` universal (primitivo `TableHead` + 23 arquivos com `<th>` literal), primitivo `<ProgressBar/>` em `ui/ProgressBar.tsx` com adoções (IFHeroCard, ReservaEmergenciaCard; EquilibrioCerbasiCard → `role="img"` por ser distribuição empilhada, Kpi microbars mantidos `aria-hidden`), `prefers-reduced-motion: reduce` global em `globals.css`. Ficam por design: gate axe `critical+serious` (D1), aria-label dos 2 Recharts (W5-T02), baselines visuais (W1-T01).
