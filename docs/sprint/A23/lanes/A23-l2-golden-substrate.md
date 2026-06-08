---
id: A23.l2
type: lane
title: "Data Lineage F1 — substrato de golden (diff tool + view-model snapshot + invariantes)"
sprint: A23
plan: PLAN-data-lineage
status: shipped
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
  - status/shipped
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

## Entregue (status: shipped)

Co-design com `data-engineer` + `senior-cto` antes de codar. Entregáveis:

- **`dev/golden_diff.py`** — núcleo puro/stateless ([[ADR-111]]); diff valor-a-valor
  classifica `unchanged|moved|value_delta|new|removed`; delta em cents int
  ([[ADR-090]]); arrays pareados por chave natural (sem falso-`moved`); detecção
  **monetário-por-default** (campo numérico novo falha alto) + allowlist
  não-monetária curada. Manifesto YAML (`rebaseline_manifest.yaml`): `value_delta`
  monetário não-justificado **ou** entrada órfã → exit≠0. `tests/test_golden_diff.py`
  (16 testes, sem subprocess).
- **`backend/tests/test_report_view_model_snapshot.py`** + golden
  `snapshots/dogfood_view_model.json` — reproduz a forma de `get_report_data`
  (E5 + `_report_lineage` + `comparisons/changelog`) sem DB; normaliza
  monetário→cents int (zero float); 4 asserções: match golden, determinismo
  2× byte-idêntico, zero float, `monetary_fields ⊆ snapshot`.
- **`tests/test_e5_conservation_invariants.py`** — invariantes por balde,
  tolerância **zero cents**: `bruto == Σ composicao[].valor`; `liquido == bruto −
  dividas`; `fluxo_liquido == receita_total − despesa_total`. Validadas
  empiricamente (O3) nos 4 goldens E5 antes de cravar a fórmula.
- **`config/schemas/e5_analysis.schema.json`** — declara `patrimonio.dividas`/
  `composicao` + `fluxo_caixa.{receita_total,despesa_total,fluxo_liquido}`
  (não-`required`, `additionalProperties` intocado) — adianta W6-T01 sem invadir.
- **Fixture dogfood** (`tests/fixtures/pipeline_golden/dogfood/`, PII-zero).

### Decisões de escopo (verificadas)

- **ADR-271 + ADR-255 exercitados genuinamente** end-to-end (código real
  E1.5c/E3): cross-year → série única; tx cross-file → `transacoes_duplicadas_removidas=1`.
- **ADR-246** (imóvel co-declarado) entra como **outcome bacado** — `imoveis_dedup`
  chaveia por `property_id` (resolver DB), fora do substrato in-memory. Dedup 246
  genuíno coberto pelo unit test `imoveis_dedup` + dogfood F3 com resolver DB (G-f).
- **ADR-241/B8** (golden de transição incremental) **diferido** — dimensionado
  separado (recomendação `data-engineer`); follow-up.
- `check_golden_rebaseline_isolation` (isolamento commit↔código) **não** é desta
  lane — é F2 (`dl-f2-deleak-slice1`, G-c). A23.l2 entrega só o reader + formato
  do manifesto + gate de cobertura.

**Fecha DE-005** ([[PLAN-platform-review]] §W6-T01); ponteiro atualizado em
CLAUDE.md §Testes.
