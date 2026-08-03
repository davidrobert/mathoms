---
id: A41.l3
type: lane
title: "Caixa chama o SDK sem gate, sem choke-point e sem BYOK — decidir o reframe antes de dimensionar"
sprint: A41
plan: PLAN-launch-trust
status: planned
priority: P1
branch_slug: a41-l3-caixa-reframe-antes-de-dimensionar
adrs:
  - "[[ADR-355]]"
depends_on:
  - "[[A41.l2]]"
tags:
  - type/lane
  - sprint/a41
  - status/planned
  - priority/p1
  - area/pipeline
  - area/llm
  - area/security
---

# A41.l3 — `caixa-reframe-antes-de-dimensionar`

> `depends_on: A41.l2` não é preferência de ordem: as duas lanes mudam o mesmo
> contrato de parser, e o *shape* do que atravessa (um bool de política vs. um
> handle de LLM) é decidido lá. Invertido, a migração de ~10 módulos acontece
> **duas vezes**.

## Problema

`_extract_via_llm` ([`scripts/e2/banks/caixa.py:212`](../../../../scripts/e2/banks/caixa.py))
instancia `anthropic.Anthropic` dentro de `extract_statements`/`extract_invoices`
— ambos **não**-`is_llm` — e lê `os.environ.get("ANTHROPIC_API_KEY")` direto
(l.223). Três defeitos empilhados:

1. **Determinismo.** Não respeita `ctx.llm_calls_allowed` ([[ADR-355]]). É a 4ª
   superfície; a emenda de 2026-07-31 da [[ADR-150]] contou três.
2. **Conformidade com o modelo de negócio.** O E0 já respeita `api_key`
   explícita com precedência sobre a env (A37.l3); a Caixa não. Workspace com
   BYOK **cobra a plataforma** — contra o que o `PRODUCT.md` §4 promete. Não é
   dívida de determinismo, é conformidade de contrato.
3. **Segurança/FinOps.** PDF financeiro inteiro em base64 para a API, sem
   sanitização ([[ADR-175]]), sem `LLMCallLog`, sem budget ([[ADR-173]]).

**O enquadramento do deferimento pode estar errado, e isso muda a estimativa em
ordem de grandeza.** `extract_with_llm` **já é** o caminho gated (`is_llm`,
choke-point, budget, cache, sanitização) para documento que o parser
determinístico não resolve, e a [[ADR-342]] fez o stub `requires_llm_fallback`
funcionar ponta a ponta. **A Caixa é o único banco que atalha esse caminho.**

Gap real medido: `extract_with_llm` só faz multimodal para **imagem**
(`extractor.is_image(doc)`,
[`extract_with_llm.py:222`](../../../../pipeline/stages/extract_with_llm.py));
para os demais extrai texto e **pula o documento** se vier vazio — que é
exatamente o caso do PDF escaneado. É a capacidade que `caixa.py` implementou
localmente porque não existia no lugar certo.

Se isso procede, o fix não é threading do ctx por ~10 módulos: é **deletar o
call-site** e mover a capacidade PDF-como-documento para `extract_with_llm` —
mais barato, e **generaliza** (PDF escaneado de qualquer banco passa a ser
extraível, não só o da Caixa).

## Decisão

**Ato 1 — gate da lane: ADR `Proposto`** decidindo entre *delete-and-delegate* e
*threading do contrato `parser_fn`*. Donos: `senior-cto` + `prompt-engineer`
(o segundo porque mover a capacidade mexe em prompt, custo e determinismo do
`extract_with_llm`). A lane **não é dimensionada nem implementada** antes disso.

**Ato 2** — implementação do que a ADR decidir.

Contrato em jogo: `result = parser_fn(file_path, filename)`
([`extract_bank_documents.py:150`](../../../../scripts/extract_bank_documents.py)),
uniforme em ~10 módulos de `scripts/e2/banks/`. [[ADR-111]] proíbe resolver com
global ou contextvar.

## Critério de aceite

- ADR `Proposto` aberta e decidida **antes** de qualquer linha de implementação.
  Referenciada em prosa até o arquivo existir (wikilink órfão é hard fail).
- `rg 'import anthropic|anthropic\.Anthropic' scripts/e2/banks/` retorna vazio.
- PDF escaneado da Caixa continua sendo extraído — teste com fixture sintética
  PII-zero. Se a ADR aceitar perda temporária de capacidade, o documento vira
  `needs_review` **declarado**, nunca silencioso.
- Workspace com BYOK: a chamada usa a chave do workspace, e o gasto aparece em
  `LLMCallLog` atribuído a ele.
- Run com `skip_llm=True` sobre corpus com PDF escaneado ⇒ 0 chamadas ao SDK.
