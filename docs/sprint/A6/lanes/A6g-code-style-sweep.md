---
id: A6g
type: lane
title: "Code Style Sweep (CLAUDE.md §Code style)"
sprint: A6
status: in_progress
priority: P1
adrs: ["[[ADR-090]]", "[[ADR-113]]", "[[ADR-114]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/in-progress
  - priority/p1
---


# A6g — Code Style Sweep (CLAUDE.md §Code style)


**Objetivo:** revisar e aplicar o `## Code style` de [CLAUDE.md](../CLAUDE.md) em todo o código existente — Python (`pipeline/`, `scripts/`, `backend/`), TypeScript (`frontend/`) e preparatório para Go (A6f). Corrige drift acumulado antes que vire convenção implícita.

**Premissa:** drift existe e é silencioso. Sem um sweep deliberado, o estilo novo vale só para código futuro; código legado continua ofendendo (funções gigantes em `e5_analyze.py`, `Dict[str, Any]` em boundaries antigos, nomes genéricos sobreviventes, docstrings multi-parágrafo, comentários WHAT). Sweep + enforcement automatizado congelam o estilo como contrato.

| # | Sub-fase | Entrega | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6g.1 | **Auditoria inicial** — script `dev/audit_code_style.py` + pacote `dev/_audit_cs_internals/`. Mede drift em P1-P10 (Python) e T1-T5 (TypeScript). Output: `_scratch/code_style_audit_<date>.{json,md}`. Primeira rodada 2026-04-21: **2047 ofensores** (462 high, 556 med, 1001 low, 28 info) em 467 py + 159 ts. Top alvos: `scripts/e6_render.py` (3875 linhas), `scripts/e5_analyze.py` (2862), `scripts/e_reset.py::main` (372 linhas). Dogfood passa `--strict`. Roda em ~2s | 1 sessão | ✅ (2026-04-21) |
| A6g.2 | **Pipeline Python** (`pipeline/`, `scripts/`, `tests/fixtures/`) — aplicar code style. **1ª rodada defensiva** (`docs/agent_prompts/track_a6g2_pipeline_style_sweep.md`): Tier 1 (`e_reset::main`, `pdf_generator.py`, `e0_audit.py`) sem goldens; Tier 2 opcional (`charts_narrator.narrate`, `pipeline_task.run_pipeline_task`). **Fora de escopo:** `e3/e4/e5/e5n/e6/e7_*.py` (goldens) e `main(root_dir)` legado (A6c.3 vai deletar) → 2ª rodada (A6g.2b) pós-A6c.3. **1ª rodada 2026-04-21:** T1.a `e_reset.main` 372→27 linhas; T1.b `pdf_generator.py` 1067→29 (shim) + pacote `tests/fixtures/pdf/` com 11 bancos + formatters + dispatcher; T1.c `e0_audit.py` 948→238 linhas, checks em `scripts/e0/audit_{helpers,filename,integrity,ledger}.py`; T2.b `run_pipeline_task` 273→58 linhas, 11 helpers por fase do ciclo de vida de `PipelineRun`; T2.a `ChartsNarrator.narrate` 284→36 linhas, 6 métodos privados por grupo de charts (paridade byte-a-byte preservada — 12 goldens E5.N verdes). Pipeline + backend tests em paridade; JSON/HTML outputs + OpenAPI snapshot idênticos | 1-2 sessões (rodada 1) + 2 sessões (rodada 2) | ✅ Tier 1+2 (2026-04-21) + Tier 3 (2026-04-25, A6g.2b — `e7`/`e5n`/`e3`/`e4`/`e5` `main_with_store` decompostos em fases nomeadas; goldens 1458 verdes byte-a-byte; `main(root_dir)` legados intocados) |
| A6g.3 | **Backend Python** (`backend/app/`) — integra com A6e (nomes, DTOs, routers finos). A6e.4 (routers ≤50 linhas) é o chute maior; A6g.3 cobre restante (services, repos, helpers, typing). Prompt: `docs/agent_prompts/track_a6g3_backend_style_sweep.md`. **1ª rodada 2026-04-22:** P4 optional defaults 5→0, P8 what-comments 2→0, P1 decomp em 4 services top (`pipeline_adapter` 5→2, `goal_service` 4→3, `task_service` 4→1, `task_progress_service` 3→0). **2ª rodada 2026-04-22:** P1 decomp em +4 services (`invitation_service` 4→2, `document_processor` 2→1, `canonical_routing` 3→1, `tarefas_md_parser` 2→1) — funções ≥40l caem 72→68. **P5 float money (13) deferido** como **A6g.3b** — wire-compat migration via MoneyBRL type; lane dedicada com prompt pronto. **3ª rodada pendente** (`content_classifier` 621l, `pipeline_service` P1×4, `models/task.py` 308l, repositories P1×5) | 2 sessões por rodada (3 rodadas planejadas) | 🚧 parcial — rodadas 1+2 ✅ 2026-04-22; continuação ☐ |
| A6g.3b | **Money Decimal migration** (follow-up A6g.3) — elimina `P5_float_money` via tipo `MoneyBRL`/`MoneyUSD` = `Annotated[Decimal, BeforeValidator, PlainSerializer(float, when_used='json')]`. Decimal em memória para precisão, number no JSON para wire-compat com frontend. Prompt: `docs/agent_prompts/track_a6g3b_decimal_money_migration.md`. **1ª sessão — slices 1+3 ✅ 2026-04-22:** tipo `MoneyBRL`/`MoneyUSD` + 11 tests; transactions 4 campos + cascata services + 19 tests; OpenAPI zero diff. **2ª sessão — slice 2 ✅ 2026-04-22:** 11 campos goal DTOs (`aporte`/`dolar`/`if_goal`) + math Decimal em `goal_service.py` (`_retorno_mensal_decimal` via `Decimal.ln()/.exp()`, `_pmt_constante_ate_fv`, `_if_meta_targets`, `_aporte_cobrindo_gap_com_patrimonio`, `compute_if/aporte/dolar_derived`); persistência via `model_dump(mode="json")` (SQLAlchemy JSON col não tem codec Decimal); factory `make_if_goal` e use cases `create_if/typed_goal_version` atualizados; OpenAPI snapshot regenerado (Input/Output split por causa do `BeforeValidator`, Output wire `number` puro — frontend TS intacto); 64 tests goal verdes, só 1 assertion ajustada. **Restam (polish):** S0 tolerance rename (P5 pode cair 13→0), S4 frontend sanity manual, S5 baseline regen + ADR-090 nota final. | 2 sessões dedicadas (~1.5h cada) | 🚧 parcial — sessões 1+2 ✅ 2026-04-22; polish ☐ |
| A6g.4 | **Frontend TypeScript** (`frontend/src/`) — eliminar `any` residual, nomes genéricos (`utils.ts`), arquivos >500 linhas (`api.ts` 1880, `pipeline/page.tsx` 1195), hex colors, componentes/hooks >40 linhas. Prompt: `docs/agent_prompts/track_a6g4_frontend_style_sweep.md`. Respeitar codegen em `frontend/src/generated/` (não editar). **1ª rodada 2026-04-21:** T1 9→0, T2 7→6 (api.ts 1880→14 módulos), T3 24→18 (high severity 12→0), T4 1→0, T5 12→0. 53 ofensores → 30 (-43%). **2ª rodada A6g.4b 2026-04-22:** 4 das 6 páginas `>500 l` decompostas (`pipeline` 1195→368, `documents` 801→347, `transactions` 741→399, `dashboard` 515→142) + 3 hooks extraídos de `TransactionsContent`. Ofensores 30 → 27. **3ª rodada A6g.4c 2026-04-22:** as 2 páginas `plano/*` remanescentes decompostas (`plano/page.tsx` 630→152 + 8 módulos; `plano/alocacao/wizard/page.tsx` 533→185 + 7 módulos). **T2 `ts_long_files` zerado** em `frontend/src/`. Ofensores 27 → 29 (líquido +2 por granularidade JSX, T3 high 2→1). Enforcement ESLint segue para A6g.6 | 1-2 sessões por rodada (3 rodadas) | ✅ fechada 2026-04-22 — rodada 1+2+3 mergeadas |
| A6g.5 | **Testes** (`tests/`, `backend/tests/`, `frontend/tests/`) — aplicar code style também em teste: fakes nomeados > `MagicMock` inline, fixtures <20 linhas, nomes descritivos (`test_reconcile_drops_duplicate_when_same_hash` > `test_dedupe_1`). Não relaxa o padrão em teste | 1 sessão | ☐ |
| A6g.6 | **Enforcement automatizado** — transforma regras do CLAUDE.md em gates de CI. Bicameral (imediato + progressivo): (a) Ruff E/F/I/W bloqueante via `[tool.ruff.lint]` + hook pre-commit + CI; (b) ESLint flat config v9 com `@typescript-eslint/no-explicit-any: error`; (c) pre-commit hooks grep `check_forbidden_names.py` + `check_float_money.py` (bloqueia apenas linhas adicionadas); (d) testes AST `test_no_any_in_boundary.py` + `test_no_forbidden_names.py` como fail-safe; (e) `check_code_style_regression.py` compara audit vs `dev/code_style_baseline.json` — legado decresce, nunca cresce. Prompt: `docs/agent_prompts/track_a6g6_enforcement.md` | 1 sessão | ✅ 2026-04-22 (ADR-114) |
| A6g.6b | Follow-up A6g.6: sweep ruff `--fix I001/F541` + `ruff format .` + promove `max-lines` warn→error | 361 auto-fixes (290 I001 + 71 F541) em 263 arquivos; 435 arquivos reformatados; `ignore = [I001, F541]` removido; `ruff-format --check` ativo no pre-commit. `max-lines` (T2, 0 ofensores) promovido a error. `max-lines-per-function` **mantido em warn** — 64 ofensores em 59 components React (tasks/report/config); promoção depende de sweep refactor dedicado (lane futura) | 1 sessão | ✅ 2026-04-22 |
| A6g.2c | Follow-up A6g.6: rename `pipeline/llm/service.py` (filename genérico, estava em ALLOWLIST `check_forbidden_names.py`). Renomeado para `pipeline/llm/litellm_client.py`; 11 imports atualizados; 2 ALLOWLISTs zeradas; hook `check_float_money.py` ganha `_is_rename()` para não bater em renames puros | 0.2 sessão | ✅ 2026-04-22 |
| A6g.7 | **Go prep** (A6f.1 ✅ 2026-04-21 destravou) — config `golangci-lint.yml` com `funlen`, `gocyclo`, `gocognit`, `revive` (nomes) alinhados ao code style. Regras vivem no repo antes do primeiro commit Go | 0.5 sessão | ✅ 2026-04-22 (ADR-113) |

**Estimativa total A6g:** 7-10 sessões médias. Pode rodar em paralelo a A6d/A6e/A6f — mas A6g.3 se beneficia de vir **depois** de A6e.4 (routers finos), e A6g.2 ignora o que A6d está fechando.

**Critérios de aceite globais:**
- Audit A6g.1 roda em <30s e é executado no CI como informativo (não bloqueante inicialmente).
- Cada sweep (A6g.2-.5) deixa o audit com **melhora mensurável** (contador de ofensores cai por categoria). Sem regressão em outras categorias.
- Enforcement A6g.6 bloqueia **apenas código novo**; legado fica em allowlist decrescente com TODO.
- Zero regressão funcional — todos os goldens, testes unit/integração/E2E continuam verdes em cada commit do sweep.

**Exceções aceitas (documentar em ADR se recorrente):**
- Parsers bank-specific em `scripts/e2/banks/` podem ter funções 25-40 linhas quando a alternativa é decomposição que prejudica leitura sequencial do formato.
- Generated files (`frontend/src/generated/`, OpenAPI snapshot, Pydantic models via codegen) — fora do escopo, nunca editar.
- Testes de paridade golden que comparam estruturas grandes inline — mantidos como estão.

> **Pickup de task / diagrama de ondas / lanes abertas:** fonte única no
> topo de [§Sprint A6](#sprint-a6--migração-infradomínio-plano-transversal) —
> subseções "Lanes abertas agora" e "Ondas paralelas — mapa de dependências".

---
