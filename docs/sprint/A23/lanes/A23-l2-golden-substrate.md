---
id: A23.l2
type: lane
title: "Data Lineage F1 — substrato de golden (diff tool + view-model snapshot + invariantes)"
sprint: A23
plan: PLAN-data-lineage
status: open
priority: P0
branch_slug: a23-l2-golden-substrate
adrs:
  - "[[ADR-279]]"
depends_on:
  - "[[A23.l1]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a23
  - status/open
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A23.l2 — Substrato de golden (guard-rails de regressão)

> **Plano:** [[PLAN-data-lineage]] · Onda 1 · **abre só após o gate F0 ([[A23.l1]])**.
> Primeira lane da Onda 1, **antes de qualquer rebaseline de golden** (F2). Fecha o
> débito **DE-005** ([[PLAN-platform-review]] §W6-T01).

## Objetivo

Construir a rede de regressão *number-level* que torna o rebaseline de F2/F3
auditável e a cobertura abrangente — antes de qualquer fase tocar golden. Resolve
G-a, G-b, G-c (parte de tooling) das guard-rails consolidadas na revisão
multi-agente (ver [[PLAN-data-lineage]] §Guard-rails de regressão).

## Escopo

1. **`dev/golden_diff.py`** (função de domínio, **não importa framework** — boundary
   `pipeline/**`): entrada = golden antigo vs. novo (JSON canônico); saída por campo
   = `unchanged | moved | value_delta | new | removed`. Delta monetário em **cents
   int** (`Decimal(novo) − Decimal(velho)`, [[ADR-090]]), nunca float. Roda no CI e
   **comenta o diff valor-a-valor no PR**.
2. **Snapshot do view-model** de `/reports/[id]/data` (`backend/tests/`): serializa o
   payload completo que o React consome (todos os `<MonetaryValue/>` + labels +
   seções, derivado do codegen `report_layout`), comparado em cents int. **Asserção
   de completude:** `monetary_fields(view_model) ⊆ snapshot` — número novo no
   relatório sem entrar no snapshot → gate falha (cobertura estrutural, não
   enumeração manual).
3. **Invariantes de conservação por balde** (estende `tests/test_e5_golden_execution.py`):
   `patrimonio.liquido == Σ(7 categorias) − dívidas`, `fluxo_líquido == Σ receitas −
   Σ despesas`, por balde (não só o total) — a "segunda testemunha" que quebra
   sozinha quando o rebaseline cimenta valor errado.
4. **Fixture sintética PII-zero** (`tests/fixtures/pipeline_golden/dogfood/`):
   família fictícia exercitando [[ADR-246]] (imóvel em comunhão), [[ADR-271]]
   (investimento cross-year), [[ADR-255]] (tx colapsada por dedup), [[ADR-241]]
   (caso incremental, B8). `InMemoryArtifactStore` ([[ADR-212]]), determinístico
   (run 2× byte-idêntico), money decimal string.

## Critério de aceite

- `golden_diff(antigo, novo)` puro/stateless ([[ADR-111]]); `value_delta` monetário
  fora de manifesto → exit≠0 no CI; comenta no PR.
- Snapshot do view-model verde **sem rebaseline** (prova de aditividade — entra no G1);
  `monetary_fields ⊆ snapshot` verde; zero float.
- Invariantes de conservação verdes sobre goldens E5 atuais.
- Fixture dogfood sintética passa gate de PII; exercita ADR-246/271/255/241.
- DE-005 marcável como fechado; ponteiro em CLAUDE.md §Testes atualizado.

## Owner sugerido

`data-engineer` (substrato de golden / contrato de dados) — co-design com
`senior-cto` (boundary do diff tool).
