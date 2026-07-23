---
id: A39.l10
type: lane
title: "Piso de materialidade: roteamento a needs_review sobre o caminho não-certificado (ADR-344, transitório)"
sprint: A39
status: planned
priority: P2
branch_slug: a39-l10-piso-materialidade
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l2]]", "[[A39.l4]]", "[[A39.l5]]", "[[A39.l7]]"]
tags:
  - type/lane
  - sprint/a39
  - status/planned
  - priority/p2
  - area/pipeline
  - area/dados
---

# A39.l10 — `piso-materialidade` (achado PC-08)

## Problema (certificação 2026-07-23)

O gate de conservação é **binário**: HARD-escala só quando
`conservacao_verificavel=True`, senão WARN (∞ — nunca escala). Não distingue gap
de −R$296 de −R$17k **no caminho não-certificado**. É defesa em profundidade: o
mecanismo primário é certificar o parser (l2/l4/l5/l7); o piso pega o resíduo
não-certificado até todo parser opta.

## Escopo

- **ADR-344 `Proposto` ANTES do PR de impl** (reabre alternativa rejeitada da
  [[ADR-342]] — "tolerância monetária no gate" — logo exige ADR-gate mesmo sendo
  P2; co-design financial-planner + data-engineer):
  - **Enquadramento decisivo (senior-cto):** o piso é **roteamento sobre o
    caminho não-certificado**, **não** tolerância sobre invariante. Caminho
    **certificado** (`conservacao_verificavel=True`) permanece **cents tolerância
    zero** (ADR-342 item 2 intocado). Caminho **não-certificado** hoje escala
    **nunca**; o piso move ∞ → materialidade = **estritamente mais estrito**.
  - Piso **global único** (não per-banco — respeita veto data-engineer contra
    institucionalizar row-drop).
  - **Transitório/modo-degradado:** north-star = certificar; ADR-344 exige
    **telemetria contando artefatos que dependem do piso** (senão vira permanente
    por inércia + anti-incentivo a flipar o flag).
- **Emenda-ponteiro datada à [[ADR-342]] item 2** (commit separado).
- Escala `needs_review` quando artefato não-certificado tem `gap > piso`.

## Critério de aceite

- ADR-344 `Decidido (A39.l10)` no merge; emenda-ponteiro em ADR-342.
- Teste: parser **certificado** com gap 1 cent ainda HARD-escala (piso **não**
  afeta caminho certificado); não-certificado com `gap < piso` → WARN (como
  hoje), `gap > piso` → `needs_review`; piso é constante **global única**
  (grep-gate contra threshold per-banco).
- Contador de artefatos "dependendo do piso" emitido (auditável como transitório).
- `depends_on` os flips primários (l2/l4/l5/l7) — piso é backstop, não substituto.

## Risco

Médio — reabre parcialmente uma alternativa rejeitada; o **enquadramento é o
entregável** da ADR-344 (roteamento ≠ tolerância). Risco de anti-incentivo
mitigado por telemetria + north-star declarado. P2 trailing.
