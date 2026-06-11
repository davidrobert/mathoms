---
id: ADR-288
type: adr
title: "Identificador fiscal ilegível em extração LLM degrada para None determinístico — nunca hard-fail retryable"
status: Decidido
date: "2026-06-11"
relates_to:
  - "[[ADR-216]]"
  - "[[ADR-238]]"
  - "[[ADR-081]]"
  - "[[ADR-157]]"
supersedes: []
superseded_by: []
aliases: ["ADR 288", "cnpj unknown informe aluguel", "pii ausente extracao llm"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/llm
---

# ADR-288 — Identificador fiscal ilegível em extração LLM degrada para None determinístico

**Status:** Decidido • **Data:** 2026-06-11 • **Relaciona** [[ADR-216]]
(extractor informe aluguel), [[ADR-238]] (precedente `data_adesao`),
[[ADR-081]] (needs_review canônico), [[ADR-157]] (prompt_version/cache).

## Contexto

Incidente prod 2026-06-11 (workspace dogfood): `extract_informe_aluguel`
falhou para informe QuintoAndar — o CNPJ da imobiliária não estava legível
no texto extraído do PDF, o LLM (instruído a não alucinar) emitiu
`"<UNKNOWN>"`, e `imobiliaria_cnpj` era required com `pattern=^\d{14}$` no
boundary Pydantic. Resultado: 4 retries queimados (124s) num dado que o LLM
nunca conseguiria ler, e o informe inteiro (valores de aluguel — o dado de
valor real) perdido. Mesma falha de modo do [[ADR-238]] (`data_adesao`
required em informe regressivo). Bug latente adjacente: a coerção de máscara
(`12.345.678/0001-90` → dígitos) existia só como instrução de prompt — CNPJ
mascarado emitido pelo LLM também hard-failava.

## Decisão

Em schemas de extração LLM (`pipeline/llm/schemas/`), **identificador
fiscal (CNPJ/CPF) é `Optional` com normalização determinística
`mode="before"`**: strip de tudo que não é dígito; sobrou exatamente o
comprimento esperado (14/11) → aceita; senão (sentinel, vazio, truncado)
→ `None`. O documento sobrevive; ausência é informação válida, não erro.

Guardrails para a degradação não ficar invisível:

1. **Telemetria de presença** no log estruturado do stage
   (`imobiliaria_cnpj_present`/`locador_cpf_present`) — detecta drift de
   layout/extração de texto sem logar PII.
2. **Prompt com contrato positivo**: ausente/ilegível → `null`, proibindo a
   categoria placeholder (não enumerando sentinels); LLM reduz `confidence`
   e registra em `notes`.
3. **JSON Schema do hook pós-write** espelha: `["string","null"]` + pattern,
   campo permanece em `required` (a chave sempre é emitida pelo
   `model_dump`; só o valor é nullable).
4. `PROMPT_VERSION` bump minor (v1.1.0 → v1.2.0) — contrato de saída mudou;
   cache invalidado ([[ADR-157]] sub-decisão 7).

Não-decisão: **sem clamp determinístico de `confidence`** no validator —
quanto a ausência de um identificador rebaixa a confiança é juízo de
extração (prompt regra 12), não regra hardcoded; informe pode ser perfeito
nos valores e só não trazer o CNPJ.

## Consequências

- Caso CNPJ-ausente passa na 1ª validação: zero retries (era 4/124s),
  informe persistido com `imobiliaria_cnpj=null`.
- Downstream já tolerava: `real_estate_metrics.PropertyInput.imobiliaria_cnpj`
  é `str | None`; CNPJ não é join key em nenhum call-site (matching
  informe→imóvel é por endereço, informe→membro por `locador_cpf`).
- Relaxamento backward-compatible puro: payloads antigos continuam válidos.
- Padrão vale para futuros extractors de informe (proventos, previdência):
  identificador PII ilegível → `None` determinístico + telemetria de
  presença, nunca required+pattern hard-fail.

## Critério de aceite

- `<UNKNOWN>` / `""` / `"N/A"` / truncado → `None`; máscara → 14/11 dígitos;
  regressão em `tests/test_informe_aluguel_schema_unit.py`.
- JSON Schema aceita `null` e segue rejeitando string fora do pattern.
- Log do stage emite flags de presença; nenhum identificador bruto em log.
