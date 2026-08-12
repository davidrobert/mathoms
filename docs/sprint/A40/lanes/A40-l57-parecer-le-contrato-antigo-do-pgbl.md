---
id: A40.l57
type: lane
title: "O parecer lê o contrato antigo do bloco PGBL: guardrail com predicado morto e âncora que resolve null"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l57-parecer-le-contrato-antigo-do-pgbl
owner: prompt-engineer
adrs:
  - "[[ADR-375]]"
  - "[[ADR-233]]"
  - "[[ADR-200]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/llm
  - area/pipeline
---

# A40.l57 — `parecer-le-contrato-antigo-do-pgbl`

> **Aberta em 2026-08-12**, no fechamento da rodada de follow-ups (decisão do
> dono). Origem dupla: o handoff da [[A40.l7]] (retitulação da S8) **agravado
> pelo PR2 da [[A40.l34]]** (#1394), que mudou o contrato do bloco
> `previdencia_pgbl` de zero para **ausência**. Dono: `prompt-engineer` — os
> quatro itens são prompt/guardrail/âncora do parecer, o mesmo especialista
> fecha todos. Remedido em 2026-08-12 antes de abrir; um claim do handoff
> envelheceu e foi corrigido (o bucket existe, meu grep é que errou o padrão).

## Problema

O PR2 da [[A40.l34]] mudou o que `previdencia_pgbl` publica quando não há IRPF
processado: antes `status: "Calculado"` com números do proxy (e, no limite,
`limite_pgbl_anual = 0`); agora `status: "N/D"` com os campos prescritivos
**`null`** e nota que nomeia o insumo que falta. Quatro consumidores no parecer
leem o contrato velho:

1. **Guardrail FP-04 com predicado morto**
   ([`parecer_planejador.yaml:428`](../../../../config/prompts/parecer_planejador.yaml)):
   dispara sobre `previdencia_pgbl.limite_pgbl_anual=0`. Com ausência, o
   predicado **nunca mais é verdadeiro** no caso sem-IRPF — e o guardrail
   colapsava dois estados que agora são distintos (teto atingido ≠ sem
   evidência). Classe conhecida: valor novo no contrato, consumidor com `if`
   antigo decide ([[ADR-235]] por analogia).
2. **Âncora que resolve `null`**: o path canônico `$.previdencia_pgbl`
   (`yaml:409-410`, whitelist `:557`) segue ancorável — mas âncora em
   `$.previdencia_pgbl.limite_pgbl_anual` etc. agora resolve `null` no caso
   sem-IRPF, e `resolve_null` é **gatilho de retenção** do parecer (vocabulário
   da [[A40.l22]]). Risco: retenção espúria de item que só citou o bloco.
3. **Resumo de seção da S8**:
   [`section_summary_orchestrator.py:281`](../../../../backend/app/services/section_summary_orchestrator.py)
   — `_SECTION_KEYS["S8"] = ("previdencia_pgbl", "ratios")`. O resumo LLM da S8
   recebe o bloco em forma N/D; a copy do resumo precisa saber ler ausência sem
   inventar número.
4. **Enquadramento do bucket**: `previdencia_irpf` (título "Previdência e
   Eficiência Fiscal") está `aligned_with_layout: "S8"` — e a S8 foi retitulada
   pela [[A40.l7]] para "Carga Tributária PJ — Regime e Base Dedutível". O hook
   de manifest ([[ADR-200]]) segue verde porque o **id** existe; o drift é
   semântico, invisível ao gate.

## Sequência recomendada

Atacar **depois (ou junto) do PR3 da [[A40.l34]]**, que move o `restante` para a
S8 e troca o registro do card da S7 — senão o realinhamento é feito duas vezes.
Não é `depends_on` duro: os itens 1 e 2 podem fechar antes, porque dependem só
do contrato do PR2, que já está em `main`.

## Critério de aceite

- FP-04 re-predicado sobre o contrato novo, distinguindo **teto atingido** de
  **sem evidência** — dois comportamentos de prompt, não um.
- Eval golden do parecer sobre payload N/D: **zero retenção espúria** por
  `resolve_null` em `$.previdencia_pgbl.*`, e zero proposta de "investigar PGBL
  do zero" no caso sem-IRPF.
- `PROMPT_VERSION` bumpado ([[ADR-233]]; hook já enforça).
- O enquadramento do bucket revisado contra o título vigente da S8.

## Gatilho de subida de prioridade

P2 → P1 se um run de dogfood mostrar retenção por `resolve_null` em
`$.previdencia_pgbl.*` — aí o dano deixa de ser hipotético.
