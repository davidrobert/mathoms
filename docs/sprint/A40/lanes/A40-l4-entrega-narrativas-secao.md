---
id: A40.l4
type: lane
title: "Entrega de narrativas de seção + re-triagem dos 7 achados que passam a aparecer"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P0
branch_slug: a40-l4-entrega-narrativas-secao
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p0
  - area/frontend
  - area/pipeline
---

# A40.l4 — `entrega-narrativas-secao` (RV3-03 + RV3-33)

> ⚠️ **Esta lane destrava conteúdo latente.** Fechá-la sem o checklist da
> §Critério de aceite publica 7 defeitos conhecidos de uma vez, por um PR correto.

## Problema

`SectionSummary.tsx:23` lê `narrativas[<ID maiúsculo>]`; o builder E5.N emite
`narrativas.summaries.<id minúsculo>` **como string**, onde o componente espera
objeto. Incompatibilidade **dupla** — chave *e* shape. Resultado: os parágrafos de
abertura do E5.N não renderizam em nenhuma seção.

**Precisão pedida pelo painel:** não são duas fontes desalinhadas, são **três**
competindo pelo mesmo parágrafo sem precedência declarada — (a)
`narrativas.summaries.s1..s10` (E5.N, string, nunca lido); (b)
`data.section_summaries["S1"]` (LLM, opt-in, default OFF); (c) derivação no
cliente. Seções que chamam `deriveSectionSummary` **renderizam** um sumário
derivado; o que está morto em 100% dos casos é especificamente **o texto do E5.N**.
Isso muda o fix de "trocar o path" para **"declarar precedência"**.

O gate CV9 "Narrativas completeness" passa verde porque mede **geração**, não
entrega — instância do padrão transversal (§Decisões nº 4 do sprint).

## Escopo

- Declarar precedência explícita em `SectionSummary`:
  `section_summaries[<ID>]` → `narrativas.summaries[<id>]` → `deriveSectionSummary`.
- Normalizar o shape (string vs objeto) no boundary, não no componente.
- Padronizar os call-sites de conclusão de chart em `narrativas.charts`.
- **Redefinir CV9** em `scripts/validate_cross.py` para medir entrega.

## Critério de aceite

- Nº de seções que renderizam parágrafo == nº com narrativa emitida (KR-C).
- Par de testes sobre **fixture único compartilhado** (TS + Python) com o shape
  real do builder e um texto sentinela por seção: o lado TS assere o sentinela no
  DOM; o lado Python assere que o builder emite naquele shape. Divergência futura
  quebra os dois.
- **Prova do gate:** emitir a narrativa sob a chave antiga tem de deixar o teste
  **vermelho**.
- **CHECKLIST BLOQUEANTE — re-triagem dos 7 inertes (RV3-33).** A lane só pode ser
  marcada `done` com os 7 re-verificados **contra o output já renderizando**, cada
  um com veredito registrado (`ainda-inerte` / `agora-visível-e-correto` /
  `agora-visível-e-errado`). Um deles é o ranking de despesa que apresenta a 14ª
  maior como a 3ª.
- Teste anti-hardcode: gerar os summaries com dois `config_overrides` que diferem
  só em parâmetros citáveis (meta, alíquota, prazo); todo summary que cita `%` ou
  "meta" tem de **variar**. Isso pega texto obsoleto antes de publicá-lo.
- Rebaseline de `test_report_view_model_snapshot.py` com `MATHOMS_UPDATE_SNAPSHOT=1`
  (roda em `backend/tests`, ~8min).

## Guarda anti-regressão

Duas: o **par de testes sobre fixture compartilhado** (forma) e o **teste
anti-hardcode** (conteúdo). O primeiro impede a divergência de shape voltar; o
segundo é o único que detecta narrativa citando parâmetro desatualizado — e nenhum
teste de forma o detecta.
