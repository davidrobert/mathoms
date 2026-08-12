---
id: A40.l60
type: lane
title: "Conselho de seguro: cobertura recomendada sem ressalva fiduciária, e uma string que afirma invalidez sem fonte"
sprint: A40
former_ids: ["A40.l50", "A40.l58"]
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l60-ressalva-e-separacao-do-conselho-de-seguro
adrs:
  - "[[ADR-192]]"
  - "[[ADR-240]]"
  - "[[ADR-161]]"
depends_on: []
parallel_with:
  - "[[A40.l35]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/frontend
---

# A40.l60 — `ressalva-e-separacao-do-conselho-de-seguro`

> **Aberta em 2026-08-12**, no fecho da sessão S6/FP-010 (#1379/#1390) — dois
> achados verificados contra `main` e fundidos porque saem do **mesmo produtor**
> e carregam a **mesma classe de risco fiduciário**. Triagem: exceção da
> §Pendência 11 (P1 que alcança o usuário, **sem dono vivo** — o checkbox
> aberto da [[ADR-192]] não é dono). Co-design `product-manager` +
> `information-architect`; o desenho da separação vida×invalidez é do
> `financial-planner` (obrigatório no PR2). Move **KR-E** (honestidade da
> recomendação).

## O defeito, medido (2026-08-12)

O disclaimer fiduciário canônico ([[ADR-192]] §"Atualizações pós-revisão")
existe nos **4 cards da S9** (`HeroGapProtecaoCard`, `CoberturaSegurosCard`,
`AcoesMitigacaoCard`, `SucessaoCard`). O conselho de cobertura, porém, **viaja
para fora da S9 sem a ressalva** — e uma das superfícies afirma mais do que o
predicado sustenta:

| Superfície | O que imprime | Problema |
|---|---|---|
| Card `pontos_urgentes` (S10) — `PontosUrgentesCard.tsx`, alimentado por `pontos_urgentes_analyzer._seguro_vida_item` | "Contratar seguro de vida e invalidez" com prioridade Alta/Imediato | **sem ressalva fiduciária** — é o item mais vendável do plano, na seção de síntese |
| Narrativa da S9 — [`summaries_narrator.py:405-413`](../../../../pipeline/domain/services/narrativas/summaries_narrator.py) (`_S9_GAP_VIDA`) | "Seguros de vida **e invalidez** inexistentes — classificados como urgentes." | dispara por `protecao_gap_vida is True` — predicado **só de vida** ([[ADR-240]] KPI F). A metade *invalidez* é afirmada **sem fonte**: `disability_coverage_gap` ([[ADR-192]] §D3) vive no bundle que a [[A40.l35]] mediu calcular sobre zeros |
| APP_E — `config/report_layout.yaml:663` declara card `disclaimers` (`enabled: true`) | nada — `ApendiceESection` renderiza só `<SectionSummary/>` | o card de disclaimers **não tem componente**; a mitigação "disclaimer global (Apêndice B)" citada no §Risco da [[ADR-192]] nunca existiu |

**Nenhum gate cobre superfície nova.** Foi assim que a classe re-armou: o
disclaimer nasceu nos cards da S9 e o conselho migrou para `pontos_urgentes` e
para a narrativa sem que nada ficasse vermelho.

**Correção de enunciado que esta lane herda (não re-derivar):** o perfil
"titular PJ alta renda sem dependente" **não recebe** o item hoje — a
A40.l10/[[ADR-365]] §D4 já estreitou o predicado (ver
`docs/reference/rules/rule-elegibilidade-da-recomendacao.md`, tabela "Emite
item? não"). O defeito vivo não é conselho errado emitido; é (i) **afirmar
invalidez sem consultar fonte** e (ii) **omitir** o conselho de invalidez para
quem precisa dele — proteção de renda própria, o ponto cego clássico do PJ.
A regra determinística irmã foi removida em FP-010 ([[ADR-161]] §Emenda
2026-08-11): o produtor é único, o que torna esta lane o lugar certo de
consertar a boca de saída.

## Entregável

**PR1 — ressalva + gate (independente da l35; é o que sustenta o `open`):**

- Ressalva fiduciária nas 3 superfícies medidas (card `pontos_urgentes`,
  narrativa `_S9_GAP_VIDA`, card `disclaimers` do APP_E — este último é criar o
  componente declarado, não inventar seção).
- **O entregável durável é o gate cross-superfície**, não os 3 fixes:
  superfície que cite cobertura recomendada sem ressalva **hard-falha** (prova
  por mutação — fixture de superfície nova sem disclaimer fica vermelha; a
  classe fecha, não a instância).
- Emenda datada na [[ADR-192]] fechando o checkbox aberto ("Disclaimers
  fiduciários em todas as narrativas/cards que citem cobertura recomendada")
  **com o escopo medido escrito** — o checkbox sem escopo foi o que deixou a
  classe re-armar.

**PR2 — separar a string e parar de afirmar o que não se verifica (amarra de
entrega parcial):**

- `_ACAO_SEGURO_VIDA` e `_S9_GAP_VIDA` param de empacotar *vida* + *invalidez*
  numa afirmação só. Enquanto `disability_coverage_gap` estiver preso ao bundle
  zerado ([[A40.l35]]), **nenhuma superfície afirma presença ou ausência de
  invalidez** — nem recomenda cobrí-la.
- Exige **ADR `Proposto`** + co-design `financial-planner` (categoria/veículo —
  invalidez é proteção de renda própria; `rd_profissional` é RC profissional,
  produto distinto; [[ADR-240]] §D11 deixou `invalidez` fora do vocabulário da
  união de propósito).
- **Amarra (2ª cláusula do §Predicado, precedente [[A40.l20]]/[[A40.l27]]):**
  se a [[A40.l35]] não entregar os insumos, o PR2 é **declarado não-entregue
  por escrito** no fecho da lane — a metade "emitir conselho de invalidez" fica
  registrada como não-entregável, e a lane fecha com PR1 + a separação
  defensiva da string.

## Critério de aceite

1. Teste de render prova que **toda** superfície que imprime valor ou
   recomendação de cobertura carrega a ressalva fiduciária.
2. O gate falha com fixture de superfície nova sem ressalva (prova por
   mutação, não por presença).
3. Nenhuma superfície afirma presença/ausência de *invalidez* sem consultar a
   união documento ∪ cadastro ([[ADR-240]] D10-D12) — enquanto não houver
   fonte, o texto não menciona invalidez.
