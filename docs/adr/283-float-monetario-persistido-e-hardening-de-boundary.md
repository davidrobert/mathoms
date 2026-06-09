---
id: ADR-283
type: adr
title: "Float monetário persistido e hardening de boundary de schema (patrimonio_liquido, gate models, E2 items)"
status: Proposto
phase: "Débito técnico"
date: "2026-06-09"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-114]]"
  - "[[ADR-137]]"
  - "[[ADR-212]]"
supersedes: []
superseded_by: []
aliases: ["ADR 283", "float money debt", "patrimonio_liquido numeric", "E2 additionalProperties"]
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/persistence
  - area/data-lineage
---

# ADR-283 — Float monetário persistido e hardening de boundary de schema

**Status:** Proposto (Débito técnico) • **Data:** 2026-06-09 • **Relaciona**
[[ADR-090]] (dinheiro nunca é float), [[ADR-114]] (gates de code-style),
[[ADR-137]] (catálogo de categorias em cents), [[ADR-212]] (DBArtifactStore + schema validation).

## Contexto

Auditoria de 4 débitos reportados. A profundidade real, após verificação no
código + validação por `financial-planner` e `data-engineer`:

1. **Float monetário persistido.** Existem **5 colunas `Float`** em
   `backend/app/models/`; só **2 são monetárias**: `Report.patrimonio_liquido`
   e `Category.monthly_cap`. As outras três (`Report.score` 0–100,
   `LLMConfig.temperature`, `Document.classification_confidence`) são razões/índices
   — float legítimo. `patrimonio_liquido` é escrito via `_to_decimal(...)`
   (coagido a float na persistência) e relido em
   `goal_service.get_latest_report_patrimonio_liquido` para o cálculo de meta de
   Independência Financeira (IF). **Em produção a coluna é NULL-only nos
   relatórios novos** — os write-sites vivos (`pipeline_task.py`,
   `backfill_reports_from_artifacts.py`) não a populam; só testes/factories e
   linhas históricas têm valor. O drift fiscal prático é sub-centavo (agregado
   escalar, não soma iterativa; `Decimal(str(row))` neutraliza na releitura).

2. **`Category.monthly_cap` é Float legado já superseded.** [[ADR-137]] migrou o
   cap para `workspace_category_overrides.monthly_cap_brl_cents` (BigInteger/cents);
   `category_resolver` lê os cents. O Float ainda é CRUD'd pelo endpoint legado
   `/config/categories` (header `Deprecation: true`, sunset agendado em
   `A12.cat-legacy-sunset`).

3. **Gate `dev/check_float_money.py` só cobre diff.** Escaneia linhas adicionadas
   em `git diff --cached`; legado fica de fora por design ([[ADR-114]]). Sem
   rede de segurança contra regressão de coluna `Float` persistida.

4. **Schema validation `warn` + `additionalProperties:true`.** `pipeline.json`
   default `mode: warn`; `config/schemas/e2_extract.schema.json` aceitava
   campos extras tanto no top-level quanto em cada transação — boundary aceita
   drift de produtor silenciosamente.

## Decisão

### A — `Report.patrimonio_liquido` Float → `Numeric(18,2)`

`Numeric(18,2)`, **não** cents int. Razões: (a) a convenção de DB do repo é
`Numeric` ([[ADR-090]]); cents int é a forma Go; (b) o read-path (`goal_service`)
já devolve `Decimal` — `Numeric` mantém o tipo de ponta a ponta sem conversões
extra; (c) o agregado é BRL **consolidado upstream** (E5 converte câmbio), escalar,
single-currency — não há aritmética acumulativa que justifique cents. Migration
`batch_alter_table` (sqlite-safe) + `postgresql_using` (auto-arredonda linhas
legadas). Backfill coberto pelo cast; prod é majoritariamente NULL.

**Wire permanece `float`** (`ReportResponse.patrimonio_liquido: Optional[float]`):
o frontend lê `number` e faz aritmética em `meta-if`. Pydantic coage `Decimal→float`
no DTO; a correção fecha a **persistência** (parte irreversível). Wire-string
decimal é follow-up consciente (§Follow-ups), não escopo desta ADR.

### B — `Category.monthly_cap`: não dropar agora

Dropar a coluna quebra o endpoint legado `/config/categories` em runtime (mapper
+ repo ainda a referenciam). O drop pertence à lane `A12.cat-legacy-sunset` (depende
de remover o endpoint + mapper + DTO command). Nesta ADR a coluna entra na
allowlist do gate como "legado órfão, drop rastreado".

### C — Gate full-scan de colunas `Float` em `models/`

`dev/check_float_money.py --scan-models backend/app/models`: detecção **estrutural**
(`mapped_column(Float)` / `Column(Float)`), não regex de nome. Allowlist **nominal**
`(path, coluna) → motivo` para os 3 floats legítimos + `monthly_cap` legado.
Hook pre-commit `float-money-models` (`always_run`). O gate diff-only existente
permanece para o resto do codebase; o full-scan cobre só `models/` (DTOs Pydantic
de boundary continuam no diff-only — delimitação limpa, evita falso-positivo no
domínio do pipeline, onde float-sobre-JSON é convenção documentada).

### D — E2: fechar `transacoes.items.additionalProperties`

`config/schemas/e2_extract.schema.json`: `transacoes.items.additionalProperties:false`,
com `items.properties` enumerando **todos** os campos por-transação emitidos pelos
12 parsers em `scripts/e2/banks/` (audit AST: `data`, `descricao`, `valor` obrigatórios;
`direction`, `natural_key`, `tipo_lancamento`, `forex`, `parcela`, `nr_doc`, `cartao`
opcionais). **Seguro em modo `warn`** — em prod só **loga** drift, não aborta o run;
gera o sinal que hoje falta. O **top-level continua `additionalProperties:true`**
(carrega metadados de evolução adicionados organicamente por writer — fechar é frágil).

## Não-decisões (rejeitadas / adiadas)

- **Cents int para `patrimonio_liquido`** — rejeitado (§A): diverge da convenção
  Postgres do repo e adiciona conversões num fluxo já-Decimal.
- **Flipar `schema_validation.mode: strict` em prod** — adiado. `warn→strict` global
  aborta run em qualquer stage com drift não-mapeado. Sequência correta: instrumentar
  contador de WARN em prod (por `workspace_id`+`stage`) → medir baseline → flip
  **per-stage** começando por E2. É lane de telemetria/ops separada.
- **Fechar `additionalProperties` no top-level E2** — rejeitado (§D): frágil.
- **Wire-string decimal em `ReportResponse`** — adiado: breaking p/ frontend
  (`meta-if` lê `number`); exige `make update-openapi-snapshot` + ajuste TS.

## Consequências

- `Report.patrimonio_liquido` honra [[ADR-090]]; releitura para meta IF é `Decimal` exato.
- Regressão de coluna `Float` monetária em `models/` é bloqueada no pre-commit.
- Drift de shape de transação E2 passa a gerar sinal (WARN) sem risco de abortar prod.
- Custo: 1 migration, 1 hook novo, enumeração do contrato E2. Sem mudança de comportamento de runtime (wire inalterado, mode `warn` inalterado).

## Follow-ups rastreados

1. **Drop `Category.monthly_cap`** → lane `A12.cat-legacy-sunset` (após sunset do endpoint legado).
2. **Wire-string decimal** em `ReportResponse.patrimonio_liquido` (+ frontend + OpenAPI snapshot).
3. **Strict per-stage em prod** — instrumentar WARN-counter → medir → flip começando por E2; expandir corpus golden E2 por banco como pré-condição.

## Critério de aceite

- `dev/check_float_money.py --scan-models backend/app/models` verde; `patrimonio_liquido` fora da allowlist (já é Numeric).
- Round-trip `Decimal("12345678.90")` persiste/relê exato; `get_latest_report_patrimonio_liquido` retorna `Decimal`.
- Goldens E2 reais validam contra schema fechado em `strict`; campo não-declarado em transação falha em `strict`.
- Migration reversível (`downgrade` re-adiciona Float, perda de precisão documentada).
