---
id: A39.l10
type: lane
title: "Piso de materialidade: roteamento a needs_review sobre o caminho não-certificado (ADR-344, transitório)"
sprint: A39
status: shipped
priority: P2
branch_slug: a39-l10-piso-materialidade
adrs: ["[[ADR-342]]", "[[ADR-344]]"]
depends_on: ["[[A39.l2]]", "[[A39.l4]]", "[[A39.l5]]", "[[A39.l7]]"]
tags:
  - type/lane
  - sprint/a39
  - status/shipped
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

## Nota de execução (2026-07-24) — lane FECHADA ([[ADR-344]] Decidido)

Co-design (financial-planner + data-engineer) confirmou **R$100** com refinamentos
incorporados na [[ADR-344]]:

- **Rationale corrigido:** R$100 é piso de **materialidade-de-interrupção/leak**,
  NÃO noise floor (ruído real é <R$1; a faixa R$1–R$100 é drop pequeno tolerado). A
  propriedade que fixa o valor é **agregação** — leak sistemático (viés-otimista de
  poupança) soma acima do piso e é pego.
- **Absoluto vence por domínio** (não só veto per-banco): relativo daria à conta
  MAIOR o MAIOR orçamento de drop silencioso (anti-ICP alta-renda).
- **Magnitude não separa drop de cosmético** (cosméticos R$7k–R$17k > drops reais
  R$296–R$1978) — o eixo é semântico (`conservacao_verificavel`); o corpus **valida
  + enumera regressões**, não escolhe o valor.
- **Transitoriedade:** code próprio `extract.conservation_above_piso` (só o ramo que
  escala; sub-piso reusa `incomplete_conservation`) → contável, deletável no sunset.
  Sem campo `piso_dependent` no schema (contrato sticky ≠ conceito transitório).
  Gatilho de sunset atrelado a cobertura de certificação; dois sinais
  (escalados-pelo-piso + escapando-abaixo-do-piso).

**Impl:** `_CONSERVATION_MATERIALITY_PISO_CENTS = 10000` (constante de módulo);
ramo não-certificado `gap > piso` escala, `≤ piso` WARN; certificado intocado.
Enum + `review_reason.schema.json`; fora de `BLOCKING_CODES`. Testes: 3 ramos
(certificado 1-cent HARD-escala; não-cert >piso escala; ≤piso WARN) + grep-gate
anti per-banco. **Medição no corpus real: 0/8 não-certificados-com-gap escalam a
R$100** (backstop inerte hoje, zero regressão em goldens — morde só gap material
futuro). Emenda-ponteiro datada em [[ADR-342]] (§Alternativas rejeitadas
reconciliada: tolerância proibida no certificado; piso no não-cert **aperta**).
