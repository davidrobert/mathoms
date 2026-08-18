---
id: A40.l68
type: lane
title: "Balanço de stage fan-out: documento que some não pode sair como sucesso"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P1
branch_slug: a40-l68-balanco-de-fan-out
owner: data-engineer
adrs:
  - "[[ADR-081]]"
  - "[[ADR-393]]"
  - "[[ADR-272]]"
  - "[[ADR-357]]"
depends_on: []
parallel_with:
  - "[[A40.l66]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
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

## Liberada e em execução — 2026-08-18

Promovida `planned` → `open` por decisão do dono. A **ADR-B** do plano é a
[[ADR-393]], aberta `Proposto` antes do PR de implementação.

Medido ao abrir a ADR, e é mais forte que o registro §r6 sozinho: r5 e r6 têm
`total_documents` **idêntico (171)** e `llm_calls` **7 vs 6**, ambos
`completed`. O limite da medição está declarado na ADR — `llm_calls` agrega mais
de um stage, então o delta é consistente com o skip do RV6-10 sem isolá-lo.

Descoberto ao mapear o terreno: são **dois** call-sites que devolvem
`(None, None)` — imagem vazia além do texto vazio — e **cinco** stages consomem
o `DocumentTextExtractor`. Só o `extract_with_llm` entra no escopo desta lane;
os outros quatro herdam a mesma cegueira e ficam declarados na [[ADR-393]] §D2,
não consertados em silêncio.

## 2a entregue — 2026-08-18 (#1526 · `4b3bff08`)

Leitor tipado (`extract_result` → `TextExtraction`), balanço
`queued ≡ processed + errors + skipped` com `success` exigindo o fechamento, e
`extract.reader_missing` WARN-first fora de `BLOCKING_CODES`. Quatro mutações
provadas, incluindo a que a lane pede (remover o leitor de um formato ⇒ motivo
nomeado + `needs_review` + balanço fecha), como teste permanente.

Três achados de execução que o planejamento não tinha:

1. **Dois** call-sites mudos, não um — imagem vazia além do texto vazio.
2. A chave `skipped` já existia como **booleano** nos early-returns do stage;
   minha lista teria criado a mesma chave com dois tipos. Renomeada
   `skipped_docs`.
3. Deslocar o seam **silenciou 18 dublês** que fazem `patch` em `extract`.
   Atualizados só os do E2-llm.

O `.xls` do RV6-10 ficou provado por execução: `openpyxl does not support the
old .xls file format`.

## §Pendência datada — 2b (ladder [[ADR-081]] no E1.5) · 2026-08-18

**Não entregue**, e não por falta de tempo: ao ler o terreno,
`extract_baseline.py:161` agrega confiança como
`min(confidences) if confidences else **0.0**`. Um ladder `< 0,7` cru dispararia
para **todo** run sem metadado de confiança, porque o `0.0` ali é **sentinela de
ausência**, não medição — é o mesmo "zero ≠ não medido" que este plano combate,
e um gate que dispara sempre ensina o operador a ignorá-lo.

Condição de retomada: `confidence` ausente modelado como estado próprio
(distinto de confiança baixa), com a taxa de disparo medida sobre r5+r6 **antes**
do WARN, na forma da [[ADR-393]] §D4. Dono: `data-engineer`. Enquanto isso a lane
fica `open` — 2a mergeado não fecha a lane.
