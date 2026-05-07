---
id: TRACK-w5t05-goal-if-v2
type: track
title: "Track W5-T05 — Goal IF v2 cutover (3 PRs sequenciais)"
sprint: W5
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/w5
  - status/consumed
---

# Track W5-T05 — Goal IF v2 cutover (3 PRs sequenciais)

> **Lane ID:** `w5t05-goal-if-v2`
> **Branch prefix:** `agent/w5t05-goal-if-v2/<yyyyMMdd-HHmm>`
> **Plano canônico:** [plan/PLATFORM_REVIEW/_README.md §W5-T05](../plan/PLATFORM_REVIEW/_README.md)
> **ADRs:** [ADR-140](../DECISIONS.md) (schema v2 — Roadmap) · [ADR-142](../DECISIONS.md) (anti-dupla-contagem — Decidido)
> **Onda:** Wave 5 (paraleliza com W5-T01/T03/T04 e W6-T*)
> **Severity:** P1 · **Effort:** L (~5-7d) — sequencial estrito
> **Owner:** financial-planner
> **Depende de:** —
> **Findings cobertos:** FP-010, FP-011, FP-012, FP-017

---

## Briefing

ADR-140 (Roadmap) e schema candidato `goal.if.v2.schema.json` existem
desde 2026-04-27 mas backend, frontend e DB writers continuam emitindo
v1. Esta lane materializa o cutover em 3 PRs incrementais
(additive → frontend reads → drop v1).

`progresso_if` em produção hoje **subestima o gap** para famílias com
renda passiva já fluindo (aluguéis/dividendos), e usa `investivel`
(financeiro+caixa, sem cat_2) em vez de `investivel_efetivo` (toggle
`imoveis_no_if`). v2 fecha ambos.

---

## 1. Diferenças v1 vs v2

### `progresso_if`

| Versão | Numerador | Denominador | Onde |
|---|---|---|---|
| **v1 atual** | `patrimonio.investivel` (= bruto − residência − veículos) | `if_meta` (bruta = renda × 12 / TRS) | `scripts/e5_analyze.analyze_goals` ~L1189 |
| **v2 alvo** | `patrimonio.investivel_efetivo` = `investivel_financeiro + (cat_2 if workspace.imoveis_no_if else 0)` | `if_meta_liquida` = `MAX(0, (renda − renda_passiva_atual) × 12 / TRS)` | `FORMULAS.md §IF` |

**Drift esperado:** progresso v2 **maior** quando `renda_passiva_atual > 0`.

### Toggle `imoveis_no_if`

- **Default produto:** `true` (ADR-142 — yield líquido dogfood ~6% > TRS 5%).
- **Hoje:** global em `config/pipeline.json:patrimonio_composicao.imoveis_no_if`.
- **Alvo:** override por workspace (`Workspace.imoveis_no_if: bool | None`, None = global). **Lane separada** — não abrir nesta task; W5-T05 consome o global e deixa hook por-workspace como TODO em PR-C.

### Campos novos v2

**Inputs:**
- `renda_passiva_atual_mensal_brl: number` (default 0)

**Derived:**
- `if_meta_bruta_brl` (substitui semanticamente `if_meta_brl`)
- `if_meta_liquida_brl` (novo — usado em `progresso_if`)
- `if_meta_brl` mantido como alias deprecated == bruta (compat reverso)

**Pipeline E5:** `goals.if_meta_bruta`, `goals.if_meta_liquida`, `goals.if_pct` (recalculado).

---

## 2. PR-A — IFProjector emite v1+v2 (additive)

**Objetivo:** zero breaking. Consumers v1 continuam lendo `if_meta`/`if_gap`/`if_pct`; consumers v2 leem campos novos.

**Assinatura:** flag `version: Literal["v1", "v2", "both"] = "both"` em `to_legacy_dict()` — devolve dict com chaves v1 SEMPRE (compat) + chaves v2 quando `version in {"v2", "both"}`. Suporta golden parity.

### `IFProjectorConfig` muda

Adicionar:
- `renda_passiva_atual_mensal_brl: float = 0.0`
- `imoveis_no_if: bool = True` (lê de `pipeline.json` no adapter)

### `IFProjection` muda

Adicionar:
- `if_meta_bruta: float`
- `if_meta_liquida: float`
- `investivel_efetivo: float` (passado pelo caller)
- `if_pct_v2: float` (= `investivel_efetivo / if_meta_liquida × 100`)
- `if_gap_v2: float` (= `MAX(0, if_meta_liquida − investivel_efetivo)`)

`project(investivel_financeiro, investivel_efetivo)` muda assinatura — caller passa os dois. Em PR-A, fallback `investivel_efetivo = investivel_financeiro` preserva v1.

### Diff por arquivo

| Arquivo | Mudança |
|---|---|
| `pipeline/domain/services/if_projector.py` | `IFProjectorConfig` +2 campos · `IFProjection` +5 campos · `to_legacy_dict(version="both")` |
| `pipeline/domain/services/patrimonio_calculator.py` | Emitir `investivel_financeiro` e `investivel_efetivo` (verificar se já emite — `FORMULAS.md` documenta). |
| `backend/app/services/goal_service.py` | `compute_if_derived` adiciona kwargs; calcula `if_meta_bruta_brl`, `if_meta_liquida_brl`. |
| `backend/app/schemas/dto/goal/*.py` | `IFGoalInputs` +1 · `IFGoalDerived` +2. `meta_version` aceita 1 ou 2. |
| `config/schemas/e5_analysis.schema.json` | Declarar `goals.if_meta_bruta`, `goals.if_meta_liquida` opcionais. |
| `tests/unit/pipeline/test_if_projector.py` | Test: `renda_passiva_atual=0` → paridade v1. |
| `tests/test_goal_service.py` | Test: `compute_if_derived(renda_passiva_atual=R$3k)` → `if_meta_liquida < if_meta_bruta`. |

**Acceptance:**
- [ ] `pytest tests/test_e5_golden_execution.py` continua verde.
- [ ] Schema validator E5 passa em `mode=warn`.

---

## 3. PR-B — Frontend reads v2 com fallback v1

**Objetivo:** UI exibe métricas v2 quando disponíveis; workspaces ainda em v1 caem em fallback.

### Diff por arquivo

| Arquivo | Mudança |
|---|---|
| `frontend/src/lib/api/goals.ts` | `IFGoalDerived` +2 opcionais (`if_meta_bruta_brl?`, `if_meta_liquida_brl?`). |
| `frontend/src/hooks/useGoalIF.ts` (NOVO) | Hook fino: lê `IFGoalResponse`, expõe `metaBruta`, `metaLiquida`, `progressoPct`, `gapBrl` com fallback. |
| `frontend/src/app/(app)/plano/_components/IFHeroCard.tsx` | Substitui `goal.derived.if_meta_brl` por `useGoalIF(goal)`. KPI "Meta IF" passa a mostrar **liquida**; "Meta bruta" como sublabel. |
| `frontend/src/components/report/sections/S7IndependenciaSection.tsx` | Lê `goals.if_meta_liquida ?? goals.if_meta`. Adicionar Stat "Renda passiva atual" quando `> 0`. |
| `frontend/src/app/(app)/plano/meta-if/wizard/page.tsx` | +Campo `renda_passiva_atual_mensal_brl`. Tooltip explica anti-dupla-contagem (ADR-142). |
| `frontend/tests/components/IFHeroCard.test.tsx` | Test: payload v1 → fallback. Payload v2 → v2. |

**Acceptance:**
- [ ] Vitest verde em fixtures v1 e v2.
- [ ] Visual baseline IF Hero atualizado.

---

## 4. PR-C — Drop v1 (controlled breaking)

**Objetivo:** remover código de paridade após PR-A+PR-B em prod ≥1 release.

### Consumers a remover/migrar

**Backend:** `IFGoalDerived.if_meta_brl` removido; migrator Alembic preenche `if_meta_bruta_brl = if_meta_brl` em goals existentes; `compute_if_derived` retorna apenas v2; `goal.if.schema.json` v1 deprecated.

**Pipeline:** `analyze_goals` retorna apenas `if_meta_bruta`/`if_meta_liquida`; schema E5 exige `if_meta_liquida`.

**Frontend:** `useGoalIF` remove fallback; `goals.ts` IFGoalDerived sem `if_meta_brl`; wizard `renda_passiva_atual` obrigatório.

### Migration de dados (one-shot Alembic)

Para todo `Goal` ativo `type=INDEPENDENCIA_FINANCEIRA`:
- `inputs.renda_passiva_atual_mensal_brl ← 0` (workspace re-edita).
- `derived.if_meta_bruta_brl ← derived.if_meta_brl`.
- `derived.if_meta_liquida_brl ← derived.if_meta_brl` (== bruta quando renda_passiva=0).
- `params_json.meta_version ← 2`.

`imoveis_no_if` permanece global em `pipeline.json`. Override por workspace é débito separado.

### Plano de comunicação

Release notes (CHANGELOG.md + email tenants) 7 dias antes do PR-C:

> **Goal IF v2** — relatórios e plano agora distinguem **Meta bruta**
> de **Meta líquida** (descontando aluguéis e dividendos já recebidos).
> Em workspaces com renda passiva > 0, o **Progresso aumenta**. Reedite
> seu Goal IF para declarar a renda passiva atual — sem isso, mantemos
> 0 (comportamento v1).

---

## 5. Risco de paridade (goldens E5)

**Procedimento obrigatório antes do merge PR-A:**

1. Em fixture canônica, executar v1 e v2.
2. Comparar `goals.if_pct`, `if_gap`, `if_meta` entre v1 e v2.
3. Documentar drift esperado:
   - Workspace dogfood `renda_passiva_atual=0` e `imoveis_no_if=true`: drift **zero**.
   - Workspace com aluguéis: `if_pct` aumenta, `if_gap` diminui, `if_meta_liquida` diminui.

**Gate:** `tests/test_e5_golden_execution.py` aceita drift documentado **ou** congela v1 no golden e cria `test_e5_golden_v2.py` (preferível).

---

## 6. Rollback plan

- **PR-A:** revert puro. Zero impacto runtime (additive).
- **PR-B:** revert da branch frontend. Backend continua emitindo v1+v2; UI volta a v1.
- **PR-C:** revert exige reverter Alembic migrator. **Mais arriscado** — PR-C só após PR-B em prod ≥1 sprint sem incidente.

---

## 7. Critério de aceite global

- [ ] PR-A mergeado: `to_legacy_dict()` emite v1+v2; goldens verdes.
- [ ] PR-B mergeado: hook `useGoalIF` cobre 100% dos consumers.
- [ ] PR-C mergeado: migrator Alembic em staging; release notes publicadas; `if_meta_brl` removido.
- [ ] ADR-140 status flippa para `Decidido (Sprint W5)`.
- [ ] FORMULAS.md §IF não menciona mais "v1 ainda em produção".
- [ ] Drift `progresso_if` v1×v2 documentado em comentário do golden.

---

## Decisões abertas (resolver no kickoff)

1. **`useGoalIF.ts` é PR-B ou PR-A?** Recomendado PR-B — não bloqueia se PR-A demorar.
2. **`if_meta_brl` alias persiste quanto tempo após PR-C?** Recomendado: 1 sprint, removido em cleanup junto com schema v1.
3. **Override `imoveis_no_if` por workspace entra agora?** **Não.** PR-C deixa hook (`workspace.imoveis_no_if_override`) preparado mas sempre None.

---

## Trade-off principal — velocidade × segurança

- **Velocidade pura** (1 PR, 2 dias): bump in-place. Custo: breaking sincronizado backend+frontend+DB; risco real de inconsistência.
- **Segurança máxima** (PR-A em prod por 2 sprints antes de PR-B): 4-6 semanas em estado dual. Risco de inércia — PR-C nunca fecha.
- **Caminho recomendado** (3 PRs em ~5-7 dias): PR-A staging ≥3 dias + prod, PR-B prod ≥1 sprint, PR-C com migrator + release notes 7 dias antes.
