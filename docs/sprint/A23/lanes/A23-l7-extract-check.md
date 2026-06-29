---
id: A23.l7
type: lane
title: "Data Lineage F1 — gate de pureza de extração (ADR-280)"
sprint: A23
plan: PLAN-data-lineage
status: shipped
priority: P1
branch_slug: dl-f1-extract-check
adrs:
  - "[[ADR-280]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a23
  - status/in-progress
  - priority/p1
  - area/data-lineage
  - area/pipeline
---

# A23.l7 — gate de pureza de extração (`check_extract_no_domain_imports`)

> **Plano:** [[PLAN-data-lineage]] · Onda 1 (F1). Conforma à [[ADR-280]] (Decidida);
> não reabre. Co-design `senior-cto` registrado em 2026-06-09.

## Objetivo

Travar o critério de corte Extract|Transform ([[ADR-280]]) com um gate estático: a
**extração pura** não pode importar lógica de domínio. **Esta lane só TRAVA o critério**
— o de-leak das regras que hoje vazam (`tipo_lancamento`, `numero_conta_norm`) é F2.
O gate nasce **verde** (zero vazamentos hoje), então protege contra regressão por
construção.

## Escopo

| Item | Onde | Status |
|---|---|---|
| Gate AST `check_extract_no_domain_imports.py` (irmão de `check_pipeline_boundaries`) | `dev/` | ✅ |
| Registro pre-commit (local) + step CI (`ci.yml`) | `.pre-commit-config.yaml` + `.github/workflows/ci.yml` | ✅ |
| Rótulo `consolidate_baseline` = Transform + pointer em `validate_full_order` (comentários) | `pipeline/stage_spec.py` | ✅ |
| Testes (verde hoje, detecção, exclusão Transform, sentinela, precisão) | `tests/unit/pipeline/test_check_extract_no_domain_imports.py` | ✅ |

## Decisões travadas (co-design)

- **Fonte da superfície = path-based, NÃO rótulo no `StageSpec`.** Rótulo `purity=`
  inflaria o blast radius (goldens, paridade de `STAGE_RENAME_MAP`, orquestrador) sem
  ganho em F1, e nem cobriria `scripts/e2/` (que não tem `StageSpec`). Glob
  `scripts/e2/**/*.py` + `pipeline/stages/extract_*.py` cobre stage de extração novo
  **por construção**; `consolidate_baseline` fica fora por não casar `extract_*`
  (`senior-cto`). Promover a rótulo se F2 provar necessidade.
- **Matcher por COMPONENTE do dotted-path, não substring crua.** `_dedup` como substring
  pegaria `dedup_metrics` (falso-positivo que mina adoção); regra real = componente
  `endswith("_dedup")` / contém `deduplicator` / contém `config_store` / contém
  `category_template`.
- **Proíbe o Protocol `config_store` também** (não só impls), sem exceção pré-cunhada
  (YAGNI) — config tipada vem do value-object concreto (ISP, [[ADR-089]]/[[ADR-097]]),
  não do store. Relaxa com allowlist nominal + ADR se um caso legítimo aparecer.
- **NÃO acopla a `validate_full_order`** (ordem ≠ pureza; acoplar forçaria AST de
  filesystem no import-time do `stage_spec`, que `pipeline/**` carrega em runtime).
  Checks separados; pointer por comentário.

## Conjunto MÍNIMO de F1 (escopo consciente)

Os 3 matchers (`category_template`, `*_dedup`/`*deduplicator*`, `config_store`) são o
**mínimo decidido para F1**, ampliável quando F2 mover regras. ⚠️ O gate **NÃO cobre**
`account_normalization` (`numero_conta_norm`, [[ADR-226]]) — `extract_members.py:46` já
o importa hoje; é vazamento conhecido, alvo de F2, **não** desta onda.

## Critério de aceite

- `dev/check_extract_no_domain_imports.py` exit 0 no repo atual (25 arquivos de extração).
- `tests/unit/pipeline/test_check_extract_no_domain_imports.py` verde: (a) verde hoje;
  (b) leak sintético sob extraction root → detecta; (c) `consolidate_baseline` importando
  dedup → permitido (fora do glob); (d) sentinela `extract_*` do REGISTRY coberto;
  (e) `dedup_metrics` não dispara falso-positivo.
- Hook em pre-commit (`pass_filenames:false`, `always_run`) + step em `ci.yml`.
- `dev/check_code_style_regression.py` verde (gate ≤20 linhas/função, sem nesting >2).

## Não-escopo

- Mover código (`tipo_lancamento`/`numero_conta_norm` → Transform) → F2 (de-leak).
- Ampliar matchers para `account_normalization` → F2.
- Rótulo de pureza no `StageSpec` → só se F2 exigir consumo multi-lugar.

## Owner sugerido

`senior-cto` (boundary gate, padrão `check_pipeline_boundaries`). Co-design da decisão
em [[ADR-280]].
