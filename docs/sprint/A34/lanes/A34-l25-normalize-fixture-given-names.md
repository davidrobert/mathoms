---
id: A34.l25
type: lane
title: "Normalização repo-wide dos primeiros nomes de fixture (David/Mariana → sintéticos)"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P2
branch_slug: normalize-fixture-given-names
adrs: ["[[ADR-319]]"]
depends_on: ["[[A34.l24]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p2
  - area/seguranca
---

# A34.l25 — `normalize-fixture-given-names` (W1 · Saneamento — opcional)

## Problema

A [[A34.l24]] removeu o **sobrenome** identificador da família
(`Ferreira Campos` / `Camargo` / `Teixeira` + razão social `…LTDA`) de todo o
repo, mantendo os **primeiros nomes** `David`/`Mariana` — que já eram os
placeholders sintéticos aceitos como fixture em ~100 arquivos de teste desde as
lanes [[A34.l7]]–[[A34.l11]] (que deliberadamente os preservaram). O critério de
aceite da l24 mira `sobrenome` para a família e `1º nome` só para *prestador* —
portanto os primeiros nomes da família estão **fora** do escopo da l24.

Esta lane (opcional, decisão-independente do owner) cobre o caso 3 discutido no
pickup da l24: se o owner quiser **zero** ocorrência de `David`/`Mariana` como
nome de fixture no repo público, normalizá-los para nomes sintéticos genéricos
(ex.: `Ana`/`Bruno`) repo-wide.

## Escopo (grande — só executar sob decisão explícita do owner)

- ~100 arquivos de teste/fixture em `tests/`, `backend/tests/`, `frontend/tests/`
  usando `David`/`Mariana` como nome de membro genérico.
- **Rebaseline de goldens** (`tests/fixtures/pipeline_golden/**`, `llm_golden/**`)
  — cada um em commit isolado (gate `golden-rebaseline-isolation`, [[ADR-319]]).
- Snapshots visuais (Playwright) que renderizam esses nomes.

## Por que P2 / opcional

- `David`/`Mariana` sem sobrenome **não são identificáveis** (nomes comuns) — não
  é PII no sentido LGPD; é higiene cosmética.
- Blast radius alto (goldens + snapshots visuais) com risco de regressão
  desproporcional ao ganho.
- Contradiz o precedente [[A34.l7]]–[[A34.l11]], que tratou `David`/`Mariana`
  como fixtures sintéticos aceitáveis.

## Critério de aceite (se executada)

- `git grep -iw "David"`/`"Mariana"` = zero fora de inventário mascarado.
- Goldens rebaselinados em commits próprios com manifesto.
- Suíte + snapshots visuais verdes.

## Referências

- Origem: pickup da [[A34.l24]] (2026-07-09) — owner respondeu "1;2;3" às
  opções de profundidade; l24 executou opção 1, esta lane registra a opção 3.
- Contrato de gate: [[ADR-319]].
