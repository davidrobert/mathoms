---
id: ADR-114
type: adr
title: "Enforcement automatizado de code style: gates imediatos + progressivos (A6g.6)"
status: Decidido
phase: "A6g.6"
date: "2026-04-22"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 114"]
tags:
  - type/adr
  - status/decidido
size_lines: 161
---

# ADR-114 — Enforcement automatizado de code style: gates imediatos + progressivos (A6g.6)

**Status:** Decidido (A6g.6) • **Data:** 2026-04-22

**Contexto:** 3 sweeps consecutivos (A6g.2 r1, A6g.4 r1+r2+r3, A6g.5) e
tracks adjacentes (A6g.3, A6g.3b, A6g.7) limparam ~500 ofensores das
regras do `CLAUDE.md` §Code style — long functions em serviços de
domínio, `any` em TypeScript, filenames genéricos, `float` em campo
monetário. O audit `dev/audit_code_style.py` (A6g.1) catalogou 2211
ofensores e permanecia **informativo**: sem gate, novos PRs
reintroduzem padrões eliminados. 15 sessões de trabalho viravam débito
técnico silencioso.

Estado pré-A6g.6: `pyproject.toml` sem bloco `[tool.ruff]`; `frontend/`
usando apenas `next lint` default sem regras bloqueantes;
`pre-commit` com hooks de higiene e codegen mas zero lint de Python
ou TS; CI rodando só `pre-commit run --all-files` no job `lint`.
Auditor existia, não rodava em CI.

Três alternativas consideradas:

1. **Ativar todas as regras do ruff/ESLint de uma vez (select = "ALL")**
   — rejeitada. Baseline de 2211 ofensores mais 421 arquivos que
   `ruff format` reformataria: `per-file-ignores` gigante + PR com
   diff de centenas de arquivos + conflito cross-cutting com agentes
   paralelos (A6e.4, A6e.events). Retorno negativo inicial.
2. **Apenas auditor informativo no CI (sem gate bloqueante)** —
   rejeitada. Já é o estado atual; não impede regressão.
3. **Gate bloqueante estrito com allowlist por arquivo/linha** —
   rejeitada como default. Allowlist com centenas de entradas vira
   arquivo ilegível; manutenção desequilibra entre o valor (evitar
   regressão) e o custo (navegar allowlist em cada review).

**Decisão:** enforcement **bicameral** — regras imediatas bloqueiam
código novo; regras progressivas decrementam via baseline auditado.

### Gates imediatos (bloqueiam staged diff)

- **Ruff** (`pyproject.toml [tool.ruff.lint]`): seleção conservadora
  E/F/I/W — bloqueia erros reais (imports quebrados, redefinições,
  sintaxe). UP (pyupgrade), B (bugbear), C90 (mccabe) ficam para
  A6g.6b após sweep dedicado. I001 (unsorted-imports) e F541
  (f-string sem placeholder) em `ignore` por ora — 285+71 arquivos
  reformatariam em auto-fix, conflitando com agentes paralelos.
  `ruff-format` disponível via `ruff format .` mas **não** ativado
  no pre-commit (422 arquivos reformatariam agora).
- **ESLint** (`frontend/eslint.config.mjs`, flat config v9):
  `@typescript-eslint/no-explicit-any: error` preserva sweep A6g.4
  (zero `any` em 2026-04-22); `@typescript-eslint/no-unused-vars:
  error` com `argsIgnorePattern: "^_"`. `max-lines` e
  `max-lines-per-function` em `warn` (74 warns atuais) —
  promovidos a error em A6g.6b.
- **Filenames genéricos** (`dev/check_forbidden_names.py`): bloqueia
  `utils.py/ts(x)`, `helpers.py/ts(x)`, `manager.py/ts(x)`,
  `handler.py/ts(x)`, `service.py/ts` — match exato, não prefixo.
  ALLOWLIST vazia desde A6g.2c ✅ (2026-04-22) que renomeou
  `pipeline/llm/service.py` → `pipeline/llm/litellm_client.py`.
- **Float monetário** (`dev/check_float_money.py`, ADR-090): bloqueia
  `: float` em campo cujo nome contém
  `amount|valor|brl|saldo|money|total|price|cost|despesa|receita|
  aporte|patrimonio|capital|dinheiro|preco`. Detecta apenas linhas
  **adicionadas** (`git diff --cached`) — 79 legados passam. Skip
  explícito para `tolerance|rate|percentage|ratio`. `_is_rename()`
  (adicionado pós-A6g.2c) consulta `git diff --name-status
  --find-renames=90%` para pular arquivos renomeados (git trata todas
  as linhas como adicionadas em rename puro, produzindo false positive
  em campos legados).
- **Test AST `test_no_any_in_boundary.py`**: varre
  `backend/app/schemas/**/*.py`; 12 arquivos em `LEGACY_FILES` (4
  OPAQUE permanentes — config blob / opaque responses; 8 com track
  previsto). Arquivos fora de LEGACY_FILES não podem ganhar `Any`.
- **Test AST `test_no_forbidden_names.py`**: fail-safe do
  `check_forbidden_names.py` — varre `backend/app/`, `pipeline/`,
  `scripts/`, `frontend/src/` no CI mesmo sem diff.

### Gate progressivo (`dev/check_code_style_regression.py`)

Roda `audit_code_style.py` em CI, compara contagens por categoria
com `dev/code_style_baseline.json`. Exit 1 se QUALQUER categoria tem
MAIS ofensores — legado pode apenas decrescer. `--save-baseline`
atualiza snapshot após sweep. Categorias em baseline (2026-04-22):
P1_long_functions=874, P2_long_files=27, P3_dict_str_any_boundary=82,
P4_optional_no_default=12, P5_float_money=79, P6_forbidden_names=5,
P7_multiparagraph_docstring=825, P8_what_comments=51,
P9_deep_nesting=239, T3_ts_long_functions=29.

### Convenções de exceção

- `# noqa: RULE — motivo citável (ADR-XXX / A6g.Nx)` — nunca sem
  referência rastreável.
- Allowlist em arquivo compilado (`[tool.ruff.lint.per-file-ignores]`,
  `ALLOWLIST` dict em check scripts, `LEGACY_FILES` em tests AST) —
  nunca `# noqa` espalhado para categorias amplas.
- Legado migra para clean: quando um arquivo sai de LEGACY_FILES, o
  test extra `test_legacy_files_still_legacy_or_migrated` detecta e
  exige remoção para promover ao gate bloqueante.

**Consequências:**

- ✅ PRs novos bloqueados imediatamente em: `any` TS, `float` money,
  filenames genéricos, `Any` em DTOs cleanos, imports quebrados,
  redefinições, sintaxe inválida.
- ✅ Gate progressivo impede a categoria inteira piorar — sweep
  A6g.6b pode decrementar P1/P7/P9 sem medo de regressão silenciosa.
- ✅ Baseline único em `dev/code_style_baseline.json` — versionado,
  revisável em PR, data-stamped.
- ✅ ESLint rebuild do ambiente — sai do `next lint` (deprecado em
  Next 16) para `eslint src/` direto; hook pré-commit pula limpo se
  `frontend/node_modules` ausente (dev), CI sempre bloqueia.
- ⚠️ Seleção ruff conservadora deixa ~525 ofensores auto-fixáveis
  fora do gate inicial (I001 imports order, F541 f-string-sem-
  placeholder). A6g.6b roda `ruff check --fix .` em sweep dedicado
  e remove esses ignores.
- ⚠️ `ruff format` reformataria 422 arquivos — **não** ativado. A6g.6b
  roda `ruff format .` em sweep dedicado e ativa o hook.
- ⚠️ `max-lines` / `max-lines-per-function` em warn (74 funções acima
  de 60 linhas em frontend) — promovidos a error só após sweep A6g.6b.
- ⚠️ Baseline JSON é grande (~26 KB) por enumerar ofensores
  individualmente. Aceito: diff revela exatamente qual categoria
  regrediu, facilita revisão.
- ❌ Allowlist dinâmica (por linha, via comentário inline) não
  adotada — força allowlist estática central, revisável em PR, sem
  ruído no código.

**Escopo deferido (follow-ups explícitos):**

- **A6g.6b**: sweep dedicado `ruff check --fix .` + `ruff format .` +
  ativa I001/F541 no gate + promove `max-lines*` de warn para error.
- **A6g.6c** (opcional): ativa rules `UP` (pyupgrade), `B` (bugbear),
  `C90` (mccabe complexity=10) no ruff após sweep.
- **A6g.2c** ✅ 2026-04-22: renomeou `pipeline/llm/service.py` →
  `pipeline/llm/litellm_client.py`; ALLOWLIST do `forbidden-names`
  zerada; hook `check_float_money.py` ganhou `_is_rename()` para não
  disparar em renames puros (`git mv` faz git ver todas as linhas
  como adicionadas, triggering false positive em campos legados).
- **A6e.3c** (sweep): elimina `dict[str, Any]` em DTOs não-OPAQUE
  (`family_member/*`, `category/mapper.py`), promove 4 arquivos de
  LEGACY_FILES para CLEAN_FILES em `test_no_any_in_boundary.py`.
- **Go enforcement** (A6g.7 follow-up): quando primeiro serviço Go
  entrar, ativa `forbidigo`/`depguard` em `.golangci.yml` banindo
  `interface{}`, `fmt.Println` fora de `cmd/`, imports cruzando
  boundary.

**Artefatos:**

- `pyproject.toml` — `[tool.ruff]` + `[tool.ruff.lint]` + `[tool.ruff.format]`.
- `frontend/eslint.config.mjs` — flat config ESLint v9.
- `frontend/package.json` — deps eslint@9, @typescript-eslint/*,
  eslint-plugin-react{,-hooks}, globals; script `lint: eslint src/`.
- `.pre-commit-config.yaml` — hooks `ruff`, `eslint-frontend`,
  `forbidden-names`, `float-money`.
- `dev/run_eslint_frontend.sh` — wrapper para pre-commit ESLint.
- `dev/check_forbidden_names.py`, `dev/check_float_money.py`,
  `dev/check_code_style_regression.py` — gates custom.
- `dev/code_style_baseline.json` — snapshot audit 2026-04-22.
- `backend/tests/architecture/test_no_any_in_boundary.py`,
  `test_no_forbidden_names.py` — AST fail-safes.
- `.github/workflows/ci.yml` — jobs `ruff`, `frontend-lint`,
  `code-style-regression` + `all-green` depende deles.
