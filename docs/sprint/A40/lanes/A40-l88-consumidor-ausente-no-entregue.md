---
id: A40.l88
type: lane
title: "Consumidor ausente no entregue: o produto emite a ressalva, a seção e o aviso — e nenhum dos três chega ao leitor"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l88-consumidor-ausente-no-entregue
owner: product-designer
depends_on: []
adrs:
  - "[[ADR-416]]"
  - "[[ADR-129]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/frontend
  - area/report
---

# A40.l88 — `consumidor-ausente-no-entregue` (RR5-01, RR5-03, RR5-04)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[REPORT-REVIEWS-active]] §r5 — **RR5-01** (Crítico, P0), **RR5-03** (Crítico, P0),
> **RR5-04** (Alto, P0). Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Admissão na A40** (a sprint não admite lane nova desde 2026-08-03): os três são **P0
> que alcança o usuário** e nenhum tem dono de arquivo em lane viva. Linha retro-registrada
> em §Fora do sprint. Precedentes: [[A40.l46]], [[A40.l87]].

> **Não muta E5 nem E3.** É render puro — **não zera o contador de 2 re-runs** da
> [[A40.l2]]. Por isso é a onda 1: mergeia a qualquer momento da janela.

## O fato, medido (2026-08-26)

Três superfícies emitidas pelo produtor **não têm consumidor no entregue**. É a mesma
classe em três lugares, e é o defeito da própria **KR-C** ("nº de seções que renderizam ==
nº com narrativa emitida") num array diferente.

| # | O que é emitido | Onde morre |
|---|---|---|
| **RR5-01** | 5 notas metodológicas do parecer | `NotaMetodologica` é declarada em [`planner-review.ts`](../../../../frontend/src/lib/api/planner-review.ts) e referenciada **só** pelo próprio DTO; nenhum componente itera o array. Tier `premium`, sem truncagem no backend |
| **RR5-03** | Seção de proteção patrimonial | [`S_ProtecaoSection.tsx`](../../../../frontend/src/components/report/sections/S_ProtecaoSection.tsx) existe completa e **já tem hide-when-empty** (`return null` na `:18`); `MIGRATED_SECTIONS` não contém a chave e o `switch` não tem o `case`; [`report_layout.yaml`](../../../../config/report_layout.yaml) declara `enabled: false` |
| **RR5-04** | Aviso de que há mais riscos | O PDF mostra o total e lista 5; o disclosure existe na tela e **não** no print. O CSS de print esconde o resumo e tenta abrir o bloco com uma custom property **inerte** — a metade que funciona é a que esconde |

**A nota que mais dói:** uma das cinco declara o diagnóstico patrimonial com confiança
**insuficiente**, num run que pausou com seis avisos retidos. O produto renderiza o
diagnóstico e descarta a ressalva do próprio modelo sobre ele.

## O que a medição já descartou

- ~~"a seção de proteção é feature — ligar exige construir o componente"~~ — **refutado na
  U1**: o componente existe, está completo e tem hide-when-empty. A condição escrita no
  próprio YAML (*"P3 liga quando o componente existir"*) **já está satisfeita**. É registro
  + flag + baselines, não feature.
- ~~"ligar a seção publicaria estado vazio para todo cliente"~~ — **refutado**: era a
  objeção que travou o flip na [[A40.l7]], e o `return null` da `:18` a responde.
- ~~"RR5-01 entrega zero das cinco notas"~~ — **PARCIAL** no cético: uma converge ~100
  caracteres com um risco que **é** renderizado. Quatro de cinco se perdem inteiras.
- ~~"o dano do print CSS é na tela"~~ — a [[A40.l7]] examinou o mesmo arquivo e concluiu o
  inverso. O comentário no componente registra a crença invertida, e **com base nela** a
  legenda foi enfraquecida de "N de M" para só o total. O fix apaga o comentário: preservá-lo
  manteria o cúmplice.

## Escopo

1. **Gate RED antes de qualquer fix** — polaridade inversa de `check_view_model_contract.py`
   (que pega *leitor sem emissor*): este pega **emissor sem leitor** no entregue. Vermelho
   sobre os três achados antes do primeiro conserto.
2. **RR5-01** — iterar `notas_metodologicas` no bloco do parecer. Gate: o smoke E2E assere
   presença de ≥1 nota quando o payload traz ≥1.
3. **RR5-04** — estado real em vez de CSS (bloco aberto sob mídia print, ou lista plana) +
   assert de regressão sobre o aviso de truncagem. Restaurar a legenda "N de M" e **apagar**
   o comentário que afirma o oposto.
4. **RR5-03** — `MIGRATED_SECTIONS` + `case` + `enabled: true` + baselines de print e PDF.
   **Exige sign-off do dono**: reverte decisão escrita da [[A40.l7]].

## Fora de escopo

- O **conteúdo** da ressalva e o limiar que ela cita → [[A40.l89]] (o alvo republicado).
- A regra de risco que deveria ter emitido o ponto urgente → [[A40.l90]].
- Baseline visual regenerada sem inspeção — inspecionar a olho, nunca `--update` cego.

## Sequência de entrega (ordem dura)

`1 → 2 → 3 → 4`. O item 2 vem **antes** do 4 e não é indiferente: publicar uma seção nova
enquanto o produto ainda não consegue enunciar a própria confiança é adicionar superfície
antes de adicionar honestidade. Ressalva primeiro, seção depois.

## Critério de aceite

- O gate do item 1 falha por **mutação nas duas direções**: emissor sem leitor ⇒ vermelho;
  leitor restaurado ⇒ verde.
- As 5 notas aparecem no `report.txt` da captura de render, e o percentual de carteira não
  classificada deixa de ter zero ocorrências no entregue.
- O PDF passa a declarar o truncamento, ou entrega os 12.
- A seção de proteção aparece no ToC e nas âncoras quando há dado, e **some** quando não há.
- Baselines de print inspecionadas a olho, com o diff descrito no PR.
- Concluído = PR mergeado em `main` com CI verde.
