---
id: A32.l2
type: lane
title: "contrato E2-LLM: tipo no writer + fallback tipo_documento nos readers + golden de paridade derivado + gate strict CI-only"
sprint: A32
plan: null
status: shipped
ship_pr: 826
ship_date: "2026-07-07"
priority: P0
branch_slug: a32-l2-e2-llm-contract-parity
adrs: []
depends_on: []
parallel_with: ["[[A32.l1]]", "[[A32.l3]]"]
tags:
  - type/lane
  - sprint/a32
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/llm
---

# A32.l2 — `e2-llm-contract-parity` (vocabulário writer↔reader + gates anti-recorrência)

## Problema

O writer LLM (`_output_to_e2_json`,
`pipeline/stages/extract_with_llm.py:400-413`) e os readers divergiram de
vocabulário por ~6 semanas sem sinal: writer grava `tipo_documento`,
readers leem `tipo` — `should_skip` e `key`
(`pipeline/domain/services/account_grouper.py:145,169`) e `from_e2_dict`
(`pipeline/domain/models/document.py:172`). Consequência: `cdbdetalhes` e
`investimentosposicao` (skip-list `_DEFAULT_SKIP_TYPES`,
`account_grouper.py:28`) **nunca são pulados** e entram na reconciliação
— metade dos 11 errors do P1 e o P3 inteiro (anachronic guard rodando
sobre posição de CDB). O fix A28.l8 de `banco` (commit `c2230844`) tratou
uma instância; esta lane fecha a **classe** do bug.

## Escopo

1. **Writer** — `_output_to_e2_json` passa a emitir
   `"tipo": output.document_type` ao lado de `tipo_documento`, espelhando
   o fix de `banco` (`extract_with_llm.py:403-405`).
2. **Readers (cobre artifacts antigos sem re-extração)** — `should_skip`,
   `key` e `from_e2_dict` aceitam
   `data.get("tipo") or data.get("tipo_documento")`, espelhando o
   fallback `banco`/`institution` já existente em `document.py:162`.
3. **Golden de paridade ESTRUTURAL derivado** — teste que extrai (a) os
   campos required de `config/schemas/e2_extract.schema.json` e (b) os
   campos lidos pelos readers (`from_e2_dict`, `should_skip`), e asserta
   que `_output_to_e2_json` os produz todos e que o parse não cai em
   fallback vazio para `institution`/`account_type`/`period`. Derivado do
   schema, não hardcoded — quebra sozinho quando um lado evoluir.
4. **Gate strict CI-only (decisão Q2 do owner)** — teste
   (`test_e2_schema_strict_corpus` ou similar) que valida corpus
   sintético de artifacts E2 contra os schemas em modo `strict`. Runtime
   segue `warn` (`pipeline.json → schema_validation.mode` inalterado).
   Atenção ao gotcha de suite: `_init_config`/`CONFIG_DIR` pinado no
   repo (poluição conhecida de `validate_dict` na suíte completa).

## Critérios de aceite

1. Fixture LLM com `tipo_documento=cdbdetalhes` é **pulada** pela
   reconciliação (teste de regressão); `investimentosposicao` idem.
2. P3 deixa de ser emitido — o doc nem entra no E3 (teste reproduzindo o
   cenário: posição com datas de aplicação antigas + skip).
3. Golden derivado quebra automaticamente se novo campo required do
   schema ou novo `d.get()` do reader não for emitido pelo writer
   (provar com mutação temporária no PR, depois reverter).
4. Gate strict CI-only verde sobre o corpus sintético; runtime `warn`
   intocado.
5. `pytest tests -q` verde; PR(s) mergeado(s) em `main` com CI verde.

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `pipeline/stages/extract_with_llm.py:400-413` | Writer `_output_to_e2_json` |
| `pipeline/domain/services/account_grouper.py:28,145,169` | Skip-list + readers `tipo` |
| `pipeline/domain/models/document.py:162,172` | `from_e2_dict` — padrão de fallback a espelhar |
| `config/schemas/e2_extract.schema.json` | Fonte do golden derivado |
| `config/schemas/e2_llm_artifact.schema.json` | Schema do writer LLM (não exige `banco` — por isso strict não pegava o P1) |
| `tests/unit/pipeline/test_period_plausibility.py` | Padrão de teste da A28.l8 |
