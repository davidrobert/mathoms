---
id: ADR-312
type: adr
title: "Canonicalização do vocabulário top-level do writer E2-llm: banco/tipo canonical-only + fallback permanente nos readers"
status: Proposto
date: "2026-07-07"
relates_to: ["[[ADR-286]]", "[[ADR-283]]", "[[ADR-244]]", "[[ADR-284]]", "[[ADR-278]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 312", "cutover vocabulario e2 llm", "canonical only writer llm"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/data-lineage
---

# ADR-312 — Canonicalização do vocabulário top-level do writer E2-llm

**Status:** Proposto · **Data:** 2026-07-07 · Fecha a §Não-decisões de
[[ADR-286]]; reusa o enforcement-por-ausência de [[ADR-283]]; preserva o
gate de informes de [[ADR-244]].

## Contexto

O writer LLM (`_output_to_e2_json`, `pipeline/stages/extract_with_llm.py`)
emite vocabulário top-level **duplicado**: `instituicao`+`banco` e
`tipo_documento`+`tipo`, com valores bit-idênticos por construção. A
duplicação nasceu aditiva na A32.l2 (PR #826), que pagou com golden de
paridade derivado (AST) o churn de identidade E3 que a [[ADR-286]]
§Não-decisões tinha adiado para o plano [[PLAN-data-lineage]]; o PR #828
fechou o gap de `membro` no reader. A dualidade de vocabulário produziu
3 bugs em ~6 semanas (skip-list de posições furada, `institution` vazia
no E3, membro perdido) — a classe é sempre a mesma: writer e reader
falam vocabulários diferentes sem gate.

Co-design 2026-07-07: `data-engineer` + `senior-cto` (aprovado com
condições). Divergência entre eles — telemetria de hit dos fallbacks
legados — fechada pelo `senior-cto` (protocolo anti-loop): **sem
telemetria**; rows de `pipeline_artifacts` são imutáveis e sem TTL, o
fallback nunca fica órfão, e telemetria só justificaria um sunset que
recriaria a alternativa C rejeitada.

## Decisão

1. **Writer emite apenas o vocabulário canônico top-level** — `banco` e
   `tipo`; remove as cópias `instituicao` e `tipo_documento`. O escopo é
   estritamente **top-level**: `investimentos[].instituicao` (aninhado)
   é vocabulário canônico do item de investimento — sem sibling `banco`,
   com consumidores vivos (`investments_consolidator`,
   `top_ativos_analyzer`, `exposicao_cambial_analyzer`) — e **não muda**.
2. **Schema `e2_llm_artifact.schema.json`**: `required` flipa de
   `[instituicao, tipo_documento, moeda]` para `[banco, tipo, moeda]`;
   os campos legados permanecem como properties opcionais documentadas
   (presentes apenas em rows antigas). Validação é on-write
   (`DBArtifactStore.write`), então rows antigas nunca revalidam.
3. **Fallback permanente nos readers, sem sunset e sem telemetria** —
   decisão consciente, dívida nomeada e barata (~4 `or` triviais,
   cobertos pelo golden). Rows antigas (mai–jun/2026) nunca são
   migradas nem re-extraídas (zero custo LLM).
4. **Readers sem fallback ganham o fallback no mesmo PR**:
   `e4_categorizer_adapter` (leitura de `tipo` para
   `_INVESTMENT_POSITION_TYPES` e de `tipo_documento` para o gate
   `is_investment_doc` de [[ADR-244]] — ambos passam a ler
   canônico-primeiro com fallback, cobrindo artifacts novos E rows
   antigas) e `statement_preprocessor` (branch de síntese de período de
   fatura lê só `tipo` — gap **pré-existente** de A32.l2, nomeado e
   fechado aqui).
5. **Enforcement por ausência** (padrão [[ADR-283]]): o golden de
   paridade ganha teste de que o writer não emite `instituicao` nem
   `tipo_documento` top-level — assert sobre as keys emitidas pelo
   writer, não sobre o schema (schema opcional não proíbe emissão).
6. **Pin de estabilidade K4**: teste prova que a `natural_key` estampada
   (`stamp_natural_key`) é idêntica entre o artifact canonical-only e o
   shape legado equivalente — protege a ordem canônico-primeiro de
   `_first` em `e2_natural_key.py` contra refactor silencioso.

## Alternativas rejeitadas

- **B — apertar só o schema** (required inclui canônico, writer segue
  dual): preserva a fonte da classe de bug indefinidamente.
- **C — backfill das rows antigas + drop dos fallbacks**: migration de
  dados de produção (runbook + snapshot + janela) para economizar `or`s
  triviais; custo alto, benefício marginal.

## Não-decisões

- **`membro` permanece** vocabulário canônico do artifact LLM: não é
  duplicação (schema o declara, E4 o consome, reader tem fallback desde
  PR #828). Canonicalizar para `documento_titular` trocaria um canônico
  por outro sem ganho. Não reabrir.
- **Baseline do flip strict** do `e2_llm_artifact` (runbook
  `schema_validation_strict_flip.md`) deve ser gerado **após** este
  cutover — baseline pré-cutover capturaria a dualidade.

## Consequências

- Identidade E3 **não muda**: os valores canônicos já são emitidos e
  lidos canônico-primeiro desde o PR #826; remover as cópias é no-op
  para `AccountGrouper.key`/grouping. Goldens E3/E4/E5 passam **sem
  rebaseline** (gate explícito do PR).
- A garantia de legibilidade de rows antigas é por construção + fixture
  sintética PII-zero (não há verificação sobre dado real de produção).
- Docstring stale em `extract_with_llm.py` (afirma que
  `SCHEMA_BY_STAGE` mapeia o stage para `e2_extract.schema.json`;
  o mapping real pós-[[ADR-286]] é `e2_llm_artifact.schema.json`)
  corrigida no mesmo PR.

## Critério de aceite

- Teste de ausência dos campos legados top-level no writer; regressão
  E4/[[ADR-244]] (artifact novo `investment_report` canonical-only entra
  em `load_investment_positions`; row antiga só-legado idem); fatura de
  row antiga sem `tipo` não skipa por vocabulário no preprocessor; pin
  de `natural_key` pré/pós-cutover.
- `test_writer_emite_todos_required_do_schema` verde com o required
  novo; golden AST de chains sem exemptions novas.
- Suítes pipeline + backend verdes; goldens de execução sem rebaseline.
