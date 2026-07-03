---
id: A28.l11
type: lane
title: "guardrails pós-LLM do parecer: confiança rebaixada sob premissa fallback + filtro 3-vias de campos_faltantes"
sprint: A28
plan: PLAN-report-trust
status: planned
priority: P1
branch_slug: parecer-guardrails-pos-llm
adrs:
  - "[[ADR-294]]"
  - "[[ADR-295]]"
depends_on:
  - "[[A28.l2]]"
parallel_with:
  - "[[A28.l9]]"
  - "[[A28.l10]]"
tags:
  - type/lane
  - sprint/a28
  - status/planned
  - priority/p1
  - area/llm
---

# A28.l11 — `parecer-guardrails-pos-llm` (Onda 2 · Should · redefinida no co-design prompt-engineer)

## Problema

No dogfood `72883bde`, o parecer E6: (a) elevou a probabilidade de IF de 31% a
risco "Alta" com `confianca: alta` **sem saber que 10/10 premissas do Monte
Carlo eram fallback** (o manifest não projeta `premissas_economicas` ao
exec-context); (b) pediu em `campos_faltantes` o path
`$.composicao_familiar.dependentes` quando o dado existe sob
`$.irpf_kpis.dependentes` (path errado para dado presente). Padrão do repo:
prompt é best-effort; **invariante é garantido deterministicamente no
orchestrator** ([[ADR-294]]/[[ADR-295]]).

**Fora do escopo (decidido no co-design):** guardrail de sanidade da TRS mora
na [[A28.l2]] (E5, onde o número nasce) — esta lane só **consome** o flag
`ratios.rentabilidade.status="suspeito"`. O pedido de
`$.protecao_patrimonial.apolices` estava **correto** (o dado não existe no E5 —
bug da [[A28.l6]]) e não deve ser suprimido enquanto a l6 não fechar.

## Escopo

Todos os itens são pós-processamento/anotação determinística — **zero custo LLM
adicional, zero reask** (coerce/mutação pós-validação, nunca raise —
[[ADR-292]]/[[ADR-294]]):

1. **Confiança sob premissa fallback — duas camadas:**
   - Pré-LLM (higiene): projetar `premissas_economicas` (status) no manifest +
     hint "status=parcial → confianca ≤ media em itens ancorados em
     `$.if_monte_carlo.*`, mencionando premissa de fallback". `PROMPT_VERSION`
     bump (invalida cache).
   - Pós-LLM (garantia): em `_generate_with_llm`, antes de `finalize_output`,
     quando `premissas_economicas.status == "parcial"` → rebaixar
     `confianca alta → media` de risco/sugestão cujas `ancoras[].path` começam
     com `$.if_monte_carlo`. Rebaixar é a direção segura (ADR-294: "dropar >
     promover"). Interação coberta: o validator dropa `impacto_estimado` quando
     `confianca != alta` — desejável, mas exige teste explícito.
2. **Filtro 3-vias de `campos_faltantes`** (pós-geração, antes de gravar
   `PlannerFieldRequest`):
   - Path pedido resolve não-nulo no E5 → **remover** + telemetria
     `field_request_spurious`.
   - Path nulo mas alias conhecido não-nulo (tabela: `composicao_familiar.
     dependentes → irpf_kpis.dependentes`) → **remover + reanotar** +
     telemetria `field_request_wrong_path` (alimenta expansão do manifest).
   - Genuinamente ausente → **manter** (sinal verdadeiro; ex.: apólices
     enquanto [[A28.l6]] aberta).
3. **Projetar `dependentes` explicitamente no manifest** (section
   `previdencia_irpf`, campo dedicado — não dump raw truncável) — ataca a raiz
   do path errado. Coordenar com [[A28.l6]] item 4 (quem tocar o manifest
   primeiro leva).
4. **Consumir o flag TRS da [[A28.l2]]:** hint no exec-context "não construa
   recomendação sobre rentabilidade quando `status=suspeito`" (precedente: hint
   de `status=sem_irpf` já existente no manifest).

## Critério de aceite

- Teste determinístico (b): E5 `premissas.status="parcial"` + item
  `confianca=alta` ancorado em `$.if_monte_carlo.*` → output `confianca=media`
  e `impacto_estimado is None`; `status="completo"` → intacto.
- Teste 3-vias (c): path não-nulo → removido + log; alias → reanotado + log;
  ausente → mantido + `PlannerFieldRequest` gravado
  (`VALID_FIELD_REQUEST_REASONS` estendido).
- **Nenhum guardrail marca `needs_review`** (assert em telemetria) — preserva o
  budget ≤15% do gate [[A26.l2]]; zero novo gatilho de reask.
- Manifest: `dependentes` projetado; `check_planner_manifest_coverage` verde;
  `PROMPT_VERSION` bump se o hint entrar.
- Fixtures sintéticas PII-zero; re-eval golden (owner-gated, US$12) **apenas**
  se o hint alterar redação — 1 rodada no fim da sprint aproveitando as
  gerações acumuladas (sinergia A26).

## Notas

- Pontos de inserção: `parecer_orchestrator._generate_with_llm` entre
  `_check_evidencia` e `finalize_output`; modelo de mutação per-item =
  `parecer_strict_enforcement` ([[ADR-295]]). **Não** implementar como red
  line/hard-block — premissa fallback rebaixa confiança, não bloqueia conselho.
- Skeleton em paralelo; **merge após Onda 0** (depende do flag da l2).

## Owner

Agente da lane; co-design `prompt-engineer` feito 2026-07-03.
