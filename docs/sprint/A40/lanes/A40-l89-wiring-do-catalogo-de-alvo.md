---
id: A40.l89
type: lane
title: "Wiring do catálogo de alvo: o produtor suprime o limiar por falta de procedência e o parecer o republica"
sprint: A40
plan: PLAN-deterministic-authority
status: blocked
priority: P0
branch_slug: a40-l89-wiring-do-catalogo-de-alvo
owner: prompt-engineer
depends_on:
  - "[[A40.l91]]"
adrs:
  - "[[ADR-399]]"
  - "[[ADR-416]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p0
  - area/pipeline
  - area/llm
---

# A40.l89 — `wiring-do-catalogo-de-alvo` (RR5-02)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[REPORT-REVIEWS-active]] §r5 — **RR5-02** (Crítico, P0).
> Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Esta lane é a RETOMADA do §Deferimento D3, não um locus novo.** O braço do `target`
> de `PE-2` e de `FP-6` no [[PIPELINE-REVIEWS-active]] §r7 está deferido desde 2026-08-21
> com donos nomeados: o catálogo determinístico mergeou (#1557, [[ADR-399]]) e **não foi
> wired** — produção segue publicando alvo do LLM. Abrir lane com nome próprio forkaria
> uma decisão que já tem endereço. O escopo abaixo executa o que o deferimento escreveu.

> **Muta E5 + prompt ⇒ zera o contador de 2 re-runs** ([[A40.l2]], estendida à l34/l35).
> Serializada atrás da [[A40.l91]] numa janela única de rebaseline.

## O fato, medido (2026-08-26)

Quatro `kpi_targets` têm `procedencia: null` com motivo nomeado — a supressão é deliberada
e documentada:

| KPI | Motivo declarado da supressão |
|---|---|
| taxa de poupança recorrente | duas fontes divergentes para o mesmo limiar |
| progresso rumo à independência | acompanhado pelo cone, não por alvo pontual |
| cobertura de proteção | capital ideal exige inventário confirmado ([[ADR-387]]) |
| carteira TRS | sem alvo canônico ([[ADR-191]]) |

**Três das quatro vazaram.** A tabela "Métricas a observar" renderizada publica alvo para
duas delas, e o plano de ação renderiza uma decisão fixando **alvo pontual** para exatamente
a métrica que o produtor declara sem alvo canônico.

O produtor suprime porque a procedência falta; republicar pela prosa devolve à família a
autoridade que o registro recusou — em três eixos de decisão ao mesmo tempo.

## O que a medição já descartou

- ~~"isto é o mesmo defeito das notas metodológicas e cabe na mesma lane"~~ — **refutado**:
  não compartilha superfície, dono, blast radius nem gate com um `.map()` faltando num
  componente. É produtor + schema + `PROMPT_VERSION` + janela de rebaseline. Tese comum não
  é lane comum.
- ~~"o parecer alucina o alvo"~~ — não. Ele autora um alvo porque **nada** no exec context
  o proíbe: o catálogo existe e não é lido.

## Escopo (executa (a)–(d) do §Deferimento D3)

1. O catálogo vira **leitor único do alvo publicado** na rota do parecer.
2. `target` com `procedencia: null` ⇒ o item perde o comparador, na prosa **e** na tabela.
3. Bump de `PROMPT_VERSION` (o modelo deixa de poder autorar alvo) + eval do enum de chaves
   de métrica.
4. O plano de ação não fixa alvo pontual para métrica sem alvo canônico.

## Fora de escopo

- Estender o leitor único à **superfície de risco** → [[A40.l90]]. A ordem é forçada: se as
  regras de risco lerem o catálogo antes do parecer, o ponto urgente passa a contradizer o
  alvo ainda autorado pelo LLM na tabela de métricas **do mesmo relatório**. Wiring primeiro.
- A base bruta/líquida da meta de independência → [[A40.l91]], que vai na frente.

## Forma canônica

Emenda datada à [[ADR-399]] **não** é necessária: o wiring é exatamente o que a D4 já decide.
Se o escopo exigir mudar o que a D4 isenta, a forma é emenda — e aí a lane é a [[A40.l90]].

## Critério de aceite

- Nenhum `target` publicado sobre `kpi_target` com `procedencia: null`, em nenhuma das três
  superfícies (prosa do parecer, tabela de métricas, plano de ação).
- Prova por mutação: injetar um `kpi_target` suprimido e exigir que o comparador suma.
- Delta de golden declarado `↑`/`↓`/`=`; rebaseline silencioso reprova.
- **Cap:** se a condição de retomada do D3 (*"nenhum rebaseline de golden em voo"*) não
  estiver satisfeita quando a janela abrir, esta lane e a [[A40.l90]] caem **juntas** para a
  A43 — não se separam.
- Concluído = PR mergeado em `main` com CI verde.
