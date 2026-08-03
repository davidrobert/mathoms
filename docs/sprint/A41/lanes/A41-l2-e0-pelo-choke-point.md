---
id: A41.l2
type: lane
title: "Classificação do E0 passa pelo choke-point LLMService (budget, log, cache, sanitização)"
sprint: A41
plan: PLAN-launch-trust
status: planned
priority: P1
branch_slug: a41-l2-e0-pelo-choke-point
adrs:
  - "[[ADR-355]]"
depends_on: []
tags:
  - type/lane
  - sprint/a41
  - status/planned
  - priority/p1
  - area/pipeline
  - area/llm
  - area/security
---

# A41.l2 — `e0-pelo-choke-point`

> Único item da A41 que é ganho puro sem decisão pendente. Vem antes de
> [[A41.l3]] porque decide o *shape* do que atravessa o contrato de parser.

## Problema

`classify_by_llm` ([`scripts/route_documents.py:505`](../../../../scripts/route_documents.py))
instancia `anthropic.Anthropic` direto. A classificação do E0 portanto **não**
tem: hard-stop de budget ([[ADR-173]]), `LLMCallLog`, cache ([[ADR-307]]),
métricas OTLP ([[ADR-110]]) nem sanitização de prompt-injection ([[ADR-175]]) —
apesar de o input ser conteúdo de documento de terceiro, que é exatamente a
superfície que a ADR-175 cobre.

O mesmo vale para a sonda de disponibilidade em
[`document_classification.py`](../../../../backend/app/services/documents/document_classification.py)
(`_llm_prerequisites_skip_reason` faz `import anthropic` só para checar se o SDK
existe). Ela nunca instancia client, mas mantém o import de produção vivo — e o
gate de [[A41.l4]] vai marcá-la. A sonda migra junto (vira capacidade do próprio
choke-point), senão quem implementar o gate enfraquece a regra ou faz um refactor
não planejado.

**Pré-requisito medido — o choke-point não sabe enviar PDF.** `LLMService.call`
monta bloco multimodal `image_url` com data-URI
([`litellm_client.py:277`](../../../../pipeline/llm/litellm_client.py)). O E0
manda PDF sem camada de texto como **document block nativo**
(`{"type":"document","source":{"media_type":"application/pdf"}}` —
[`route_documents.py:463`](../../../../scripts/route_documents.py)). Rotear sem
resolver isso **perde a capacidade de visão para PDF escaneado**. Que o
`image_url` carregue PDF via litellm é hipótese: tem de ser provado com teste,
não presumido.

## Decisão

1. O choke-point ganha caminho para **PDF como documento**. Essa capacidade é
   compartilhada com [[A41.l3]] — é a razão pela qual as duas superfícies foram
   construídas por fora.
2. `classify_by_llm` chama `LLMService.call(...)` com `output_schema`
   (structured output substitui o parse de JSON cru + strip de markdown),
   `stage="route_documents"`, e `LLMConfig(call_hooks=ctx.llm_call_hooks,
   response_cache=…, metrics_emitter=…)`.
3. A precedência de chave permanece a de A37.l3: `api_key` explícita
   (`llm_config` DB-backed) vence a env var.
4. A sonda de disponibilidade sai de `document_classification.py` para o
   choke-point.

## Critério de aceite

- Run premium com documento de baixa confiança ⇒ **≥1 row em `LLMCallLog`** com
  `stage="route_documents"` e `cost_usd > 0`.
- PDF escaneado continua classificado por visão — teste com fixture sintética
  PII-zero. Sem regressão de capacidade.
- Budget estourado ([[ADR-173]]) ⇒ a classificação do E0 **para**, como qualquer
  outra chamada LLM.
- `temperature=0` preservado (invariante de determinismo já travado em
  `tests/test_route_documents_llm_determinism.py`).
- `rg 'import anthropic' scripts/route_documents.py backend/app/services/documents/document_classification.py`
  retorna vazio.
