---
id: TRACK-w6t01-schema-hardening
type: track
title: "Track W6-T01 — Schema hardening (E5 strict + 7 sub-schemas E4 + ADR-090 wire)"
sprint: W6
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/w6
  - status/consumed
---

# Track W6-T01 — Schema hardening (E5 strict + 7 sub-schemas E4 + ADR-090 wire)

> **Lane ID:** `w6t01-schema-hardening`
> **Branch prefix:** `agent/w6t01-schema-hardening/<sub>/<yyyyMMdd-HHmm>`
> **Plano canônico:** [plan/PLATFORM_REVIEW/_README.md §W6-T01](../../../plan/PLATFORM_REVIEW/_README.md)
> **Onda:** Wave 6 (paraleliza com Wave 5)
> **Severity:** P1 · **Effort:** L (3 sub-PRs sequenciais)
> **Owner:** data-engineer
> **Depende de:** W1-T08 ✅ (PR #96 — `cenarios_conjuge` formal + 18 blocos shallow)
> **Findings cobertos:** DE-005, DE-006, DE-007, DE-012, DE-014, DE-018, DE-020, DE-021

---

## 1. Inventário (snapshot 2026-05-07)

### 14 schemas em `config/schemas/`:

| Schema | top-level `additionalProperties` | Wire money | Status |
|---|---|---|---|
| `pipeline.schema.json` | `true` | n/a (config) | OK lenient |
| `e2_extract.schema.json` | `true` | `number` ❌ | fix wire |
| `e3_reconciled.schema.json` | `true` | `number` ❌ | fix wire + strict |
| `e4_unified.schema.json` | `true` (oneOf 4 shapes) | `number` ❌ | **split em 7** |
| `e5_analysis.schema.json` | `true` (W1-T08 declarou 19 blocos) | `number` ❌ | flip strict + wire |
| `e16_irpf_full.schema.json` | `true` (sub-models `false`) | **string-decimal ✅** (`$defs/moneyDecimal`) | **template ADR-090** |
| `baseline_patrimonial.schema.json` | (não declara) → default `true` | `number` ❌ | strict + wire |
| `goal.if.v2.schema.json` | `false` ✅ | `number` ❌ | wire |
| `goal.alocacao_alvo.v2.schema.json` | `false` ✅ | `number` (pcts) | OK |
| `goal.aporte_mensal.schema.json` | `false` ✅ | `number` ❌ | wire |
| `goal.dolarizacao.schema.json` | `false` ✅ | n/a (pcts) | OK |
| `goal.if.schema.json` (legacy v1) | `false` ✅ | `number` ❌ | superseded |
| `goal.alocacao_alvo.schema.json` (legacy) | `false` ✅ | `number` | superseded |
| `report_layout.schema.json` | `true` (sub-models `false`) | n/a | OK |

### Schemas faltando (gap explícito):

- `e7_review.schema.json` → Pydantic existe (`pipeline/llm/schemas/e7_review.py` `E7ReviewOutput`) mas JSON Schema não vive em `config/schemas/`.
- `e5_narrativas.schema.json` → bloco `narrativas` em E5 é `{"type": "object"}` opaco.
- `validate_cross.schema.json` (E7-crossval) — DE-007.
- `e1_members.schema.json` → Pydantic `MembersExtractOutput`.
- `e15_baseline.schema.json` → Pydantic `BaselinePatrimonialOutput`.

`pipeline.json → schema_validation`: `enabled=true`, `mode=warn`.
**Flippar `mode=strict` é o ponto-final desta lane.**

---

## 2. Split E4 — 7 sub-schemas

`e4_unified.schema.json` hoje é `oneOf` shallow. Esconde drift entre os
7 artefatos produzidos por `pipeline/domain/services/e4_serialization.py::ARTIFACT_KEYS`:

| Sub-schema novo | Origem | Justificativa |
|---|---|---|
| `e4_receitas.schema.json` | `CashFlowBuilder.build_receitas_unified` | Shape estrito; hoje colapsa com Despesas. |
| `e4_despesas.schema.json` | `CashFlowBuilder.build_despesas_unified` | `categorias` tem `tipo` ∈ {fixo, variável} que não vale receita. |
| `e4_fluxo_mensal.schema.json` | `CashFlowBuilder.build_fluxo_mensal` | Único shape com timeseries. |
| `e4_patrimonio.schema.json` | `NormalizedBaseline.data` (E1.5c) | ADR-132 permite ausência. |
| `e4_investimentos.schema.json` | `InvestmentsConsolidator.consolidate` | 80% strict em E5 §investimentos; portar. |
| `e4_seguros.schema.json` | `empty_placeholder()` | Placeholder strict: `dados=[]` constante. |
| `e4_pontos_milhas.schema.json` | idem | Idem; explicita placeholder. |

`e4_unified.schema.json` vira **meta-schema** com `oneOf` referenciando
os 7. Resolver por artifact key em
`pipeline_common.validate_artifact(stage, artifact_key, payload)`.

**Findings:** DE-014, DE-018.

---

## 3. Auto-gen Pydantic → JSON Schema

Schemas que devem nascer do Pydantic (single source of truth):

| Schema novo | Pydantic source |
|---|---|
| `e7_review.schema.json` | `pipeline/llm/schemas/e7_review.py::E7ReviewOutput` |
| `e5_narrativas.schema.json` | (a criar) `NarrativasOutput` em `pipeline/domain/services/narrativas/builder.py` |
| `validate_cross.schema.json` | (a criar) `CrossValidationOutput` em `pipeline/stages/validate_cross.py` |
| `e1_members.schema.json` | `pipeline/llm/schemas/e1_members.py::MembersExtractOutput` |
| `e15_baseline.schema.json` | `pipeline/llm/schemas/e15_baseline.py::BaselinePatrimonialOutput` |

**Tooling:** `dev/codegen_schemas_from_pydantic.py`:
- Whitelist `PYDANTIC_TO_JSON_SCHEMA` (model FQN → output path).
- `model.model_json_schema(by_alias=True, mode="serialization")`.
- Pós-processa: injeta `$schema`, `title`, `description`; força `additionalProperties: false` no top quando `extra='forbid'`.
- `Decimal` fields → `{"type": "string", "pattern": "^-?\\d+(\\.\\d{1,2})?$"}` (ADR-090 wire). Template em `e16_irpf_full.schema.json` `$defs/moneyDecimal`.
- Hook pre-commit + CI gate `make check-schemas-generated`.

Padrão consagrado: `make update-openapi-snapshot` (ADR-109).

---

## 4. ADR-090 wire compliance

Campos monetários **ainda como `number`** (precisam virar string-decimal):

- **`e2_extract.schema.json` L32:** `transacoes[].valor`.
- **`e3_reconciled.schema.json` L51, 57:** `saldo_inicial`, `saldo_final`.
- **`e4_unified.schema.json` L12:** `total_geral`. Após split: em todos 7 sub-schemas.
- **`e5_analysis.schema.json`:** `patrimonio.bruto/liquido` (L22-23), `cenarios_conjuge.aportes[]` (L63), `cenarios.aporte_mensal` (L95), `investimentos.tabela_classes[].valor` (L129), `top_ativos[].valor` (L167) — dezenas de campos.
- **`baseline_patrimonial.schema.json` L55-56, 60, 69-70:** `valor_31_12_anterior/atual`, `total_bens`, `total_dividas`.
- **`goal.if.v2.schema.json`**, **`goal.aporte_mensal.schema.json`**: meta/aporte.

### Backfill plan — `dev/backfill_money_decimal.py`

1. **Read-side compat (urgent):** `pipeline_common.load_artifact(...)` aceita ambos (`number` legado e `string-decimal` novo). Coerção via `Decimal(str(v))`.
2. **Write-side flip (per artifact, atrás de flag `MATHOMS_WIRE_MONEY_DECIMAL=1`):** `pipeline/domain/services/{e3,e4,e5}_serialization.py` → `Money.brl(v).to_decimal_str()`.
3. **Schema flip:** adicionar `$defs/moneyDecimal` em cada schema; referenciar via `$ref` nos campos listados.
4. **Backfill artefatos persistidos** (`pipeline_artifacts.payload` BYTEA): script idempotente que lê payload, transforma `number → string-decimal`, regrava com `schema_version` bumpado. Run em batch via Celery beat. Não migrar artefatos com `retention_until` < 30d (W6-T05); deixar expirar.
5. **Cutover:** flag default ON após 1 sprint; remover read-side compat após 90d.

**Idempotência:** content-hash do payload pré/pós como sentinela.

---

## 5. Modo strict default — pré-condições

1. Todos 14 schemas com `additionalProperties: false` no top-level (ou justificado lenient com TODO/ADR).
2. W1-T08 já declarou 19 blocos top-level de E5 — falta declarar properties internas dos blocos `{type: object}` opacos: `fluxo_caixa`, `ratios`, `goals`, `orcamento_prospectivo`, `reserva_emergencia`, `endividamento`, `previdencia_pgbl`, `equilibrio_cerbasi`, `tarefas_status`, `consumo_consciente`, `programa_milhas`, `narrativas`, `irpf_kpis`, `passive_income`, `if_monte_carlo`.
3. Wire money flippado (passo 4 acima) — strict expõe `number ≠ string-decimal` como erro.
4. Auto-gen Pydantic em CI — sem isso, qualquer field new no Pydantic quebra strict.

### Tests que quebram ao flippar `mode=strict`:

- `tests/test_e5_golden_execution.py` — golden tem chaves shallow não declaradas.
- `tests/test_e3_golden_execution.py` — `transacoes[]` é lenient hoje.
- `tests/test_e4_golden_execution.py` — `oneOf` falha 100% em strict (DE-018).
- `backend/tests/test_pipeline_artifacts_validation.py` — adapter `DBArtifactStore` valida no read.
- Possíveis falhas em E2 LLM extracts com bancos exóticos.

**Mitigação:** flag `MATHOMS_SCHEMA_STRICT_E5=1` por stage isolado;
flippar incrementalmente E2→E3→E4→E5→pipeline-wide.

---

## 6. Faseamento (3 sub-PRs sequenciais)

### PR-1 — Foundation (`agent/w6t01-schema-hardening/01-codegen`)
- `dev/codegen_schemas_from_pydantic.py` (NOVO).
- Gerar `e7_review.schema.json`, `e1_members.schema.json`, `e15_baseline.schema.json`.
- Adicionar `$defs/moneyDecimal` em todos os schemas.
- CI gate `make check-schemas-generated`.
- **Sem mudança runtime.** Risco: minimal.

### PR-2 — E4 split + ADR-090 read-side (`02-e4-split-wire-read`)
- 7 sub-schemas E4 + `e4_unified.schema.json` vira meta.
- `pipeline_common.validate_artifact` resolve por artifact key.
- `pipeline_common.load_artifact` aceita ambos wire formats.
- `e4_serialization.py` emite string-decimal **atrás de flag** OFF.
- Goldens regenerados.
- Risco: médio (split E4 quebra paridade golden se shape divergir).

### PR-3 — Wire flip + strict cutover (`03-strict-cutover`)
- `dev/backfill_money_decimal.py` (NOVO) com run em DB artifacts.
- `e5_narrativas.schema.json` + `validate_cross.schema.json` (Pydantic novos).
- Flag `MATHOMS_WIRE_MONEY_DECIMAL=1` default.
- `pipeline.json → mode = "strict"`.
- Schema bump `pipeline_artifacts.schema_version` (W6-T05 conflito — coordenar).
- **ADR nova:** "Schema hardening — strict default + auto-gen + ADR-090 wire". Status `Decidido (W6-T01)`.
- Risco: alto (regressão silenciosa em consumers que ainda esperam `number`).

---

## 7. Critério de aceite

- [ ] `make check-schemas-generated` no CI.
- [ ] Todos 14 schemas: top-level `additionalProperties` declarado.
- [ ] Zero `{type: number}` em campos monetários (auditoria via `dev/check_wire_money.py` NOVO).
- [ ] `pipeline.json → mode=strict` em CI.
- [ ] Goldens regenerados, paridade verde com `MATHOMS_WIRE_MONEY_DECIMAL=1`.
- [ ] Backfill rodado em staging com volume de prod; rollback testado (flag OFF).
- [ ] ADR nova criada e linkada.

---

## 8. Risco de regressão

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Frontend lê `number` e quebra com `string-decimal` | Alta | Flag escalonada; codegen TS atualiza tipo `Decimal` aliased a `string`; testes Vitest. |
| Goldens E5 quebram em massa | Média-Alta | PR-2 regenera goldens com flag OFF; PR-3 com flag ON; review visual. |
| `DBArtifactStore` rejeita payload legado em strict | Alta | Backfill obrigatório antes do cutover; read-side compat 90d. |
| Schema generated diverge do Pydantic em prod | Média | CI gate trava merge se schema mudou sem regenerar. |
| Frontend `MonetaryValue` quebra com tipo string | Baixa | Já espera `string \| number` (PD-006/W5-T03). |

---

## Coordenação

- **W6-T05** (artifacts retention) — schema_version bump pode colidir; quem mergeia segundo rebase.
- **W2-T01** (PII Fernet) — toca `db_artifact_store.write`; ortogonal mas requer sync.
- **W5-T05** (Goal IF v2) — schema E5 + goal schemas — coordenar wire flip.
