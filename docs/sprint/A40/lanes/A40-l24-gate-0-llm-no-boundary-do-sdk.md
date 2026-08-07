---
id: A40.l24
type: lane
title: "Asserção \"0 LLM\" do gate F2 mede a camada errada — passa para o boundary do SDK"
sprint: A40
plan: PLAN-go-shell
status: shipped
ship_pr: 1157
ship_date: "2026-08-03"
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
  - status/shipped
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

`_llm_artifact_count` (era `dev/go_parity_run.py:85`; hoje
[`llm_artifact_count`](../../../../dev/go_parity_llm_free.py) após a extração
desta lane) conta `pipeline_artifacts WHERE stage LIKE '%llm%'`. Isso enxerga o stub de
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

## Entregue 2026-08-03

**Correção de premissa desta lane.** O §Decisão dizia "medir no boundary do SDK".
Isso **não é alcançável no harness**: o run é disparado por `make pipeline-run`
e executa no worker Celery (ou em subprocess do shell Go), então o spy
`RecordingAnthropicSDK` — que vive no processo do teste — não alcança a chamada.
Instrumentar o boundary em produção exigiria estado mutável de módulo sempre
ligado, que [[ADR-111]] proíbe.

O que entrou no lugar, mais forte: **no Tier-1** o gate **impede** a chamada em vez
de detectá-la. `LLM_FREE=1` apaga `ANTHROPIC_API_KEY` do env do worker Celery **e**
do shell Go, e o harness exige o marcador na saída do `make` (scrub que não rodou
falha alto). Credencial ausente é garantia por construção **nesse tier**; detecção
pós-hoc seria sempre incompleta enquanto existir a rota alternativa ([[A41.l2]] /
[[A41.l3]] / [[A41.l4]]).

**Achado não previsto: #1151 inverteu a asserção.** Entre a escrita desta lane e
a execução, #1151 trocou a contagem de artefato por `requires_llm_fallback` —
que é setado **só quando a visão falha**. O gate passou a reprovar o braço sem
credencial (zero chamada) e a aprovar o que fez chamada paga. Como o Makefile
injeta a key só no braço Go, o veredito ficava invertido **entre os braços** na
configuração real do dono. Os três testes de #1151 que codificavam essa
polaridade foram removidos.

**Prova de mutação (o critério desta lane):** `tests/test_go_parity_llm_free_gate.py`
força a visão da Caixa com credencial e prova que a chamada acontece **sem**
setar o flag; reverter a polaridade de #1151 ou remover o scrub do Makefile
deixa a suíte vermelha (ambas verificadas).

**Reclassificado, não descartado:** `requires_llm_fallback` continua lido como
sinal de **corpus encolhido** ([[ADR-355]] §Consequências) — reportado, sem
reprovar. No Tier-1 o stub é o comportamento esperado.

### O que esta lane NÃO fechou

Estava só no [`_README` da A40](../_README.md) e em
[`OWNER-GATED-active.md`](../../../_MOC/OWNER-GATED-active.md) §1 — quem lesse a
lane sozinha concluía que os 4 critérios foram cumpridos. Não foram:

1. **Critério 2 (`run com skip_llm=True` ⇒ 0 chamadas ao SDK e 0 rows novas em
   `LLMCallLog`) não foi executado.** Exige a stack local do dono; a lane subiu a
   `shipped` com a prova de mutação (unit) e **sem** a prova ao vivo. O 1º
   `make go-parity` é que confirma a asserção mordendo — está em OWNER-GATED §1
   com os itens a conferir.
2. **A simetria de credencial ficou fechada só no Tier-1.** `llm_free =
   args.tier == "tier1"` deixou o **Tier-2** com a mesma assimetria que esta lane
   corrigiu — e o Tier-2 **custa dinheiro**: `_go-on-native` segue injetando a key
   do `.env` no shell Go enquanto `dev-worker-up` só herda o env do shell, então
   `.env` com chave + shell sem chave reproduz a divergência de 2986 vs 1002 bytes
   fora do escopo do `skip_llm`. Fechado depois por **#1169** com
   `assert_credential_symmetry`, que enforça simetria por **presença** (o Tier-2
   precisa da credencial nos dois braços) em `assert_preconditions`, antes de
   gastar run.

O erro de enquadramento do item 2 vale para quem retomar: o eixo do defeito é
**simetria**, não ausência. Scrub só serve ao tier que pode rodar sem a
credencial; o tier em que ela é legítima precisa da checagem oposta.

Colateral: `dev/go_parity_run.py` passou de 500 linhas (P2) → extraídos
`dev/go_parity_llm_free.py` + `dev/go_parity_errors.py`. E `_make` entrou no
autouse guard de `tests/test_go_parity_run.py`: `_restore_python_arm` agora
reinicia o worker com credencial (senão o gate deixaria a stack de dev do dono
sem a key — a mesma degradação silenciosa que esta lane fecha), e sem o stub um
teste unitário derrubaria o Celery do dono.
