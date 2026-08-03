---
id: A40.l24
type: lane
title: "Asserção \"0 LLM\" do gate F2 mede a camada errada — passa para o boundary do SDK"
sprint: A40
plan: PLAN-go-shell
status: open
priority: P1
branch_slug: a40-l24-gate-0-llm-no-boundary-do-sdk
adrs:
  - "[[ADR-355]]"
depends_on: []
parallel_with:
  - "[[TRACK-f2-cutover]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/llm
---

# A40.l24 — `gate-0-llm-no-boundary-do-sdk`

> **Fora do tema da A40, dentro da A40 de propósito.** Nasceu como `A41.l1` e foi
> promovida em 2026-08-03 por ser a única dos follow-ups da [[ADR-355]] com
> **consumidor datado**: enquanto a [[A41]] espera gatilho, o dono pode rodar
> `make go-parity` a qualquer momento e receber falso-verde. Uma lane `planned`
> em sprint `candidate` não aparece em `SPRINT_CURRENT` — sprint corrente é o
> único lugar de onde ela é pescável a tempo.
>
> Não compartilha arquivo com nenhuma outra lane da A40: roda em paralelo com
> qualquer onda.

## Problema

`_llm_artifact_count` ([`dev/go_parity_run.py:85`](../../../../dev/go_parity_run.py))
conta `pipeline_artifacts WHERE stage LIKE '%llm%'`. Isso enxerga o stub de
escalação do E2 e o artefato de `extract_with_llm` — e **não enxerga chamada LLM
bem-sucedida fora desses stages**:

- `scripts/e2/banks/caixa.py::_extract_via_llm` grava artefato **normal** de
  `extract_statements` quando a visão funciona. `requires_llm_fallback` só é
  setado quando ela **falha** (l.322, l.363, l.368) — sucesso não deixa rastro.
- O E0 roteia o documento e não produz artefato `%llm%` nenhum.

O §Critério de aceite do [[TRACK-f2-cutover]] afirma
`telemetria assert 0 invocação LLM (E0-route, E2, narrativas)`. Hoje essa
asserção é **vacuamente verde**: ela não pode falhar nos dois caminhos que mais
importam.

O track também declara que nada mais é executável sem o dono rodar o Tier-1
(`make go-parity`). Ou seja: existe consumidor com data. Se ele rodar antes do
fix, recebe falso-verde **e** paga o custo do run.

O pré-requisito já está em `main`: o spy nomeado sobre `anthropic.Anthropic`
entrou com #1141 ([`tests/fakes/anthropic_sdk.py`](../../../../tests/fakes/anthropic_sdk.py)
`RecordingAnthropicSDK`), e foi o que provou a [[ADR-355]].

## Decisão

A asserção de "0 chamada" passa a medir **no boundary do SDK**, não no artefato.
`_llm_artifact_count` permanece como sinal secundário (barato, roda sobre o DB),
mas deixa de ser o critério.

A reescrita do §Pré-condições 2 do [[TRACK-f2-cutover]] é **entrega desta lane**,
no PR dela — o track é de outra lane, e é assim que a mudança tem dono e momento
em vez de virar comentário solto.

## Critério de aceite

- **Prova de mutação, não inspeção:** fixture que força uma chamada de visão da
  Caixa ⇒ o gate fica **vermelho**. Sem esse teste o gate volta a ser vacuamente
  verde no próximo refactor.
- Run com `skip_llm=True` sobre o corpus do dogfood ⇒ 0 chamadas ao SDK e 0 rows
  novas em `LLMCallLog`.
- `docs/plan/GO_SHELL/tracks/f2-cutover.md` §Pré-condições 2 reescrita para a
  asserção no boundary do SDK, no PR desta lane.
- Ressalva em `docs/_MOC/OWNER-GATED-active.md` §1 removida quando o gate passar
  a morder (ela existe só enquanto a asserção mente).
