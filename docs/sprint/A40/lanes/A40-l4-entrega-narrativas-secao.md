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
- **Corrigir o que a entrega passa a publicar** — nenhum defeito conhecido vai ao
  relatório: PII fora do texto (ADR-355 §D9), zero número de default de código
  (§D7-D8), zero afirmação duplicada com o empty state (§D7).

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
  `agora-visível-e-errado`). **A re-triagem bloqueou:** C29 e C32 viraram
  `agora-visível-e-errado` e foram corrigidos aqui; PD-20 também. Vereditos
  finais em §Checklist.
- Teste anti-hardcode **por parâmetro citado**, não por summary: para cada
  parâmetro citável, o trecho que o cita tem de conter o token do valor — com dois
  valores diferentes. A granularidade por summary (a primeira versão) fica VERDE
  quando se congela um literal entre outros parâmetros que ainda variam; medido:
  congelar `if_meta` em `summaries_narrator` deixa o assert coarse `a != b`
  **verde** e o caso por-parâmetro **vermelho**.
- Snapshot do view-model: **não rebaselinar**. Nenhum campo novo entra no
  view-model, então o sinal é `test_report_view_model_snapshot.py` passar verde
  **sem** `MATHOMS_UPDATE_SNAPSHOT=1`. Medido: 4 passed.
- **Declarar o sinal esperado do delta** (decisão nº 5 do painel): esta lane não
  recalcula número, então o sinal é `=` para todo campo monetário — qualquer
  divergência em `dev/golden_diff.py` no rebaseline é achado, não ruído de
  snapshot. Se um valor mover, pare: a narrativa está sendo gerada a partir de
  caminho diferente do que o card lê.

## Guarda anti-regressão

Cinco pernas independentes — é a independência que remove a auto-referência.
Cada uma foi provada por mutação (aplicada, vermelha, restaurada):

1. **Par sobre fixture compartilhada** (forma) — `tests/fixtures/narrativas/e5n_delivery.json`,
   gerada pelo produtor **na condição de produção** (sem
   `parametros_fiscais.json`), lida por `tests/test_e5n_delivery_contract.py` e
   por `frontend/tests/components/report/sectionSummaryDelivery.test.tsx`.
2. **Destino semântico** — `tests/fixtures/narrativas/e5n_destinations.json`: o
   mapa esperado seção → chave, declarado **fora** do layout, com a razão
   semântica por entrada. Sem ele as pernas liam o destino do layout e o aferiam
   contra o layout: declarar `summary_source: "s2"` na S2 passava 30/30. Medido:
   com ele, a mesma mutação deixa duas asserções vermelhas (mapa e conteúdo).
3. **Anti-hardcode por parâmetro** (conteúdo) — `tests/test_e5n_anti_hardcode.py`;
   nenhum teste de forma detecta narrativa citando parâmetro congelado.
4. **PII no output** — `tests/test_e5n_pii_guard.py`, 3 braços (sentinela por
   campo, forma de nome completo, regra estática de leitura).
5. **Regras estáticas** (estrutura) — regras 5 e 6 de
   `dev/check_chart_conclusion_parity.py`: bag `narrativas` só via `.charts`, e
   `summary: true` ⟺ `<SectionSummary sectionId="…">`.

CV9 (`entregues=N/esperadas=M`) é a **sexta** perna e telemetria de run, não gate
de PR — só roda no stage `validate_cross`. Os quatro predicados têm unit test
próprio (`tests/test_cv9_narrativas_delivery.py`), incluindo o caso
gerado-e-não-entregue construído de propósito.

## Medição — KR-C (render real via `MigratedSection`)

Medido nesta lane, não herdado: `git archive origin/main` para `/private/tmp`,
`node_modules` por symlink, **mesmo payload** (fixture
`tests/fixtures/narrativas/e5n_delivery.json` por path absoluto) nos dois lados,
render de todas as 17 entradas `enabled` pelo dispatcher. Detector: o parágrafo
de abertura é o primeiro filho do grid do `ReportSection`.

| | antes (`origin/main`) | depois |
| --- | --- | --- |
| seções que renderizam parágrafo de abertura | **8** | **13** |
| destinos declarados que entregam o texto do E5.N | **0 / 7** | **7 / 7** |

As 8 de antes: S8, S9, S10, APP_A, APP_B, APP_C, APP_D, APP_E. Nenhuma exibia
texto do E5.N — todas caíam no derivado, e a APP_C tem parágrafo **autoral**
próprio. As **+5** são S1, S2, S3, S4, S7 (a S2 pelo derivado, `summary_source:
null`; as outras 4 pelo E5.N).

**A APP_C não muda** — renderiza parágrafo antes e depois. A versão anterior
desta tabela dizia "7 → 13" e creditava "+6 … APP_C": o "antes" estava
subcontado por 1 e a APP_C entrava como ganho sem ter mudado. A própria ADR-355
se contradizia na §Contexto (contava 8 call sites de `deriveSectionSummary` e
declarava 7 seções com parágrafo). É a 5ª vez nesta sprint que contagem de
memória divergiu do medido — a partir daqui a tabela só aceita número com
procedimento descrito.

## Checklist bloqueante — re-triagem dos 7 inertes (RV3-33)

Códigos de **cluster** (não RV3-xx), de `SINTESE.md` §placar cético do run
`2026-07-29-573a54a7`. Verificados contra o output com a entrega ligada. **A
re-triagem bloqueou:** 2 dos 7 viraram `agora-visível-e-errado` e foram
corrigidos nesta lane (ver ADR-355 §D7-D9); os vereditos abaixo são os finais,
pós-fix.

| # | Cluster | Veredito | Motivo |
| --- | --- | --- | --- |
| 1 | **C11** — runway canônico (ADR-335) calculado e nunca renderizado; alias colide de nome com cobertura da reserva | `ainda-inerte` | Medido: `ratios.autonomia_financeira_meses` = 16,72 no payload, sem consumidor. É campo do view-model, não de narrativa. Dos 7 destinos entregues nenhum cita runway — o `s2`, que cita `cobertura_meses`, é órfão (`summary_source: null` na S2). A l4 não muda a superfície. Dono: A40.l5. |
| 2 | **C18** — narrativa do donut de despesas publica ranking com 4 categorias fixas e ordem falsa | `ainda-inerte` | A l4 **não** aponta os charts de S1/S2 para `narrativas.charts` (ADR-355 §Deferimentos): o texto com o ranking hardcoded continua sem leitor, e o usuário segue protegido pelo `deriveChartConclusion` do TS, que ordena de verdade. Medido no texto real: ele cita **só o topo**, então o defeito das "4 categorias fixas" não se materializa como "14ª aparece como 3ª" — materializa-se como *ordem inventada quando há empate/valores próximos*. Dono: A40.l15. |
| 3 | **C29** — narrativa fiscal publica DAS estimado e alíquota efetiva que nenhum campo do payload sustenta | `agora-visível-e-errado → CORRIGIDO` | O bloqueante de acender o `s8`. Três defeitos medidos (constante 6% fora de faixa, base = entrada na conta PF, ramo "sem regime + DAS" impossível) + o fallback declarado na §D7 original ser **inalcançável em produção**. Fix: a estimativa sai inteira; o `s8` afirma regime **declarado** + DAS **recolhido** (categoria E4 `das_simples`) e deixa carga/alíquota para a cascata do card irmão. ADR-355 §D7. |
| 4 | **C30** — `dev/explain_number.py` devolve números de fixture sintética sem marcar | `ainda-inerte` | Ferramenta de dev, fora do caminho de render. A l4 não a toca. |
| 5 | **C32** — narrativa determinística publica nome completo de adultos e de menor | `agora-visível-e-errado → CORRIGIDO` | A classificação "inerte" da SINTESE estava errada: `perfil_familia` renderiza hoje, independente desta lane. Mas a l4 **acendeu duas superfícies novas de PII** (`s4` citava `endereco.rua`; `s8` citava `contador_nome`), então não havia como fechar a lane sem tratar. Fix: primeiro nome para adultos, papel para o menor e para o contador, nada para endereço; guarda em 3 braços. ADR-355 §D9. |
| 6 | **C36** — blocos que não movem decisão competem com o sinal (orçamento 44m, premissas 10/10 indisponíveis, checklist de sucessão todo negativo) | `ainda-inerte` | São cards, não narrativa. Medido: a S9 curto-circuita em `<EmptyState/>` quando `bubble_riscos.data_state == "empty"` — e a l4 passou a **suprimir o `s9`** nesse ramo (o EmptyState já é a mensagem). Não bloqueia a lane. |
| 7 | **PD-20** — `goals?.trs_pct ?? 5.0` em `S7IndependenciaSection.tsx` (chave real é `goals.if_trs`) | `agora-visível-e-errado → CORRIGIDO (parcial)` | Não é "contradição 4 vs 5": sob ADR-191 §Emenda FP-03 o SWR 4% (que o `s7` cita, corretamente) e o yield-alvo 5% são conceitos distintos que **não se harmonizam** — "consertar" na direção de um número só desfaz FP-03 e encurta a meta de IF ~20%. O defeito era chave fantasma + rótulo: o card lê `ratios.rentabilidade.meta_pct`, imprime "Yield-alvo" (não "Meta") e não imprime nada quando o payload não traz. Residual: a meta ainda não é da família (ver §Residual). ADR-355 §D8. |

## Residual medido (não bloqueou, fica declarado)

| Item | Veredito medido | Dono |
| --- | --- | --- |
| **C11** — `ratios.autonomia_financeira_meses` = 16,72 calculado e sem consumidor | Confirmado. Campo do view-model, não de narrativa; nenhum dos 7 destinos o cita. | A40.l5 |
| **C18** — ranking do donut | O texto real cita só o topo; a instância "14ª maior como 3ª" **não se materializa**. O defeito é ordem inventada em valores próximos, e o texto segue sem leitor. | A40.l15 |
| **C30** — `dev/explain_number.py` devolve fixture sintética | Confirmado, fora do caminho de render. | — |
| **C36** — blocos que não movem decisão | Confirmado como cards; a parte narrativa (duplicação no empty state da S9) foi corrigida aqui. | A40.l5 |
| **PD-20** — a meta de TRS não é configurável | `RatiosCalculator()` roda com `RentabilidadeConfig()` default (5,0) e `PassiveIncomeConfig.trs_meta_pct` (construído do goal) **nunca é lido** pelo calculator. O wizard coleta `trs_pct` 0-20 e o relatório ignora. Ler `meta_pct` resolve a contradição intra-seção, **não** "a meta é da família" — isso é mudança de cálculo. | lane própria |
| **Base da cascata** — `receita_bruta = receita_pj_anual` herda o erro de categoria do CTO-05 no ramo de regime declarado; a fonte correta (`FinanceiroPJSnapshot.receita_bruta_total_anual`, ADR-238) é passthrough e não usada | Confirmado por leitura do `tributario_input_builder`. Mudança de cálculo ⇒ ADR + lane. | lane própria |
| **`renda_passiva_estimada_4pct`** cristaliza "4" no nome enquanto a taxa é configurável | O texto entregue é honesto (imprime a taxa real); a liability é o nome da chave no view-model. | A40.l5 |
| **`FORMULAS.md:94`** documenta `goals.trs_pct` como local do yield-alvo — chave que o payload não tem | Corrigido nesta lane (aponta `ratios.rentabilidade.meta_pct` + `goals.if_trs`), senão o próximo agente reimplementa o mesmo bug. | — |
| **Fixture compartilhada roda sobre E3 mínimo** (monetários zerados) | É contrato de **forma e string exata**, não amostra de conteúdo. A revisão de conteúdo é o anti-hardcode, que semeia valores. | — |

## Delta esperado

- **Monetário: `=`.** Nada da lane escreve campo do view-model. O sinal é
  `backend/tests/test_report_view_model_snapshot.py` passar **verde sem
  rebaseline** — o golden tem 31 chaves e não contém `narrativas` (o substrato
  roda `E1.5c→E3→E4→E5` e nunca chama E5.N). Rodar com `MATHOMS_UPDATE_SNAPSHOT=1`
  aqui só poderia mascarar regressão.
- **Visual.** Nas 5 fixtures E2E o bag `narrativas` só tem `perfil_familia`,
  então a camada 2 **não dispara nelas** e o delta é o parágrafo *derivado*: `S1`,
  `S2`, `S3`, `S7` × {light, dark} = 8 PNGs. `S4` segue não-montada com a fixture
  `medium` (`real_estate: null`). A `APP_C` perde o parágrafo derivado que
  duplicava o autoral (delta só se a fixture tiver `cenarios_conjuge`). O card de
  TRS da `S7` troca "Meta 5,0%" por "Yield-alvo …" **ou nada** — nas fixtures sem
  `ratios.rentabilidade`, nada. As demais seções mantêm markup byte-idêntico.
  Rebaseline **tem de rodar em CI Linux** — o próprio spec
  (`sections.snapshots.visual.spec.ts:22`) proíbe atualizar em macOS.
