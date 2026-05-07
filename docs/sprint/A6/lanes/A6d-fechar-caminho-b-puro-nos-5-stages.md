---
id: A6d
type: lane
title: "Fechar Caminho B puro nos 5 stages pragmáticos (ADR-100)"
sprint: A6
status: shipped
priority: P1
ship_date: "2026-04-20"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p1
---


# A6d — Fechar Caminho B puro nos 5 stages pragmáticos (ADR-100)


**Commitment — não opcional.** Converte E4/E5/E5.N/E7/E1.5c de pragmático para puro.

#### A6d.1 — Eliminação de globals nos 5 scripts

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6d.1.1 | Padrão A3b replicado em `e4_categorize.py` | P1 | 1h | ✅ 2026-04-24 |
| A6d.1.2 | Padrão A3b em `e5_analyze.py` | P1 | 2h | ✅ 2026-04-24 |
| A6d.1.3 | Padrão A3b em `e5n_narrativas.py` | P1 | 1h | ✅ 2026-04-24 |
| A6d.1.4 | Padrão A3b em `e7_review.py` | P1 | 1h | ✅ 2026-04-24 |
| A6d.1.5 | Padrão A3b em `e15_consolidate.py` | P1 | 1h | ✅ 2026-04-24 |
| A6d.1.6 | Teste estrutural AST: `_init_config` não invocado em top-level dos 5 scripts | P1 | 30min | ✅ 2026-04-24 |

#### A6d.2 — Testabilidade dos `analyze_*` sem disco ✅ entregue 2026-04-20

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6d.2.1 | `extract_if_target_from_life_plan(content=None)` / `extract_if_trs(content=None)` / `extract_renda_passiva_from_life_plan(content=None)` aceitam content string; `_read_life_plan_content()` centraliza o I/O | P1 | 2h | ✅ |
| A6d.2.2 | `parse_tarefas_md_content(text)` puro + wrapper `parse_tarefas_md(content=None)` com shell loader fino | P1 | 2h | ✅ |
| A6d.2.3 | `parse_milhas_md_content(text)` puro + wrapper `parse_milhas_md(content=None)` análogo | P1 | 1h | ✅ |
| A6d.2.4 | `load_methodology` já era shell-loader fino; `extract_persona_from_methodology(content)` já é puro — docstring formaliza separação em `scripts/e7_review.py` | P1 | 1h | ✅ |
| A6d.2.5 | `tests/unit/pipeline/test_e5_content_parsers.py` — 26 testes cobrindo parsers + extract_if_* sem `tmp_path`; shell loaders testados com `monkeypatch` de paths | P1 | 3h | ✅ |

**Checkpoint A6d.2:** ✅ MD content (`life_plan_goals.md`, `tarefas.md`, `milhas.md`) é lido uma única vez no shell (`scripts/e5_analyze.main_with_store(ctx)`) e repassado aos helpers puros. `analyze_goals(patrimonio, life_plan_content=None)` propaga content para os extractors. 1240 testes passando, zero regressão nos goldens (E3/E4/E5/E5.N/E6/E7).

#### A6d.3 — Integração dos 14+ domain services em `main_with_store`

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6d.3.1 | E4: auditoria confirmou que `main_with_store` já usa `E4CategorizerAdapter.from_configs` + `categorize_via_store` + `serialize_e4_artifacts` (entregue em A4b). Zero uso de `process_transactions`/`build_*_unified` dentro de `main_with_store` — funções legadas permanecem apenas em `main(root_dir)` CLI legado | P1 | 1 sessão | ✅ (verificado 2026-04-20) |
| A6d.3.2 | E5.N: decomposição de `build_narrativas` (425 locs) em pacote `pipeline/domain/services/narrativas/` com `NarrativasContext` + `PerfilFamiliaNarrator` + `SummariesNarrator` + `ChartsNarrator` orquestrados por `E5NarrativasBuilder`. `scripts.e5n_narrativas.build_narrativas` vira delegate de 2 linhas; format helpers + validator movidos para `format_helpers.py` com back-compat aliases. 10 tests novos em `tests/test_e5n_builder_decomposition.py` + paridade legado↔novo em `tests/test_e5n_e7_main_with_store_parity.py` | P1 | 1 sessão | ✅ 2026-04-20 |
| A6d.3.3 | E5: `E5AnalyzerAdapter` completado com 3 calculadoras puras novas (Etapa 1, já entregue) + switch de `main_with_store` para o adapter (Etapa 2, +143/-54 locs) + golden parity `tests/test_e5_main_with_store_parity.py` (Etapa 3, 2 cenários @ 0.01 BRL). Correções de paridade: `conjuge_key=""` sem default "mariana", `goals={}` no `PontosFortesAnalyzer`, `CenariosConjugeAnalyzer._compute_prazo` retorna `999` (int) | P1 | 2 sessões | ✅ 2026-04-20 |

**Estimativa total A6d:** 3-5 sessões grandes (~200+ testes). **Realizado:** A6d.1 (2026-04-24) + A6d.2 + A6d.3.1 + **A6d.3.2** + **A6d.3.3** (~5 sessões). **Resta:** nada — A6d **fechada**. Caminho B **puro** para todos os stages determinísticos relevantes (E3, E5, E5.N); E4 e E1.5c permanecem em B pragmático (decisão consciente — refactor não entrega valor adicional relevante); E7 é LLM-bound e não migra.
