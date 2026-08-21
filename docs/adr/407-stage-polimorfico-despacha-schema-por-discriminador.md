---
id: ADR-407
type: adr
title: "Stage com N formas de payload despacha schema por discriminador declarado, nunca por shape"
status: Proposto
date: "2026-08-21"
relates_to:
  - "[[ADR-239]]"
  - "[[ADR-238]]"
  - "[[ADR-284]]"
  - "[[ADR-212]]"
  - "[[ADR-090]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 407"
  - "schema por forma de payload"
  - "comprovante_base"
  - "oneOf cega a telemetria de drift"
tags:
  - area/pipeline
  - area/dados
  - status/proposto
  - type/adr
---

# ADR-407 — Stage com N formas de payload despacha schema por discriminador declarado

**Status:** Proposto · **Data:** 2026-08-21 · **Relaciona** [[ADR-239]] (D8, stage único
polimórfico), [[ADR-238]] (D2, leniência top-level), [[ADR-284]] (telemetria de drift +
flip per-schema), [[ADR-212]] (hook pós-write), [[ADR-090]] (dinheiro no wire).

## Contexto

`SCHEMA_BY_STAGE` é `dict[str, str]` — um schema por stage. O stage
`extract_comprovantes_bens` tem **dois** produtores (`_persist_crlv` e
`_persist_apolice`), e o mapa apontava para `crlv.schema.json`. Payload de apólice
era validado contra o schema de veículo.

Medido em 2026-08-21 pelo caminho real de produção (`validate_dict` com
`MATHOMS_PIPELINE_SCHEMA_MODE=strict`, produtor `_build_apolice_payload` alimentado
pelo golden `apolice_combinada.json`): **9 erros, 25 paths em drift** — 8 `required`
ausentes (`placa`, `renavam`, `marca`, `modelo`, `ano_modelo`, `ano_fabricacao`,
`exercicio`, `categoria`) e 17 propriedades não declaradas. `config/schemas/apolice.schema.json`
**nunca existiu**, embora `docs/sprint/A18/_README.md` o declarasse entregue: o Pydantic
`ApolicePayload` foi entregue em A18 L2; o JSON Schema não.

É a **mesma classe** que a [[ADR-284]] §3 fechou para o E2 — "o contrato não refletia
os writers vivos" —, aqui reaparecida em outro stage. Só não abortava porque o modo
global é `warn`.

Três consequências que não eram visíveis pelo enunciado do achado:

1. **`_schema_version_token` também resolve pelo mapa.** Toda row de apólice em
   `pipeline_artifacts.schema_version` estava carimbada com o hash do schema de
   veículo. A auditoria por row (A37.l13 / CTO-07) mentia.
2. **`dev/check_artifact_read_keys.py` é um terceiro consumidor**, e lê o mapa por
   `ast.literal_eval`. Valor não-literal levanta `ValueError` cru — o que descarta,
   por construção, qualquer desenho que troque o `str` por callable.
3. **`crlv.schema.json` era permanentemente inelegível ao flip `warn→strict`.** A
   [[ADR-284]] gateia o flip per-schema por baseline ≥7 dias zero-WARN; schema que
   emite WARN em todo write nunca limpa a baseline. São **dois bloqueios independentes**:
   o [#1599](https://github.com/davidrobert/mathoms/pull/1599) fechou o do CRLV
   (`source_artifact_id` não declarado); este fecha o da apólice.

## Decisão

### D1 — Schema-base polimórfico com discriminador declarado no payload

`SCHEMA_BY_STAGE["extract_comprovantes_bens"]` aponta para
`comprovante_base.schema.json`, que declara `tipo_comprovante` (`required`) e despacha
por `allOf/if-then/$ref` para o schema do ramo. O mapa **permanece `dict[str, str]` 1:1**,
então os três consumidores continuam alimentados por construção.

O discriminador é **enxertado pelo stage**, não pedido ao LLM: o tipo já é determinístico
em `_detect_tipo_comprovante`. O enxerto vive em `_stamp_stage_fields`, ao lado de
`prompt_version` e `source_artifact_id` — os campos que o stage acrescenta pós-`model_dump()`
e que, por escaparem do `extra="forbid"` do Pydantic, só existem para o JSON Schema se ele
os declarar. Foi essa a origem do #1599.

### D2 — `oneOf` por shape é proibido em schema de stage polimórfico

Medido, mesmo payload com **um** drift real (falta `corretor`):

| desenho | path emitido à telemetria |
| --- | --- |
| `oneOf` por `required` | `$` |
| `if/then` por discriminador | `$.corretor` |

`iter_errors` não faz union dos erros de ramo: emite **um** erro no keyword `oneOf`, com
os sub-erros em `error.context`, onde `_validation_paths` ([[ADR-284]] §B) não desce. O
efeito não é ruído — é **apagar o eixo medido**: `1 path em drift` parecendo pequeno
enquanto esconde 25.

Como a telemetria per-path **é o gate do flip**, schema cujo drift reporta sempre `$` é
indiagnosticável, logo permanentemente inelegível. Adotar `oneOf` trocaria a
inelegibilidade atual por outra, mais discreta.

E o argumento de classe: `oneOf` discrimina por **forma**, e forma não é identidade. Em
N=2 a exclusão mútua é sorte. A18 V2 traz RGI/IPTU de imóvel, que colide de frente com
`BemSeguradoImovel` (ambos carregam `endereco`/`tipo_imovel`); `oneOf` exige
**exatamente um** match e reprova a colisão com `$`, sem dizer qual ramo. Mesma lição de
[[ADR-364]] aplicada a contrato: identidade é declarada, não inferida.

> **Consequência para [[ADR-284]]:** a lista de critérios de elegibilidade ao flip
> ganha um item que ela não previa — *schema cujo drift colapsa na raiz não é elegível,
> porque a baseline zero-WARN não é diagnosticável.*

### D3 — Cada ramo mantém a própria strictness; o schema espelha o produtor e não adiciona política

`crlv.schema.json` segue `additionalProperties: false` (espelha `extra="forbid"`);
`apolice.schema.json` é lenient no topo com **todo** sub-objeto strict (espelha
`extra="allow"` + sub-models `extra="forbid"`, [[ADR-238]] D2). A assimetria é travada por
`tests/unit/pipeline/test_schema_leniency_lock.py` e sobrevive ao despacho — `allOf`
avalia ramos independentemente do `additionalProperties: true` do base.

Ramo strict precisa **declarar `tipo_comprovante`**: `$ref` para schema com
`additionalProperties: false` não enxerga as `properties` do documento que o referencia.

O schema **não condiciona** `lmi_brl`/`lmi_fipe_percentual` a `lmi_modo`, embora fosse
tentador: o Pydantic não enforça essa regra, e schema mais estrito que o produtor gera
WARN em payload legal — exatamente o que trava a elegibilidade ao flip. Dinheiro é string
decimal ([[ADR-090]]); `number` reprova.

### D4 — Leitor de corpus histórico deriva o tipo por forma; não há backfill

Rows anteriores a esta lane não têm `tipo_comprovante`. Isso **não** quebra leitura:
`_validate_schema` é chamado só de `write()`; nenhum caminho de leitura revalida. O leitor
que precisar despachar (o card S_PROTECAO, A19 · [[ADR-240]]) deriva por presença de
`placa`. Backfill está **descartado**: as rows são cifradas (#1592), e decrypt→update→re-encrypt
é caro e arriscado para ganho estético. A derivação por forma é a lógica que D2 proíbe no
**validador** — aqui ela é aceitável porque vive no **leitor**, onde errar é barato e
diagnosticável.

### D5 — O token de auditoria hasheia o fecho transitivo dos `$ref`

`_schema_version_token` hasheava só o arquivo mapeado. Sob D1 o arquivo mapeado é o base,
que **só despacha** — o token ficaria estável enquanto o contrato real muda atrás do
`$ref`. É o mesmo falso-verde, deslocado uma casa. Passa a hashear o conjunto ordenado do
fecho transitivo, o que retro-corrige três buracos preexistentes: `informe_base`,
`e2_llm_artifact` e `e5_analysis`.

## Alternativas consideradas

- **Resolver por callable (`SCHEMA_BY_STAGE: dict[str, str | Callable]`)** — descartada por
  medição: `dev/check_artifact_read_keys.py` lê o mapa por `ast.literal_eval` e levanta
  `ValueError` cru em valor não-literal. Trocaria um contrato mentiroso por um gate morto —
  e é o gate nascido do incidente do card que devolveu zero por três meses.
- **Stage separado para apólice** — contradiz [[ADR-239]] D8 (stage único polimórfico,
  decidido deliberadamente) e exigiria mexer em `STAGE_REGISTRY`/`FULL_ORDER`/orchestrator
  mais backfill das rows existentes.
- **Aninhar o payload sob `crlv:`/`apolice:`** (estilo `informe_base`) — resolveria de
  graça a cegueira do gate de leitura, mas quebra o shape flat que `vehicle_upsert`,
  `reconcile_apolice_bens` e a telemetria já leem, e é migration de payload cifrado.

## Consequências

- `crlv.schema.json` e `apolice.schema.json` passam a ser candidatos legítimos ao flip
  `warn→strict` via `mode_overrides` ([[ADR-284]]): a partir do merge, o write dos 9
  goldens produz zero record em `mathoms.pipeline.schema_validation` — é o dia 0 da
  baseline de 7 dias.
- `dev/check_artifact_read_keys.py` ganha duas capacidades: desce `allOf[].then.$ref` (sem
  o que reprovaria `payload["placa"]` do leitor de S_PROTECAO como chave inexistente) e
  reprova schema alcançável pelo mapa que não existe em disco.
- **Defeito nomeado, não corrigido aqui:** `_schema_to_validate` falha **aberta** no schema
  ausente (`return None, True`) e **fechada** no corrompido (`return None, False`). A
  assimetria é evidência de acidente, não de política — mas `validate_dict` tem callers fora
  do mapa e o blast radius não está medido. Esta ADR fecha a classe pelo gate de existência;
  o flip do runtime fica como follow-up.
- **Follow-up para [[A40.l58]]:** `e4_unified.schema.json` tem 5 ramos em `oneOf` e cai em
  D2 — drift sempre em `$`, cobrindo 7 artifact keys do E4. É a mesma inelegibilidade, num
  stage maior.
