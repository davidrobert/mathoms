---
id: A40.l74
type: lane
title: "Stage com dois produtores, schema 1:1: apólice validava contra o schema de veículo, e o mapa mentia em três lugares"
sprint: A40
status: in_progress
priority: P1
branch_slug: a40-l74-schema-por-forma-de-payload
adrs:
  - "[[ADR-407]]"
  - "[[ADR-239]]"
  - "[[ADR-284]]"
  - "[[ADR-238]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/pipeline
  - area/backend
---

# A40.l74 — Schema por forma de payload no stage de comprovantes

> **Escopo herdado:** a metade CRLV deste problema fechou em
> [#1599](https://github.com/davidrobert/mathoms/pull/1599) (`crlv.schema.json` não
> declarava `source_artifact_id`, que o produtor emite desde #836). Esta lane fecha a
> metade apólice — que é a maior — e a **classe** que produziu as duas.

## O achado, medido

`SCHEMA_BY_STAGE` é `dict[str, str]`. O stage `extract_comprovantes_bens` tem **dois**
produtores (`_persist_crlv` e `_persist_apolice`, ambos `store.write("extract_comprovantes_bens", …)`),
e o mapa apontava para `crlv.schema.json`.

Medido em 2026-08-21 pelo caminho real (`validate_dict` com
`MATHOMS_PIPELINE_SCHEMA_MODE=strict`, alimentado por `_build_apolice_payload` sobre o
golden `apolice_combinada.json`): **9 erros, 25 paths em drift** — 8 `required` ausentes
+ 17 propriedades não declaradas. `config/schemas/apolice.schema.json` **nunca existiu**,
embora [[A18]] o declarasse entregue (linha corrigida nesta lane).

Não abortava porque `config/pipeline.json → schema_validation.mode` é `warn`.

## O que o enunciado do achado não continha

1. **O 1:1 tem três consumidores, não um.** `_schema_version_token` também resolve pelo
   mapa e grava o hash em `pipeline_artifacts.schema_version` — **toda row de apólice
   estava carimbada com o hash do schema de veículo**. E `dev/check_artifact_read_keys.py`
   lê o mapa por `ast.literal_eval`, o que descarta por construção qualquer desenho que
   troque o `str` por callable.
2. **O molde ingênuo do gate passa vazio.** `_schema_to_validate` faz short-circuit para
   `True` quando o arquivo não existe: medi que `validate_dict(payload, "apolice.schema.json")`
   retornava `True` **antes** do fix, com o schema inexistente. Um teste copiado do #1599
   sem afirmar existência reproduziria o falso-verde que originou o achado.
3. **`oneOf` seria uma armadilha silenciosa.** `e4_unified.schema.json` resolve "1 stage,
   7 formas" com `oneOf` por `required` — precedente tentador, e sem custo no produtor.
   Medido: com **um** drift real, `oneOf` emite path `$` e `if/then` emite `$.corretor`.
   Como a telemetria per-path da [[ADR-284]] é o gate do flip `warn→strict`, `oneOf`
   trocaria a inelegibilidade atual por outra, mais discreta. Ver [[ADR-407]] D2.

## Entrega

- `config/schemas/apolice.schema.json` — pareado com `ApolicePayload`: 3 ramos de bem,
  5 de cobertura, 3 modos de LMI, `$defs` internos. Topo lenient, todo sub-objeto strict
  ([[ADR-238]] D2). Dinheiro é string decimal ([[ADR-090]]).
- `config/schemas/comprovante_base.schema.json` — despacha por `tipo_comprovante` via
  `allOf/if-then/$ref`. `SCHEMA_BY_STAGE` **permanece 1:1**.
- Produtores enxertam `tipo_comprovante` em `_stamp_stage_fields`, junto de
  `prompt_version`/`source_artifact_id` — os campos que o stage acrescenta pós-`model_dump()`
  e que só existem para o JSON Schema se ele os declarar (origem do #1599).
- `_schema_version_token` hasheia o **fecho transitivo** dos `$ref` — retro-corrige
  `informe_base`, `e2_llm_artifact` e `e5_analysis`, cegos hoje.
- `dev/check_artifact_read_keys.py` desce `allOf[].then.$ref` (media 1 property visível
  contra 37 reais) e ganha gate de existência transitivo.
- `tests/test_comprovante_schema_contract.py` — 17 testes.

## Prova de que o gate não é cego

| controle | resultado |
| --- | --- |
| mapa revertido para `crlv.schema.json` (estado pré-fix) | **12 de 17 falham** |
| base reescrito como `oneOf`-por-shape | **5 de 17 falham** |
| `apolice.schema.json` apagado | gate de existência **morde** |
| `crlv.schema.json` editado | token de auditoria **muda** |

## Efeito na [[A40.l58]] (flip `warn→strict`)

Não desbloqueia a l58 — [[ADR-284]] manda flip per-schema por `mode_overrides`, gateado
por baseline ≥7 dias zero-WARN. O que muda é que `crlv.schema.json` e
`apolice.schema.json` passam a ser **candidatos legítimos**: eram inelegíveis por
emitirem WARN em todo write. O merge desta lane é o dia 0 da baseline.

## Follow-ups (não entram nesta lane)

- **`e4_unified.schema.json` cai na mesma D2** — 5 ramos em `oneOf`, drift sempre em `$`,
  cobrindo 7 artifact keys do E4. Endereçado a [[A40.l58]], que é o dono do flip.
- **`_schema_to_validate` falha aberta no ausente e fechada no corrompido.** A assimetria
  é acidente, não política, mas `validate_dict` tem callers fora do mapa e o blast radius
  não está medido. Fechado por gate aqui; o flip do runtime fica em aberto ([[ADR-407]]
  §Consequências).
