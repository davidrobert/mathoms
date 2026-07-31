---
id: A40.l4
type: lane
title: "Entrega de narrativas de seção + re-triagem dos 7 achados que passam a aparecer"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l4-entrega-narrativas-secao
adrs:
  - "[[ADR-355]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
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
- **Declarar o sinal esperado do delta** (decisão nº 5 do painel): esta lane não
  recalcula número, então o sinal é `=` para todo campo monetário — qualquer
  divergência em `dev/golden_diff.py` no rebaseline é achado, não ruído de
  snapshot. Se um valor mover, pare: a narrativa está sendo gerada a partir de
  caminho diferente do que o card lê.

## Guarda anti-regressão

Três pernas independentes — e é a independência que remove a auto-referência:

1. **Par sobre fixture compartilhada** (forma) — `tests/fixtures/narrativas/e5n_delivery.json`,
   gerada pelo produtor, lida por `tests/test_e5n_delivery_contract.py` e por
   `frontend/tests/components/report/sectionSummaryDelivery.test.tsx`.
2. **Anti-hardcode** (conteúdo) — `tests/test_e5n_anti_hardcode.py`; nenhum teste
   de forma detecta narrativa citando parâmetro desatualizado.
3. **Regra estática** (estrutura) — regra 5 de `dev/check_chart_conclusion_parity.py`:
   em `sections/*.tsx` o bag `narrativas` só via `.charts`.

CV9 (`entregues=N/esperadas=M`) é a **quarta** perna, mas é telemetria de run, não
gate de PR — só roda no stage `validate_cross`.

## Medição — KR-C (render real via `MigratedSection`)

| | antes | depois |
| --- | --- | --- |
| seções que renderizam parágrafo de abertura | 7 | 13 |
| destinos declarados que entregam o texto do E5.N | **0 / 7** | **7 / 7** |

As 7 de antes vinham todas de `deriveSectionSummary` (S8, S9, S10, APP_A, APP_B,
APP_D, APP_E) — nenhuma do E5.N. As +6 são S1, S2, S3, S4, S7 e APP_C.

## Checklist bloqueante — re-triagem dos 7 inertes (RV3-33)

Códigos de **cluster** (não RV3-xx), de `SINTESE.md` §placar cético do run
`2026-07-29-573a54a7`. Verificados contra o output com a entrega ligada:

| # | Cluster | Veredito | Motivo |
| --- | --- | --- | --- |
| 1 | **C11** — runway canônico (ADR-335) calculado e nunca renderizado; alias colide de nome com cobertura da reserva | `ainda-inerte` | É campo do view-model, não de narrativa. Dos 7 destinos entregues, nenhum cita runway — o `s2`, que cita `cobertura_meses`, tem `summary_source: null`. A l4 não muda a superfície. |
| 2 | **C18** — narrativa do donut de despesas publica ranking com 4 categorias fixas e ordem falsa | `ainda-inerte` | A l4 **não** aponta os charts de S1/S2 para `narrativas.charts` (ADR-355 §Deferimentos): o texto com o ranking falso continua sem leitor. O usuário segue protegido pelo `deriveChartConclusion` do TS, que ordena de verdade. Dono: A40.l15. |
| 3 | **C29** — narrativa fiscal publica DAS estimado e alíquota efetiva que nenhum campo do payload sustenta | `agora-visível-e-correto` | Era o bloqueante de acender o `s8`. ADR-355 §D7: `das_aliquota_pct` passa a ser `None` sem fonte fiscal e o `s8` suprime a cláusula inteira, degradando para "Perfil tributário PJ pendente" (registro do irmão `impostos_pj`, ADR-236 §D5). Com fonte declarada, imprime valor declarado. |
| 4 | **C30** — `dev/explain_number.py` devolve números de fixture sintética sem marcar | `ainda-inerte` | Ferramenta de dev, fora do caminho de render. A l4 não a toca. |
| 5 | **C32** — narrativa determinística publica nome completo de adultos e de menor | `já-visível-antes-da-lane` | **A classificação "inerte" da SINTESE está errada para este.** O caminho é `narrativas.perfil_familia`, lido por `PerfilFamiliaCard` (`ReportShell.tsx:357`) sob a chave `"perfil_familia"` — que o produtor emite. Renderiza hoje, independente desta lane; as 5 fixtures E2E inclusive só têm `perfil_familia` no bag. A l4 não altera nem melhora. |
| 6 | **C36** — blocos que não movem decisão competem com o sinal (orçamento 44m, premissas 10/10 indisponíveis, checklist de sucessão todo negativo) | `ainda-inerte` | São cards, não narrativa; e a S9 curto-circuita em `<EmptyState/>` quando `bubble_riscos.data_state == "empty"`. Não bloqueia a lane. |
| 7 | **PD-20** — `goals?.trs_pct ?? 5.0` em `S7IndependenciaSection.tsx:96` (chave real é `goals.if_trs`) | `agora-visível-e-errado · pré-existente · owned by A40.l5` | O `s7` entregue cita `taxa_retirada_segura_pct` vindo de `goals.json`, ao lado de um card que lê a chave errada. A contradição já era visível via `perfil_familia_narrator.py:192`; a l4 adiciona superfície, não cria o defeito. Corrigir aqui faria o KR-A da l5 ("leituras órfãs 5 → 0") mentir. |

## Delta esperado

- **Monetário: `=`.** Nada da lane escreve campo do view-model. O sinal é
  `backend/tests/test_report_view_model_snapshot.py` passar **verde sem
  rebaseline** — o golden tem 31 chaves e não contém `narrativas` (o substrato
  roda `E1.5c→E3→E4→E5` e nunca chama E5.N). Rodar com `MATHOMS_UPDATE_SNAPSHOT=1`
  aqui só poderia mascarar regressão.
- **Visual: 8 dos 48 PNGs.** `S1`, `S2`, `S3`, `S7` × {light, dark} ganham o
  parágrafo derivado (as 5 fixtures E2E têm `narrativas` só com
  `perfil_familia`, então a camada 2 não dispara nelas). `S4` segue não-montada
  com a fixture `medium` (`real_estate: null`). As outras 9 seções mantêm markup
  byte-idêntico. Rebaseline **tem de rodar em CI Linux** — o próprio spec
  (`sections.snapshots.visual.spec.ts:22`) proíbe atualizar em macOS.
