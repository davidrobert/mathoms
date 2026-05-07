---
id: ADR-169
type: adr
title: "Modo incremental estendido aos stages globais E1"
status: Decidido
date: "2026-05-06"
relates_to: ["[[ADR-080]]", "[[ADR-105]]", "[[ADR-157]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 169"]
tags:
  - area/llm
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 49
---

# ADR-169 — Modo incremental estendido aos stages globais E1

**Status:** Decidido • **Data:** 2026-05-06 • **Relaciona** [ADR-080](#adr-080--pipeline-incremental-extrair-só-docs-novos-consolidar-full), [ADR-105](#adr-105--llm-stages-escrevem-via-artifactstore-e1-e-e7-review-llm-não-migram-a6a), [ADR-157](#adr-157--schema-irpf-completo-stage-extract_irpf_full).

**Contexto:** ADR-080 (2026-04-16) introduziu o modo incremental como "E0→E2 incremental + E3→E7 full". A flag `ctx.incremental` + `ctx.incremental_doc_paths` (paths novos com `pipeline_last_run_at IS NULL`) era consumida apenas em [`pipeline/stages/e2.py`](pipeline/stages/e2.py). Sprint A5f e ADR-105/127/157 adicionaram stages globais E1 (`extract_members`, `extract_baseline`, `consolidate_baseline`, `extract_irpf_full`) que rodam **antes** de E2 e operam sobre **todos** os docs do workspace via `rglob` em `data/income_tax_br/`, `data/real_estate/`, `data/vehicles/`, etc. Nenhum desses stages checa `ctx.incremental`.

Sintoma observado em produção: usuário clicou "Processar somente novos", o pipeline reprocessou as 5 declarações IRPF do workspace via LLM em `extract_irpf_full` (~7m + ~$0,70 cada — ADR-157 §11), gastando ~40min e ~$3,50 sem nenhum IRPF novo no upload. Família e baseline têm o mesmo problema, em escala menor.

**Alternativas avaliadas:**

1. **Status quo: globals E1 sempre rodam full em incremental** — simples, mas anula o benefício do modo incremental para o stage mais caro (LLM IRPF). Gasto crescente com o número de declarações no workspace.
2. **Skip total quando `incremental` e zero overlap** (uniforme em todos os globals) — barato, mas em `extract_irpf_full` regride: se o usuário sobe 1 IRPF novo entre 4 antigos, o stage rodaria full sobre os 5 sem necessidade. E em `extract_baseline`, o agregado E1.5 ficaria correto (run inclui todos), mas o custo LLM é proporcional ao número total de declarações.
3. **Per-stage com semântica adaptada à forma do output (escolhida)** — tira proveito da estrutura de cada stage: `extract_irpf_full` filtra per-doc (cada IRPF tem artefato próprio); `extract_baseline` filtra per-doc + agrega o JSON E1.5 lendo todos os `E1.5a` do store (existentes não-tocados + novos da run); `extract_members` faz skip-total se zero overlap, full caso contrário (output é único agregado, merge LLM seguro de delta seria stage novo).

**Decisão:** Adotar (3). Helper compartilhado em [`pipeline/incremental.py`](pipeline/incremental.py) com 4 funções (`normalize_stem`, `allowed_stems`, `filter_to_incremental`, `has_incremental_overlap`). Cada stage chama o helper apropriado conforme a sua semântica de output:

| Stage | Forma | Justificativa |
| --- | --- | --- |
| `extract_irpf_full` (ADR-157) | `filter_to_incremental` per-doc | Cada IRPF gera artefato próprio (`_artifact_key_for(doc)`). Drop dos não-novos preserva artefatos antigos no store. Custo LLM proporcional **só** ao novo. |
| `extract_baseline` (E1.5) | `filter_to_incremental` per-doc + agregado E1.5 lê **todos** `E1.5a` do store (existentes + novos) | Cada IRPF gera `E1.5a` próprio mas o agregado `baseline_patrimonial-1.5_baseline.json` é sobrescrito a cada run. Em modo full mantém comportamento legado (`_aggregate_baselines(per_file_baselines)` da run); em incremental, recombina do store para preservar paridade. |
| `extract_members` (E1) | `has_incremental_overlap` + skip-total se zero | Output é **único** agregado (`members-1b_unified.json`); não há layer per-doc. Merge LLM-safe entre run anterior e novos docs exigiria prompt de consolidação (custo + risco de regredir membros confiáveis). Fora de escopo. |
| `consolidate_baseline` (E1.5c) | sem mudança | Puro Python, idempotente, lê store. Custo negligenciável; já skipa se baseline ausente. |

**Sub-decisões:**

1. **Stem normalization compartilhado.** `normalize_stem(p)` strip de `-0_original` é a mesma regra em `e2.py:_normalize_stem_for_incremental` e `scripts/e2_extract.py:_artifact_key_for_file`. Centralizar evita drift; o helper é a fonte única para qualquer stage futuro que precisar matching incremental.
2. **Modo full não muda em nenhum stage.** Toda lógica nova é guardada por `if ctx.incremental:`. Goldens existentes e paridade legada permanecem intactos. Esta ADR não toca o agregado em modo full — fato relevante: `_aggregate_baselines(per_file_baselines)` em modo full evita reincluir `E1.5a` órfão de doc removido pelo usuário (bug pré-existente em incremental, mas escopo separado).
3. **`extract_members` aceita conservadorismo.** Quando há ao menos 1 doc novo personal, roda full sobre todos os personal docs (até `_MAX_DOCS_PER_RUN`). Custo LLM ~30s — não compensa engenharia de delta agora. Quando merge-of-globals virar padrão (caso surjam outros stages com output agregado puro), abre lane para extrair `MergeAggregatorStrategy` dedicada.
4. **Test gate empírico.** [`tests/pipeline/test_incremental_globals.py`](tests/pipeline/test_incremental_globals.py) cobre os 3 cenários per-stage + 4 helpers. O caso "1 IRPF novo + E1.5a antigo no store → agregado contém ambos" é o gate de paridade que protege futuras mudanças de regredir.

**Consequências:**

- ✅ Custo LLM em `extract_irpf_full` proporcional ao número de **IRPFs novos**, não ao total no workspace. Para o caso reportado (5 IRPFs, 0 novos): de ~$3,50 + 40min para `{"skipped": true}`.
- ✅ `extract_baseline` mantém paridade do agregado consolidado em incremental (read-from-store) sem custo LLM extra.
- ✅ `extract_members` skipa quando irrelevante (sem doc personal novo) e roda full caso contrário — sem risco de regredir merge.
- ✅ Helper único centraliza stem normalization — qualquer global futuro herda comportamento correto chamando `filter_to_incremental` ou `has_incremental_overlap`.
- ⚠️ Em incremental, `extract_baseline` agora lê `E1.5a` órfão do store (caso usuário tenha removido um IRPF do disco mas nunca limpou o store). Mitigado pelo fato de que remoção de doc é fluxo separado e raramente ocorre; em modo full, o comportamento legado segue protegendo.
- ⚠️ `extract_members` em modo incremental ainda paga ~30s de LLM full quando há pelo menos 1 doc personal novo. Aceito; lane específica de delta-merge fica em backlog.
- ❌ `consolidate_baseline` e demais stages não são tocados — esta ADR é estritamente sobre os 3 globais LLM-bound (members/baseline/irpf_full).

**Referências de código:**

- `pipeline/incremental.py` — helper compartilhado.
- `pipeline/stages/extract_irpf_full.py:_select_runnable_docs` — filtro per-doc.
- `pipeline/stages/extract_baseline.py:run` — filtro per-doc + agregação read-from-store em incremental.
- `pipeline/stages/extract_members.py:run` — skip-if-no-overlap.
- `tests/pipeline/test_incremental_globals.py` — regression gate.
