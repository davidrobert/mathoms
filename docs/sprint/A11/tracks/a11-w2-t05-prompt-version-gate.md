---
id: TRACK-a11-w2-t05-prompt-version-gate
type: track
title: "W2-T05 — extract_with_llm incremental + PROMPT_VERSION gate CI"
lane: "[[A11.w2]]"
sprint: A11
plan: PLAN-platform-review
status: ready
created_at: "2026-05-20"
agent_role: data-engineer
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/pipeline
  - area/llm
  - area/ci
  - phase/a11
---

# Track — W2-T05 extract_with_llm incremental + PROMPT_VERSION gate

> **Lane ID:** A11.W2 · Task T05
> **Branch prefix:** `agent/platform-review-w2-t05/<yyyyMMdd-HHmm>`
> **Severidade:** P1 · **Effort:** S
> **Owner agent:** data-engineer
> **Deps:** nenhuma; segue [[ADR-093]]. Não cria ADR nova.
> **Paralelo com:** W2-T02 (security headers), W2-T04 (heartbeat), W2-T06 (stage suffix).
> **Nota de escopo (2026-05-13):** `review_finances` removido do escopo — substituído pelo stage `parecer_planejador` em PLANNER_REVIEW Ato 4. **PROMPT_VERSION gate e `extract_with_llm` incremental permanecem.**

## Contexto que você DEVE ler antes de agir

1. `CLAUDE.md` (raiz) — §"Concluído" · §"Pipeline não importa framework" · §"Cadência de commit defensiva" · §"Antes de pegar uma task do BACKLOG" · §"Stateless rigoroso".
2. `docs/sprint/A11/_README.md` — DoD code-complete pós-[[ADR-228]].
3. `docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md` §[W2-T05] — files_touched + acceptance_criteria + nota **escopo_alterado**.
4. Arquivos relevantes:
   - `pipeline/stages/extract_with_llm.py` (stage que precisa respeitar `ctx.incremental`)
   - `pipeline/llm/schemas/e1_members.py`, `pipeline/llm/schemas/e15_baseline.py`, `pipeline/llm/schemas/e2_llm.py` — 3 dos 4 prompts a versionar
   - `pipeline/llm/prompts/parecer_planejador*.py` (ou equivalente) — 4º prompt; **investigue** onde vive (PLANNER_REVIEW Ato 4 entregou; `rg "parecer_planejador" pipeline/llm/`).
   - Buscar `ctx.incremental` em outros stages para padrão de uso: `rg "ctx.incremental" pipeline/stages/`.

## Estado de entrada (2026-05-20)

- W1 ✅ + W2-T03 ✅ + W2-T01 PR #359 + W2-T02 em paralelo (worktree `crazy-borg-f27ed8` — NÃO toque).
- Wave 2 fechando: T04 + T05 + T06 paralelo + T02 já em curso.
- Escopo W2-T05 reduzido em 2026-05-13 (remover `review_finances` — agora `parecer_planejador` cobre).

## Pickup checks obrigatórios

```bash
git fetch origin
git worktree list
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/ | head -15
```

Procure `agent/platform-review-w2-t05-*`. Disjunto de W2-T02 (`crazy-borg-f27ed8`), W2-T04, W2-T06.

## Branch + ordem

1. `git checkout -b agent/platform-review-w2-t05/<yyyyMMdd-HHmm> origin/main`
2. **Delegação obrigatória**:
   - `data-engineer` — owner principal (contrato `extract_with_llm`, `PROMPT_VERSION` semantics, CI gate logic).
   - Brief mínimo: contexto + recomendação inicial (formato `PROMPT_VERSION = "v1"` como constante no módulo do prompt; `dev/check_prompt_version_bumped.py` grep diff em prompts + bump check). **NÃO peça código.**
3. **Não precisa criar ADR nova** — escopo coberto por [[ADR-093]] e discussão prévia no PLAN. Se durante implementação você descobrir decisão arquitetural latente (ex.: formato semver vs counter), abra ADR-NNN `Proposto` antes do PR.

## Implementação

- `pipeline/stages/extract_with_llm.py`:
  - Checar `ctx.incremental` flag; se True, skipar prompts cujos `PROMPT_VERSION` + input hash já estejam cacheados em `pipeline_artifacts` (pattern dos outros stages que respeitam incremental — `rg "ctx.incremental"`).
- Cada um dos 4 prompts LLM declara constante de módulo:
  ```python
  PROMPT_VERSION = "v1"
  PROMPT_TEXT = """..."""  # ou template existente
  ```
  4 prompts: `e1_members`, `e15_baseline`, `e2_llm`, `parecer_planejador` (confirmar nome do arquivo do parecer; investigue via `rg "parecer" pipeline/llm/`).
- `dev/check_prompt_version_bumped.py` (NOVO):
  - Hook CI/pre-commit: `git diff origin/main -- pipeline/llm/prompts/ pipeline/llm/schemas/`.
  - Se diff toca arquivo com `PROMPT_TEXT` ou `PROMPT_TEMPLATE` ou similar, exige que `PROMPT_VERSION` no mesmo arquivo seja bumpado (`v1` → `v2`).
  - Sem bump: falha gate com mensagem `"PROMPT_VERSION não bumpado para <file>; defina nova versão para invalidar cache LLM."`
- Adicionar hook em `.pre-commit-config.yaml`.

## Tests

- `tests/unit/pipeline/test_extract_with_llm_incremental.py` (NOVO) — assert que prompt cacheado é skipado em incremental mode.
- `tests/unit/dev/test_check_prompt_version_bumped.py` (NOVO) — cenários: diff sem bump → fail; diff com bump → pass; diff em arquivo não-prompt → pass; sem diff → pass.

## Validação obrigatória pré-push

```bash
python3 -m pre_commit run --all-files
pytest backend/tests -q --ignore=backend/tests/integration
pytest tests -q --ignore=tests/integration
python3 dev/check_code_style_regression.py
# Smoke do gate novo:
python3 dev/check_prompt_version_bumped.py  # deve passar (sem diff em prompts)
```

## Commit + PR

```bash
git commit -m "feat(pipeline): W2-T05 — extract_with_llm incremental + PROMPT_VERSION gate CI (Sprint A11.W2)"
git push origin agent/platform-review-w2-t05/<yyyyMMdd-HHmm>
gh pr create --base main --title "..." --body "..."
gh pr merge <N> --squash --auto
```

Corpo: explicar incremental flag + gate logic + 4 prompts versionados. Após merge: update Index PLAN W2-T05 → done. **Não há ADR nova para flippar.**

## Anti-padrões a evitar

- ❌ Bumpar `PROMPT_VERSION` de forma que invalide cache **em massa** num PR só (forçar 4 prompts a bumpar juntos). Cada arquivo bumpa independente.
- ❌ Hook que faz parse AST quebradiço — prefira regex sobre `PROMPT_VERSION\s*=\s*['"]v\d+['"]`.
- ❌ Esquecer parecer_planejador (4º prompt) — buscar caminho no repo.
- ❌ Confundir `extract_with_llm` (stage) com `extract_invoices`/`extract_statements` (E2 deterministic).
- ❌ Push direto em `main`; auto-merge squash via Ruleset.

## Critério de fim

- PR aberto com CI rodando OU mergeado.
- W2-T05 marcado done no Index do PLAN.
- Gate `check_prompt_version_bumped.py` operacional (hook pre-commit + workflow CI).
- 4 prompts LLM declaram `PROMPT_VERSION = "v1"`.
