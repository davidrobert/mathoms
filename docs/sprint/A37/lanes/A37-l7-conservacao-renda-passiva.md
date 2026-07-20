---
id: A37.l7
type: lane
title: "Conservação de renda passiva sem gate runtime + dict de fontes não-conservativo"
sprint: A37
status: planned
priority: P1
branch_slug: a37-l7-conservacao-renda-passiva
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p1
  - area/pipeline
  - area/dados
---

# A37.l7 — `conservacao-renda-passiva` (CTO-01 + DE-04)

> Compõe com [[A36.l3]] (gate E7 pausa run em conservação): esta lane adiciona
> o **check** que falta; a A36.l3 dá **dentes** ao conjunto. Não duplicar — se
> a A36.l3 abrir junto, coordenar severidade/tier no mesmo PR de
> `validate_cross`.

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

1. **Sem CV runtime (CTO-01):** nenhum dos 15 CVs de
   `scripts/validate_cross.py` cobre `passive_income`; a conservação
   (`headline = Σ(fontes) − distribuição PJ − ganho de capital`, exclusões por
   design ADR-191/ADR-336) existe só como teste golden sobre fixture sintética
   (`tests/test_e5_conservation_invariants.py::test_renda_passiva_conservation`).
   Um drift real mudaria o headline em ~8× — a cobertura da despesa essencial
   saltaria de ~11% para ~88%, invertendo a tese central — **sem gate**.
2. **Dict não-conservativo (DE-04):** `distribuicao_pj_titular` (excluída do
   headline por design) mora **dentro** de
   `passive_income.renda_passiva_por_fonte_brl`; somar o dict dá 7,84× o
   headline. Nenhum consumidor determinístico soma hoje, **mas o dump chega ao
   LLM do parecer** (bloco `$.passive_income` no manifest; a distribuição PJ
   sobrevive à truncação ao lado do headline) — risco real na superfície LLM.

## Escopo

- **CV17**: `Σ(fontes que compõem o passivo) == renda_passiva_anual_brl`
  (cents, tolerância zero), com os componentes excluídos parametrizados
  conforme a ADR de referência — simétrico ao CV16.
- **Shape**: mover `distribuicao_pj_titular` para campo irmão explícito (ex.:
  `renda_ativa_pj_excluida_brl`) para o dict fechar com o headline —
  auto-conservativo é mais barato que gate. Atualizar schema E5 + consumidores
  (grep: tipos do frontend, manifest do parecer — coordenar com [[A37.l1]] se
  os bumps de manifest coincidirem).
- Golden de conservação atualizado para o novo shape.

## Critério de aceite

- CV17 presente em `validate_cross.py`, verde no payload dogfood real (KR-C) e
  **vermelho** num payload mutado (unit com fonte vazando pro headline).
- `Σ(renda_passiva_por_fonte_brl) == renda_passiva_anual_brl` no payload novo.
- Teste de regressão do shape: consumidor que somava o dict antigo não compila/
  falha explicitamente (mudança de contrato visível, não silenciosa).

## Risco

Médio (mudança de contrato E5): mitigar com varredura de consumidores no PR e
bump coordenado do manifest do parecer.
