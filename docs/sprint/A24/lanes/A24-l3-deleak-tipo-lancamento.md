---
id: A24.l3
type: lane
title: "Data Lineage F2 — de-leak tipo_lancamento (delete do output + contrato)"
sprint: A24
plan: PLAN-data-lineage
status: shipped
priority: P0
branch_slug: dl-f2-deleak-tipo-lancamento
adrs:
  - "[[ADR-280]]"
  - "[[ADR-283]]"
depends_on: ["[[A24.l1]]"]
parallel_with: ["[[A24.l2]]"]
tags:
  - type/lane
  - sprint/a24
  - status/shipped
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A24.l3 — `dl-f2-deleak-tipo-lancamento`

> **Plano:** [[PLAN-data-lineage]] · Onda 2 (F2). Bloqueada por [[A24.l1]];
> paralela a [[A24.l2]] (vazamentos ortogonais, não-colidentes — F2-B6).

## Objetivo

Remover `tipo_lancamento` do **output** da extração. O campo é dead-downstream
(zero consumidores em `pipeline/`/`backend/`; `e2_natural_key.py:59` confirma que
não alimenta a K4) — classificação que ninguém lê. **NÃO criar stage Transform
para campo que ninguém consome**; se a classificação for desejável um dia, recria
como sinal na Transform (follow-up consciente, fora desta lane).

## Escopo

| Item | Detalhe |
|---|---|
| Remover `tipo_lancamento` do output dos parsers | `scripts/e2/banks/c6bank.py` · `caixa.py` · `santander.py:772` — lógica interna de parsing que o usa para derivar sinal/direção PODE permanecer; o que sai é o **campo no dict emitido** |
| **F2-DB1**: remover do contrato fechado [[ADR-283]] na MESMA PR | `config/schemas/e2_extract.schema.json` (linha 36) + migrar `tests/test_schema_validation.py:195` + nota de emenda no corpo da [[ADR-283]] (campo sai do contrato; mudança esperada, manifesto + runbook) |
| **F2-B5**: enforcement por **AUSÊNCIA-DE-CAMPO** | `test_e2_contract_no_methodological_fields` — NÃO gate de regex inline (alto falso-positivo) |
| Migrar testes de parser | `tests/test_c6bank_pdf_parser.py` (asserções do campo) |
| ⚠️ `category_hint` ([[ADR-242]]) **NÃO é desta fila** | já é sinal preservado; anexar `origin=llm_extract` FLAT é o máximo aditivo permitido; objeto `{value,origin,confidence}` aninhado é **DEFERIDO** (breaking em 3 superfícies — F2-DB2) |

## Risco mapeado (data-engineer, co-design l1)

Strip de campo declarado no schema fechado dispara `validate_dict` pós-write
(`DBArtifactStore.write`, [[ADR-212]]): em `warn` loga, em `strict` aborta.
Por isso **schema + writers saem no MESMO commit/PR** — e o
`check_golden_rebaseline_isolation` (l1) trata `config/schemas/**` como
contrato, não produção, permitindo schema+golden juntos.

## Critério de aceite

- Nenhum parser emite `tipo_lancamento`; schema E2 não declara o campo.
- `test_e2_contract_no_methodological_fields` verde (e falha se o campo voltar).
- `check_no_leak_field_consumers` (l1) continua verde.
- `golden_diff` E3/E4/E5 + dogfood: zero `value_delta`; artefatos E2 mudam por
  **remoção de campo** (kind `removed`, não-monetário) — sem rebaseline de valor.
- Invariantes de conservação verdes; dogfood real (G-f) sem delta.

## Não-escopo

- Recriar a classificação na Transform (YAGNI até existir consumidor).
- Reshape do `category_hint` (DEFERIDO — F2-DB2).

## Owner

Co-design `data-engineer` + `senior-cto` (registrado na l1).
