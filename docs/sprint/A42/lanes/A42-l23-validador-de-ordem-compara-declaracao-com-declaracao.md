---
id: A42.l23
type: lane
title: "O validador de ordem compara declaração com declaração: `writes` falso passa, e um `reads` sobre ele valida contra ficção"
sprint: A42
status: open
priority: P2
branch_slug: a42-l23-validador-compara-declaracao-com-declaracao
owner: data-engineer
depends_on: []
adrs: ["[[ADR-087]]", "[[ADR-357]]"]
tags: [type/lane, sprint/a42, status/open, priority/p2, area/pipeline, area/dados]
---

# A42.l23 — `validador-compara-declaracao-com-declaracao`

> **Origem:** `PV9-30` ([[PIPELINE-REVIEWS-active]] §r9), aberto desde então **sem
> lane nem ADR** — o que a §Convenção item 3 do próprio registro chama de "bug
> deste índice". Re-enunciado aqui pela medição de 2026-08-31; o remédio que a
> linha prescrevia foi refutado em [#1908](https://github.com/davidrobert/mathoms/pull/1908).

## O defeito

`validate_full_order` (`pipeline/stage_spec.py:312`) monta `produced_by_prefix` a
partir de `spec.writes` dos stages anteriores e exige que todo `spec.reads` esteja
nele. Ele compara **declaração com declaração** — nada ancora nenhum dos dois lados
na realidade. Duas das 18 declarações de `writes` são falsas:

| stage | declara | faz |
|---|---|---|
| `generate_narratives` | `("generate_narratives",)` | escreve em `("analyze_finances", "analise_financeira")` — merge no payload do E5, por desenho |
| `validate_cross` | `("validate_cross",)` | **zero** call-site de write (`scripts/validate_cross.py`) |

**Medido — o validador não distingue verdadeira de falsa.** Um stage novo que
declare `reads` sobre cada uma:

| `reads=` | veredito |
|---|---|
| `("generate_narratives",)` — declaração **falsa** | **PASSA** ⚠️ |
| `("validate_cross",)` — declaração **falsa** | **PASSA** ⚠️ |
| `("analyze_finances",)` — declaração **verdadeira** (controle) | PASSA |

O controle é o que dá o veredito: os três casos são indistinguíveis para o
validador, porque o grafo é validado **contra si mesmo**.

## Por que ainda não deu prejuízo — e por que isso não é conforto

As duas declarações falsas caem exatamente na região onde o campo é **inerte**.
Mutação de `writes` nos 18 stages, um a um (`()` e `("xpto_inexistente",)`):

- **load-bearing: 8/18** — `extract_baseline`, `consolidate_baseline`,
  `extract_invoices`, `extract_statements`, `extract_with_llm`,
  `reconcile_transactions`, `categorize_transactions`, `analyze_finances`.
  Mutar qualquer um **REPROVA**. É a espinha do pipeline.
- **inerte: 10/18** — ninguém lê a chave. Mutar **PASSA**. As 2 falsas estão aqui.

⚠️ **Isto refuta a perna de medição do `PV10-10`**, que concluiu *"o campo é
ornamental, não load-bearing"* a partir de mutação em `generate_narratives` e
`validate_cross` — os **dois** stages de cauda onde ele é inerte por construção.
A conclusão foi generalizada da amostra que não podia refutá-la. O campo é
load-bearing em 44% dos stages, e a falsidade mora no complemento.

Logo o dano hoje é **zero**, e está a **um `reads=` de distância**: qualquer stage
futuro que consuma `generate_narratives` ou `validate_cross` passa no validador e
lê o vazio.

## O que já cobre, e o que não

| camada | cobre | estado |
|---|---|---|
| `validate_full_order` | `writes` errado nos **8** load-bearing (mutação REPROVA) | existe |
| `X5` da rodada unificada | stage que promete artefato e não entrega, **no run** | shipou em [#1906](https://github.com/davidrobert/mathoms/pull/1906) ([[A42.l21]]) |
| — | `writes` **falso** nos 10 inertes, estaticamente | **descoberto** |

## Remédio recomendado

**Ancorar a declaração na fonte, não fazer `writes ≠ ∅ ⇒ artefato emitido`** (esse
era o remédio prescrito no `PV9-30`, e reprovaria 4 stages benignos por run — ver
[[A42.l21]]).

Gate estático que, por stage, compara `StageSpec.writes` com os alvos de
`store.write(...)` encontrados no módulo que o orquestrador despacha
(`pipeline/orchestrator.py` linhas 145-146 dão o mapa stage → módulo). O
mecanismo já existe e está em produção: é o cross-check de dispensa do `X5`
(`dev/_unified_xchecks/execucao.py::_viola`, regex `_WRITE_ALVO`).

As 2 falsas reprovariam de imediato, forçando a decisão que esta lane não
antecipa — e que é o cerne:

> `writes` conflaciona **duas** perguntas. "Que chaves este stage disponibiliza
> como dependência?" (semântica de ordenação, o que o validador usa) e "em que
> chaves este stage escreve?" (fato de I/O). Para 16 stages elas coincidem. Para
> `generate_narratives` divergem — e declarar a verdade de I/O
> (`writes=("analyze_finances",)`) **quebraria a semântica de ordenação**, porque
> passaria a satisfazer o `reads` de quem depende do E5 sem poder produzi-lo.

## Critério de aceite

- [ ] Um `reads` declarado sobre uma declaração **falsa** REPROVA; sobre uma
      **verdadeira**, PASSA. (Hoje os dois passam — a tabela acima é o baseline.)
- [ ] O gate deriva os alvos reais da **fonte do módulo despachado**, não de lista
      escrita à mão — lista à mão reintroduz a declaração-contra-declaração num
      arquivo novo.
- [ ] A ambiguidade de `writes` fica **resolvida por decisão declarada** (ADR):
      ou o campo passa a significar só ordenação (e `generate_narratives` declara
      `()`), ou ganha um segundo campo para o fato de I/O. Não deixar as duas
      leituras coexistindo — é o que produziu o achado.
- [ ] **Controle negativo:** o gate roda verde sobre os 8 load-bearing sem nenhuma
      mudança neles.

## Fora de escopo

Severidade. O `PV9-30` está `Alto`/`P1` desde o `r9`; a medição acima re-escala para
**Médio/P2** — o raio de explosão **atual** é zero e a cobertura de run já shipou.
Reabrir para `P1` exige um `reads` real sobre chave falsa, que não existe hoje.
