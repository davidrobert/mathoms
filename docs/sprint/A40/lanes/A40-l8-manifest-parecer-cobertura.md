---
id: A40.l8
type: lane
title: "Cobertura do manifest do parecer: dado renderizado inalcançável pela narrativa"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P1
branch_slug: a40-l8-manifest-parecer-cobertura
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p1
  - area/llm
---

# A40.l8 — `manifest-parecer-cobertura` (RV3-08 + teto declarativo)

## Problema

Nenhum path do manifest do parecer toca as duas seções em questão, e a mesma
`section_whitelist` gateia `get_e5_section` e `planner_drill_down.py:145`. O
`tool_trace` do run tem 5 chamadas, nenhuma ali. A família **vê** os números no
card, mas o parecer não os integra à narrativa. O gate próprio já avisa — e emite
`EXIT=0`.

**Correção de mecanismo do painel:** não existe tool loop em produção. A whitelist
**não está no caminho de leitura** do LLM, só no de **citação pós-LLM**.
Consequência: "ampliar a whitelist" é **no-op** para a narrativa e produziria um
falso-fechado. A trilha correta é **projetar `context_section` no corpo orçado** +
ampliar o enum.

**Split de ownership.** A metade imobiliária é `prompt-engineer`. A metade
tributária **não é fechável na camada de prompt**: o campo não existe no contrato
E5, então a projeção hard-falha no gate; e a [[A40.l9]] mostra a seção zerada, então
projetar zeros ensinaria o modelo a narrar "carga ≈ 0" — trocando um silêncio por
uma **afirmação falsa**. Metade tributária → `data-engineer`, atrás da [[A40.l9]].

**Achado novo (fora dos 33).** `max_total_input_tokens` e `max_tool_iterations` são
**teto declarativo**: parseados e nunca enforçados. O único teto vivo é
`max_exec_context_bytes`. Manter teto que não trava induz revisão a assumir
proteção inexistente — foi o que aconteceu nesta própria rodada.

## Escopo

- Projetar `context_section` da seção imobiliária no corpo orçado + ampliar o enum.
- Promover `warn_unmapped_layout_sections` de `report.warn` para `report.fail`,
  com allowlist declarada e com motivo.
- Enforçar ou **remover** os tetos declarativos, com nota.
- Contenção de PII por construção: o bloco novo é `key_value` com folhas
  **escalares declaradas uma a uma** — nunca o objeto de imóvel inteiro (o
  sanitizer cobre identificadores por regex, não texto cartorial livre).

## Critério de aceite

- Gate falha **antes** do patch (seção habilitada sem `context_section`) e fica
  verde depois — red-before-green.
- **Zero eviction** do exec context na fixture de referência: o invariante é
  `evicted == []`, não "cabe no cap".
- Scan de PII com a seção nova na whitelist + identificador sintético injetado ⇒
  falha se sobreviver ao sanitizer.
