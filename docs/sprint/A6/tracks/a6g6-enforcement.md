---
id: TRACK-a6g6-enforcement
type: track
title: "Track A6g.6 — Enforcement automatizado de code style"
sprint: A6
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a6
  - status/consumed
---

# Track A6g.6 — Enforcement automatizado de code style

> **Lane ID:** A6g.6
> **Branch prefix:** `agent/a6g6-enforcement/*`
> **Depende de:** A6g.2 r1 ✅ · A6g.4 (r1+r2+r3) ✅ · A6g.5 ✅ (3 sweeps fecharam; enforcement impede regressão)
> **Paralelo com:** A6e.4 (🚧 thin routers) · A6e.events (☐ domain events) — zero overlap de arquivos **se** respeitar escopo (esta lane toca `pyproject.toml`, `.pre-commit-config.yaml`, `frontend/eslint.config.*`, `.github/workflows/`, `backend/tests/architecture/`, `dev/`)
> **Conflita com:** commits simultâneos em `.pre-commit-config.yaml`, `pyproject.toml`, `.github/workflows/ci.yml`, `frontend/package.json`. Nenhuma outra lane ativa toca esses — safe.
> **Onda:** 3
> **Índice de prompts:** [README.md](../../../../README.md)
> **Fonte de verdade:** [CLAUDE.md §Code style](../../../../CLAUDE.md#code-style) · [docs/archive/audits/](../../../archive/audits/) baseline A6g.1

> **Objetivo:** transformar as regras do CLAUDE.md §Code style em **gates
> automatizados** (pre-commit + CI + testes AST) que impedem regressão
> dos sweeps já feitos. Gates **imediatos** bloqueiam código novo com
> violação; gates **progressivos** usam allowlist de legado que só pode
> decrescer.

---

## Por que esta lane agora

1. **3 sweeps fecharam** (A6g.2 r1, A6g.4 r1+r2+r3, A6g.5). Sem enforcement, novos PRs reintroduzem os padrões que acabamos de eliminar — desperdiça ~15 sessões de trabalho.
2. **Audit A6g.1** (`dev/audit_code_style.py`) já existe como medidor (2171 ofensores catalogados em 2026-04-22). Falta **ativar como gate de CI** comparando contra baseline.
3. **Baseline está fresco** — mais simples definir allowlist agora do que 3 meses depois quando sweeps mais forem feitos.
4. **Destrava F7** — produção precisa CI limpo e bloqueante; code style gate é pré-requisito para não gerar débito silencioso em F7A-F7E.

---

## Atenção — estado atual é menos configurado do que parece

**Verificação feita (2026-04-22):**

- **Ruff:** `pyproject.toml` não tem `[tool.ruff]` block. Projeto roda Python sem ruff configurado — `pre-commit` não tem hook de ruff. Esta lane **configura do zero**.
- **ESLint:** `frontend/` usa `next lint` (default do Next.js). Não há `.eslintrc.*` nem `eslint.config.*` explícito. Esta lane **adiciona config explícita** com regras bloqueantes.
- **Pre-commit:** `.pre-commit-config.yaml` tem 5 hooks custom locais (`forbidden-paths`, `commit-msg-format`, `design-tokens-sync`, `report-layout-codegen`, `main-drift-check`) + hooks comunitários (trailing-whitespace, etc.). **Sem hook de lint** de Python ou TS.
- **CI (`.github/workflows/ci.yml`):** job `lint` roda `pre-commit run --all-files` apenas. Não roda `ruff check` direto, nem `eslint`, nem `tsc --noEmit`.
- **Testes AST existentes:** `backend/tests/architecture/test_routers_thin.py` (A6e.4) — padrão a replicar.
- **`dev/audit_code_style.py`:** script de auditoria (A6g.1) com flag `--strict` que exit-code 1 se ofensores >0 em categorias escolhidas. Hoje **não roda em CI**.

---

## Regras inegociáveis

Do CLAUDE.md §Code style + ADRs:

1. **Gate imediato** bloqueia código **novo** que viola regra específica; legado fica em allowlist com TODO (`P6 forbidden names`, `P5 float money`, `T1 TS any`).
2. **Gate progressivo** usa **allowlist decrescente** — se novo commit deixa categoria com MAIS ofensores que baseline, CI falha. Legado na allowlist pode apenas **diminuir** (`P1 long functions`, `P2 long files`, `P3 Dict[str, Any]`).
3. **Nunca** `# noqa` sem motivo citável (ADR/track de backlog). Forma: `# noqa: RULE — motivo breve (ADR-XXX / A6g.Nx)`.
4. **Auditor é fonte de verdade** — `dev/audit_code_style.py --strict` deve passar em CI. Baseline fica em `dev/code_style_baseline.json` (novo artefato).
5. **Legado**: ofensores mapeados em A6g.1 ficam em allowlist explícita; cada entrada cita track (ex.: `"e5_analyze.py::main": "A6g.2b pós-A6c.3"`).
6. **Exceções aceitas** (CLAUDE.md §Code style + sweeps):
   - Bank parsers em `scripts/e2/banks/*.py` podem ter funções 25-40 linhas.
   - Generated files (`frontend/src/generated/`, OpenAPI snapshot, Pydantic codegen) — fora do escopo.
   - Goldens de paridade que comparam estruturas inline — mantidos.
7. **Dinheiro nunca é `float`** (ADR-090): P5 gate procura `: float` em campos com nome `amount|valor|brl|saldo|money|total|price|cost` — bloqueia código novo.
8. **Sem `any` em TS** (§Code style): ESLint rule `@typescript-eslint/no-explicit-any` = `error`, não `warn`.
9. **Preserve comentários existentes em refactor.**

---

## Alvo estrutural

```
pyproject.toml                          # + [tool.ruff] + [tool.ruff.lint] blocks
frontend/eslint.config.mjs              # novo — config flat ESLint v9
.pre-commit-config.yaml                 # + hooks ruff + eslint + grep
.github/workflows/ci.yml                # + jobs ruff-check, eslint-check, audit-regression
dev/code_style_baseline.json            # novo — snapshot da 2ª rodada audit (baseline decrescente)
dev/code_style_allowlist.yaml           # novo — exceções citando track/ADR
backend/tests/architecture/
  test_routers_thin.py                  # já existe (A6e.4)
  test_no_any_in_boundary.py            # novo — Dict[str, Any] em boundary HTTP
  test_no_forbidden_names.py            # novo — filenames proibidos (utils.py, helpers.py, manager.py)
```

---

## Targets — 5 slices atômicos

### Slice 1 — Ruff config inicial + hook pre-commit

**Objetivo:** ativar ruff com regras **imediatas** (bloqueiam código novo, allowlist legados).

1. **`pyproject.toml`** — adicionar `[tool.ruff]` + `[tool.ruff.lint]`:
   ```toml
   [tool.ruff]
   line-length = 100
   target-version = "py311"
   extend-exclude = [
       "backend/app/generated",  # codegen
       "frontend/src/generated", # codegen
       "_archive",
       "_scratch",
   ]

   [tool.ruff.lint]
   # Ativar progressivamente — começar com o que já passa
   select = [
       "E",   # pycodestyle errors
       "F",   # pyflakes
       "I",   # isort
       "W",   # pycodestyle warnings
       "B",   # flake8-bugbear
       "UP",  # pyupgrade
       "C90", # mccabe complexity
   ]
   # PLR0915 max-statements e C901 complexity ficam para slice 2 (progressive)
   ignore = [
       "E501",  # line-length duplica pycodestyle; ruff já tem line-length acima
   ]

   [tool.ruff.lint.mccabe]
   max-complexity = 10
   ```

2. **`.pre-commit-config.yaml`** — adicionar hook ruff:
   ```yaml
   - repo: https://github.com/astral-sh/ruff-pre-commit
     rev: v0.6.0
     hooks:
       - id: ruff
         args: [--fix, --exit-non-zero-on-fix]
       - id: ruff-format
   ```

3. **`pre-commit run ruff --all-files`** — rodar localmente, estabelecer **baseline de ofensores**. Qualquer erro crítico (`F` pyflakes) é consertado inline. Demais ficam em `per-file-ignores` em `pyproject.toml` com comentário citando track:
   ```toml
   [tool.ruff.lint.per-file-ignores]
   "scripts/e2/banks/*.py" = ["C901"]  # bank parsers — CLAUDE.md exceção
   "scripts/e5_analyze.py" = ["PLR0915", "C901"]  # A6g.2b pós-A6c.3
   ```

4. **CI** — adicionar step em `.github/workflows/ci.yml`:
   ```yaml
   - name: Ruff check
     run: pip install ruff==0.6.0 && ruff check . && ruff format --check .
   ```

**Gate:** `pre-commit run --all-files` verde; `pytest backend/tests -q` + `pytest tests -q` sem regressão (ruff pode ter auto-fixado imports; revisar diff).

**Commit 1:** `infra(lint): configura Ruff inicial + hook pre-commit + CI gate (A6g.6 · slice 1)`

### Slice 2 — ESLint config explícito + `no-explicit-any` bloqueante

**Objetivo:** configurar ESLint com regras que impedem regressão do sweep A6g.4 (T1 `any`, T2 long files).

1. **`frontend/package.json`** — adicionar deps:
   ```json
   "devDependencies": {
     "eslint": "^9.0.0",
     "@typescript-eslint/eslint-plugin": "^8.0.0",
     "@typescript-eslint/parser": "^8.0.0",
     "eslint-plugin-react": "^7.35.0",
     "eslint-plugin-react-hooks": "^5.0.0"
   }
   ```

2. **`frontend/eslint.config.mjs`** — flat config (ESLint v9):
   ```js
   import tsParser from "@typescript-eslint/parser";
   import tsPlugin from "@typescript-eslint/eslint-plugin";
   import reactPlugin from "eslint-plugin-react";

   export default [
     {
       files: ["src/**/*.ts", "src/**/*.tsx"],
       ignores: ["src/generated/**"],  // codegen
       languageOptions: { parser: tsParser },
       plugins: { "@typescript-eslint": tsPlugin, react: reactPlugin },
       rules: {
         "@typescript-eslint/no-explicit-any": "error",  // T1 imediato
         "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
         "max-lines": ["warn", { max: 500, skipBlankLines: true, skipComments: true }],  // T2 progressivo (warn, não error)
         "max-lines-per-function": ["warn", { max: 40, skipBlankLines: true }],  // T3 progressivo
       },
     },
   ];
   ```

3. **`.pre-commit-config.yaml`** — adicionar hook ESLint local:
   ```yaml
   - id: eslint-frontend
     name: "ESLint: frontend/"
     entry: bash -c 'cd frontend && npx eslint src/'
     language: system
     files: ^frontend/src/.*\.(ts|tsx)$
     pass_filenames: false
   ```

4. **CI** — adicionar step:
   ```yaml
   - name: ESLint
     run: cd frontend && npm run lint
   ```

**Gate:** `cd frontend && npm run lint` verde; Vitest + E2E sem regressão.

**Commit 2:** `infra(lint): ESLint explícito + no-explicit-any bloqueante (A6g.6 · slice 2)`

### Slice 3 — Pre-commit hooks grep para gates imediatos P5/P6

**Objetivo:** hooks leves (<100ms) que grep-bloqueiam padrões em arquivos staged.

1. **`dev/check_forbidden_names.py`** (novo):
   ```python
   """Bloqueia arquivos com nomes proibidos (CLAUDE.md §Code style).

   Filenames proibidos: utils.py/ts, helpers.py/ts, manager.py/ts, handler.ts.
   Classes proibidas: Manager, Service (sozinho), Utils, Helpers.
   """
   # Usa sys.argv (lista de arquivos staged). Exit 1 se qualquer um violar.
   ```

2. **`dev/check_float_money.py`** (novo):
   ```python
   """Bloqueia float em campos monetários (ADR-090).

   Pattern: `:\s*float\b` em campo cujo nome contém amount|valor|brl|saldo|money|total|price|cost.
   Skip fields com docstring que diz "percentage" ou "rate" (explícito).
   """
   ```

3. **`.pre-commit-config.yaml`** — adicionar ambos:
   ```yaml
   - id: forbidden-names
     name: "Proíbe filenames/classes genéricos (utils, helpers, manager)"
     entry: python dev/check_forbidden_names.py
     language: system
     pass_filenames: true
     types: [python]

   - id: float-money
     name: "Proíbe float em campo monetário (ADR-090)"
     entry: python dev/check_float_money.py
     language: system
     pass_filenames: true
     types: [python]
   ```

**Gate:** hooks novos passam em `pre-commit run --all-files` (talvez com allowlist para legados). Teste negativo: adicionar arquivo `backend/app/services/utils.py` temporariamente — hook deve falhar; remover.

**Commit 3:** `infra(lint): pre-commit hooks para nomes proibidos + float money (A6g.6 · slice 3)`

### Slice 4 — Testes AST: no-`any`-in-boundary + no-forbidden-names

**Objetivo:** complementar ruff/eslint com verificações AST que linters não fazem bem.

1. **`backend/tests/architecture/test_no_any_in_boundary.py`** (novo, ~80 linhas):
   - Parse AST de `backend/app/schemas/**/*.py` (Pydantic DTOs).
   - Falha se encontrar `Dict[str, Any]`, `dict[str, Any]`, `Any` em campo top-level.
   - `ALLOWLIST` decrescente documenta legados com track (A6e.3b resolveu alguns; mapear restantes).

2. **`backend/tests/architecture/test_no_forbidden_names.py`** (novo, ~60 linhas):
   - Itera `backend/app/`, `pipeline/`, `scripts/` procurando arquivos `utils.py`/`helpers.py`/`manager.py`.
   - `ALLOWLIST` para `pipeline_common.py` (exceção histórica) — mas proíbe novos.
   - Idem para `frontend/src/**/*.ts` (exceto `cn.ts` que é rename validado em A6g.4).

**Gate:** ambos passam com ALLOWLIST preenchida de acordo com baseline; quebram se alguém adicionar novo offender fora da allowlist.

**Commit 4:** `test(architecture): no any em boundary + no forbidden names (A6g.6 · slice 4)`

### Slice 5 — Audit regression em CI + ADR-114 + docs

**Objetivo:** audit roda em CI; falha se baseline piorar.

1. **`dev/code_style_baseline.json`** (novo) — gerado por `python dev/audit_code_style.py --format json --output-dir dev/` com flag `--save-baseline`. Snapshot da 2ª rodada (pós-A6g.2/.4/.5/.3/.3b/.5/.7 — ~1800 ofensores estimados). Commit junto.

2. **`dev/check_code_style_regression.py`** (novo, ~50 linhas):
   - Roda `audit_code_style.py` atual.
   - Compara contagens por categoria com `dev/code_style_baseline.json`.
   - Exit 1 se QUALQUER categoria com gate progressivo tem MAIS ofensores que baseline. Exit 0 caso contrário (permite baseline decrescer).

3. **CI step** em `.github/workflows/ci.yml`:
   ```yaml
   - name: Code style baseline regression
     run: python dev/check_code_style_regression.py
   ```

4. **ADR-114** em `docs/DECISIONS.md` — "Code style enforcement (A6g.6)": design + gate imediato vs progressivo + estratégia de baseline decrescente.

5. **CHANGELOG** + **BACKLOG**: A6g.6 ☐ → ✅ + data; mencionar allowlist inicial e política de atualização.

**Gate:** CI inteiro verde em PR de teste com mudança legítima; CI vermelho em PR de teste que introduz violação nova.

**Commit 5 (docs hotspot, atomic ≤5min):** `docs(a6g.6): ADR-114 + CHANGELOG + BACKLOG — enforcement automatizado ativo`

---

## Sequência de execução

### 1. Setup

```bash
git fetch origin
git worktree list                              # confirma zero worktree a6g6-*
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/ | head -15
git checkout -b agent/a6g6-enforcement/$(date +%Y%m%d-%H%M)
```

### 2. Baseline

```bash
pre-commit run --all-files 2>&1 | tail -10    # baseline do pre-commit antes
pytest backend/tests -q 2>&1 | tail -3
pytest tests -q 2>&1 | tail -3
cd frontend && npm test -- --run 2>&1 | tail -3 && cd ..
python dev/audit_code_style.py --format json --output-dir _scratch/a6g6_baseline/
# anotar contagens por categoria — será o baseline a proteger
```

### 3. Slices 1 → 5 na ordem acima

Cada slice = 1 commit atômico + gate verde. Nunca misture.

### 4. Gates de push final

```bash
pre-commit run --all-files                     # tudo verde (inclui hooks novos)
pytest backend/tests -q                        # zero regressão
pytest tests -q                                # zero regressão
cd frontend && npm run lint && npm test -- --run && cd ..
python dev/check_code_style_regression.py      # verde contra baseline commitado

git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest backend/tests -q

git push origin HEAD:main
```

---

## Critérios de aceite (binários)

- [ ] `pyproject.toml` tem `[tool.ruff]` + `[tool.ruff.lint]` blocks; `ruff check .` passa.
- [ ] `frontend/eslint.config.mjs` existe; `cd frontend && npm run lint` passa com `@typescript-eslint/no-explicit-any: error`.
- [ ] `.pre-commit-config.yaml` tem novos hooks: `ruff`, `ruff-format`, `eslint-frontend`, `forbidden-names`, `float-money`. Todos passam em `pre-commit run --all-files`.
- [ ] `.github/workflows/ci.yml` tem 3 steps novos: `ruff check`, `eslint`, `audit regression`. Todos verdes em CI.
- [ ] `backend/tests/architecture/test_no_any_in_boundary.py` + `test_no_forbidden_names.py` existem; `pytest backend/tests/architecture/ -q` verde.
- [ ] `dev/code_style_baseline.json` existe e é commitado; `dev/check_code_style_regression.py` passa contra o baseline.
- [ ] ADR-114 escrita em `docs/DECISIONS.md`.
- [ ] CHANGELOG + BACKLOG atualizados (A6g.6 ☐ → ✅).
- [ ] Teste negativo: PR local introduzindo `Dict[str, Any]` em boundary OU `: any` em TS OU arquivo `utils.py` — todos bloqueados pelo CI.
- [ ] `pytest backend/tests -q` + `pytest tests -q` + frontend unit + E2E @critical: zero regressão.

---

## Rollback criteria — ABORTE se

- Ruff config desencadeia mais de ~30 erros em `per-file-ignores` que precisariam cadastrar — indica que base-line precisa ser mais permissiva inicialmente. Rever seleção de regras (`B`, `UP`, `C90` podem ser muitos — comece com `E`, `F`, `I`, `W`).
- ESLint config desencadeia ≥100 erros — config muito estrita. Reduzir a `@typescript-eslint/no-explicit-any` + `no-unused-vars` apenas no primeiro slice; outras regras virão em sub-fases.
- `pre-commit run --all-files` fica >60s — hooks novos lentos. Otimizar (`types: [python]` + `pass_filenames: true` filtra staged; allowlist em arquivo compilado).
- `pytest backend/tests -q` regridi em ≥2 tests — ruff auto-fix alterou algo não esperado. Revisar diff do `ruff --fix`; reverter ou marcar fix como opt-in.
- Teste AST em `backend/tests/architecture/` cobre de forma muito ampla (>200 entries em allowlist) — refinar allowlist ou regra.

Em rollback: `git reset --hard origin/main`; anunciar qual slice quebrou; issue aberta para ajustar escopo.

---

## Anti-patterns a evitar

- **Ativar regras em lote "pra pegar tudo de uma vez".** Incremental: slice 1 = ruff base; slice 2 = ESLint base; só depois progressivos. Cada slice independente.
- **Usar `# noqa` sem comentário de motivo.** Cada `# noqa: RULE` deve citar track/ADR. `# noqa: PLR0915 — e5_analyze, A6g.2b pós-A6c.3`.
- **Colocar allowlist em `# noqa` espalhado.** Para categorias progressivas com muitos offenders, use `[tool.ruff.lint.per-file-ignores]` ou `dev/code_style_allowlist.yaml` — centralizado facilita audit.
- **Migrar código legado pra "passar no lint".** Refactor é escopo de sweep (A6g.2, A6g.4). Esta lane só configura gates; legados ficam em allowlist.
- **Quebrar a suíte de testes pra "ter lint mais limpo".** Se ruff `--fix` mudou behavior (raríssimo, mas possível com `UP`), reverter e desligar a rule.
- **Adicionar gate novo sem baseline explícito.** Toda regra progressiva deve ter entry em `dev/code_style_baseline.json` dizendo "aceitamos X offenders hoje; qualquer número maior = fail".
- **Rodar `audit_code_style.py --strict` em CI como bloqueante imediato.** Baseline primeiro (informativo), ativar bloqueante em slice 5 quando baseline committado.
- **Commits misturando slices.** Slice 1 = ruff. Slice 2 = ESLint. Slice 3 = grep hooks. Slice 4 = AST tests. Slice 5 = docs + regression gate. Rebase limpo exige isso.

---

## Coordenação com outros agentes

| Lane | Status | Overlap |
|---|---|---|
| **A6e.4** thin routers | 🚧 ativo | **Zero overlap de config** — A6e.4 toca `backend/app/api/` + `backend/tests/architecture/test_routers_thin.py`. Você toca `backend/tests/architecture/test_no_any_in_boundary.py` + outros arquivos novos. |
| **A6e.events** domain events | ☐ pode iniciar | **Zero overlap** — A6e.events toca `backend/app/events/` + `backend/app/application/`. |
| **A6e.3** / **A6e.3b** / **A6e.5** / **A6f.1** / **A6g.2 r1** / **A6g.4** / **A6g.5** / **A6g.7** | ✅ mergeadas | Baseline — teus gates preservam. |

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- pyproject.toml .pre-commit-config.yaml .github/workflows/ci.yml docs/CHANGELOG.md docs/BACKLOG.md docs/DECISIONS.md
```

Se agente mergeou hotspot <30min, espere 2min, anuncie, commite no **mesmo turno** (≤5min).

**Sync periódico (sessão >1h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# Se A6e.4 merge, pode ter alterado backend/tests/architecture/ — rebase incremental
```

---

## O que esta lane NÃO entrega

- **Sweep de código legado adicional** — não. Escopo é só gates. Legados ficam em allowlist.
- **Ruff rules completas do universo** — seleção conservadora (E/F/I/W/B/UP/C90). Rules adicionais (`N` naming, `D` docstrings, `ANN` annotations) podem vir em A6g.6b se necessário.
- **Gate progressivo automático de PR size, lint warnings, etc.** — fora de escopo. Tá tudo focado em code style.
- **Bloqueio de `multiparagraph_docstring` (P7, 806 offenders)** — severidade baixa/info; não bloqueia. Ficam em allowlist como referência, sem gate ativo (a auditoria pega por osmose).
- **Migração de Pydantic v1→v2** se ruff sugerir — fora de escopo, abre track dedicado.
- **Tests AST genéricos** para "toda regra em CLAUDE.md" — alvos pontuais (boundary `Any`, forbidden names). Outras regras são cobertas pelo audit ou pelo ruff.

---

## Referências

- [CLAUDE.md §Code style](../../../../CLAUDE.md#code-style) — fonte das regras
- [docs/archive/audits/](../../../archive/audits/) — baseline A6g.1 (2171 ofensores)
- [BACKLOG §A6g](../../../BACKLOG.md) — trilho completo de sweeps
- **Ruff** — https://docs.astral.sh/ruff/rules/
- **ESLint flat config** — https://eslint.org/docs/latest/use/configure/configuration-files-new
- **Teste AST modelo:** `backend/tests/architecture/test_routers_thin.py` (A6e.4)
- **Auditor existente:** `dev/audit_code_style.py` (A6g.1)
- Prompts paralelos: [track_a6e4](a6e4-thin-routers.md), [track_a6e_events](a6e-events-domain-events.md)
