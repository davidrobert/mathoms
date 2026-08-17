---
id: A40.l68
type: lane
title: "Balanço de stage fan-out: documento que some não pode sair como sucesso"
sprint: A40
plan: PLAN-deterministic-authority
status: planned
priority: P1
branch_slug: a40-l68-balanco-de-fan-out
owner: data-engineer
adrs:
  - "[[ADR-081]]"
  - "[[ADR-272]]"
  - "[[ADR-357]]"
depends_on: []
parallel_with:
  - "[[A40.l66]]"
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p1
  - area/pipeline
---

# A40.l68 — `a40-l68-balanco-de-fan-out`

> Aberta em 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] (Onda 2,
> itens 2a e 2b). **Paralela desde o dia 0** — não depende do seam da
> [[A40.l66]] e não compete pela mesma janela de rebaseline. Nasce `planned`
> apenas porque a Onda 0 abriu uma lane `open` de cada vez; o pickup pode
> promovê-la sem esperar ninguém.

## Problema

`extract_with_llm` faz fan-out sobre N documentos e devolve `success` sem provar
que os N foram contabilizados. Documento que entra na fila e não sai — porque o
leitor do formato não existe — desaparece **sem deixar rastro**: o run fica
verde e o relatório é publicado sobre corpus incompleto.

A causa medida no r6 é um resultado não-tipado na extração de texto:
`text_extractor.py` **lava a exceção do leitor** e devolve string vazia. O `.xls`
observado não é "texto vazio" — é **leitor ausente**, e as duas condições são
indistinguíveis para o chamador.

## Escopo

**2a — invariante de balanço.** `queued ≡ processed + errors + skipped(motivo)`
no `extract_with_llm`, com **resultado tipado** na extração de texto
(`texto | falha_de_leitor(motivo)`). Regras:

- `skip` → `review_reason` **nomeando o documento** ([[ADR-272]]);
- `success` exige balanço fechado;
- formato sem extrator falha **no E0**, não no meio do fan-out;
- o invariante mora no **contrato de retorno do stage** (stage log /
  `validation`), **não** em JSON Schema: com `processed = 0` não existe payload
  para o hook pós-write validar;
- denominador **enumerado** — lista declarada de stages fan-out, não descoberta
  por reflexão.

**2b — ladder [[ADR-081]] no E1.5.** `confidence < 0,7` → `review_reason` +
`degraded`, WARN-first com budget medido.

## Enforcement

WARN-first ([[ADR-357]]): `skipped(motivo)` + `needs_review`; `success=false`
**só** com balanço aberto. Budget medido sobre r5+r6 antes do flip; kill-switch
por env var. Estado terminal de documento não processado é `degraded` +
`needs_review`, nunca run abortado.

## Critério de aceite

- **Prova por mutação:** remover o leitor de um formato ⇒ motivo "leitor
  ausente" + documento em `needs_review` + balanço fecha. Sem a mutação, o teste
  nomeia o mecanismo sem exercitá-lo.
- Fixture com formato sem extrator falha **no E0** e não chega ao fan-out.
- `success=true` com `queued != processed + errors + skipped` é impossível —
  teste que constrói o desbalanço à mão.
- Cada `skipped` carrega motivo e identificador do documento no
  `review_reason`; taxa medida sobre r5+r6 e escrita na ADR-B.
- ADR-B aberta `Proposto` antes do PR de implementação. **Nenhuma emenda à
  [[ADR-342]]** — escopo distinto, decisão do co-design.

## Fora de escopo

- Ampliar [[A42.l4]] (dona de `validate_cross`): ela **preserva a disjunção
  declarada**, ganha citação da ADR-B e re-prioridade P1 no frontmatter, e nada
  além disso.
- `llm_call_log` e telemetria por tentativa → [[A42.l7]].
- Cache/pin de extração → depois da Onda 1 (§Anti-decisões do plano).
