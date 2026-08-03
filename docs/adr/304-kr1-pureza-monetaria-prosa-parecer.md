---
id: ADR-304
type: adr
title: "KR1 do parecer — pureza monetária da prosa: fix de prompt + doutrina de enforcement"
status: Decidido
phase: "A27"
date: "2026-07-02"
relates_to:
  - "[[ADR-296]]"
  - "[[ADR-295]]"
  - "[[ADR-081]]"
  - "[[ADR-202]]"
  - "[[ADR-204]]"
  - "[[ADR-357]]"
  - "[[ADR-358]]"
supersedes: []
superseded_by: []
amended_at: ["2026-08-03"]
aliases: ["ADR 304", "KR1 prose purity", "R22 pureza monetaria"]
tags:
  - type/adr
  - status/decidido
  - area/llm
  - phase/a27
---

# ADR-304 — KR1 do parecer: pureza monetária da prosa (fix de prompt + doutrina de enforcement)

**Status:** Decidido (A27) • **Data:** 2026-07-02 • **Relaciona** [[ADR-296]] (citação
determinística — o contrato "zero R$ na prosa"), [[ADR-295]] (enforcement per-item da
citação), [[ADR-081]] (regex→LLM→needs_review).

> **Emenda 2026-08-03 (incidente P0 do enforcement, [[A40.l16]]):** a §2
> ("`==0` estrito é enforcement, não prompt") e a §3 (timing) estão
> **revogadas**. A condição que a §3 impôs — *"validar contra tráfego real"* —
> foi cumprida por acidente e **reprovou**: sob o prompt vigente 2.2.0, 7 runs
> apagaram 1–4 conselhos verificados (16 itens) e 1 derrubou o entregável
> inteiro. A §1 (fix de prompt, persona 1.1.0 · yaml 1.6 · detector
> `_REAIS_RE`) **permanece vigente e não é tocada**. A política operativa de
> `number_in_prose` volta a ser a da [[ADR-296]] §Re-eval holdout: **budget
> monitorado, não invariante `==0`**. Ver §Emenda 2026-08-03 ao final.

## Contexto

O **KR1 da A27** exige `number_in_prose_violation == 0`: o LLM do parecer nunca deve escrever
valor monetário na prosa (a [[ADR-296]] fez o LLM emitir âncoras e o pipeline renderizar o
valor da folha E5). Eval de 2026-07-01 (120 gerações, holdout sintético PII-zero n=24×5)
media **61 instâncias de R$ na prosa em 38/120 runs (32%)**, mediana 0.

Diagnóstico (co-design `prompt-engineer` 2026-07-02) achou a raiz: **o prompt se
contradizia.** `config/agents/planner_persona.md:119` mandava o `diagnostico_geral` "citar
2-3 números materiais já no body" — instrução literal de escrever R$ na prosa no campo de
100% de cobertura. R17 (premissa-base "na mesma frase") induzia o valor-base monetário
inline em raciocínios de percentual (ex.: "renda tributável de R$ 720.000"). E a regra
ADR-296 estava enquadrada como "regra de citação", não como invariante de prosa.

## Decisão

### 1. Fix de prompt (config-only, bump persona 1.0.0→1.1.0 · yaml 1.5→1.6)

- `diagnostico_geral`: referencia dimensões pelo **conceito** + âncora; nunca R$ inline.
- **R17 reconciliado:** premissa-base = taxa/percentual/prazo (permitidos na prosa); valor
  monetário-base → âncora, nunca inline.
- **R22 (nova):** invariante categórico de pureza monetária — nenhum campo textual pode
  conter valor em R$ (nem "720 mil reais", nem por extenso), **inclusive** como premissa de
  cálculo. Percentuais/taxas/múltiplos/prazos permitidos. + few-shot negativo↔positivo do
  caso "valor-base em cálculo".
- Detector estendido (`parecer_evidencia._REAIS_RE`): pega valor **sem** prefixo R$ ("720
  mil reais", "720.000 reais", "3 milhões de reais") — o LLM podia driblar o `R$`.

**Resultado (eval 2026-07-02, mesmo holdout, detector robusto):** R$ na prosa **61→7
(↓88%)**, mediana 0, densidade de âncoras **12→14 (KR2 melhorou** — valores viraram âncora),
conformidade 100%, per-parecer violações 0.

### 2. Doutrina: `==0` estrito é enforcement, não prompt

O resíduo de 7 é **cauda estocástica** (5 runs/120 = 4,2%, espalhados por 5 fixtures × 1,
todos os estratos) — não um padrão fixável. Atingir `==0` estrito por prompt num gerador
estocástico é irrealista; cada rodada custa ~US$26 e não converge. **O caminho canônico
para o KR1==0 estrito é uma camada de enforcement** (pós-processa a prosa → strip/reescreve
ou `needs_review`), espelhando exatamente como a citação chegou a "0 errado publicado" via
enforcement per-item ([[ADR-295]]) e render determinístico ([[ADR-296]]). **Princípio:
prompt para qualidade, enforcement para garantia.**

### 3. Timing: shipar o fix agora, adiar o enforcement

O fix de prompt (ganho de 88% + KR2 melhor) é bancado já. O enforcement **não** se constrói
agora: o KR1 não está no caminho crítico (A27 só promove quando a A26 fechar) e o eval de
tráfego real (l2 do plano LAUNCH_TRUST / A26.l2) vem de qualquer forma — o resíduo em dados
reais pode ser diferente. **Follow-up:** construir o enforcement de pureza monetária
(análogo à [[ADR-295]]) quando a A27 for promovida + validar contra tráfego real.

## Alternativas rejeitadas

- **Iterar o prompt até 0** — teto estocástico (~4%); diminishing returns + US$26/rodada
  sem convergência garantida.
- **Construir o enforcement agora** — perfeccionismo prematuro num KR fora do caminho
  crítico; melhor validar o resíduo em tráfego real antes.

## Consequências

- **Positivas:** −88% de R$ na prosa; densidade de citação subiu; contradição do prompt
  removida; detector robusto a "mil reais"/extenso. Doutrina de enforcement documentada.
- **Custo:** KR1 não fecha `==0` estrito por ora (7/120, mediana 0) — depende do enforcement
  (follow-up) + tráfego real.
- **Gate:** eval owner-gated; `number_in_prose_median == 0` mantido; `densidade ≥ piso 5`
  (mediana 14).

## Emenda 2026-08-03 — a doutrina `==0` da §2 cai; a §1 permanece

O enforcement previsto na §2 foi implementado no PR #875 e produziu, no workspace
de dogfood, o oposto do pretendido.

**O que cai:** §2 (a doutrina de que `==0` estrito se atinge por enforcement) e
§3 (timing). **O que fica:** §1 — o fix de prompt (persona 1.0.0→1.1.0, yaml
1.5→1.6, R17 reconciliado, R22, `_REAIS_RE` estendido) segue vigente e é a razão
pela qual esta é emenda e não supersedure.

**Política operativa restaurada:** [[ADR-296]] §Re-eval holdout — `number_in_prose`
é **budget monitorado** (mediana 0 = maioria limpa), **não invariante `==0`**.
Aquele parágrafo havia rejeitado explicitamente os três remédios: *"Strip
quebraria a prosa; drop perderia item bom"*.

**Evidência que reprova a condição da §3.** Janela completa em que o contador
existiu — `pipeline_stage_logs.output_summary` →
`evidencia_verification.failures_by_layer.number_in_prose`, o único instrumento
persistido (19 runs do workspace de dogfood, 2026-07-10 → 07-31):

| data | prompt | `number_in_prose` (itens) | itens apagados | riscos entregues |
| --- | --- | --- | --- | --- |
| 2026-07-31 | 2.2.0 | 3 | 0 | **run `failed`, zero relatório** |
| 2026-07-29 | 2.2.0 | 1 | 1 | 11 |
| 2026-07-28 | 2.2.0 | 2 | 2 | 10 |
| 2026-07-27 | 2.2.0 | 3 | 3 | 9 |
| 2026-07-25 | 2.2.0 | 2 | 2 | 10 |
| 2026-07-23 | 2.2.0 | 0 | 0 | 12 |
| 2026-07-23 | 2.2.0 | 3 | 3 | 9 |
| 2026-07-22 | 2.2.0 | 4 | 4 | 9 |
| 2026-07-20 | 2.1.0 | 1 | 1 | 9 |
| 07-18 … 07-10 (10 runs) | 2.1.0 | 0 | 0 | 9–10 |

**Duas perdas de natureza distinta, não uma:** 7 runs **apagaram** 1–4 conselhos
(16 itens no total); 1 run **destruiu o entregável** (escalou para `needs_review`,
`items_dropped: 0`). São KRs diferentes — não somar.

**A taxa depende da janela, e a janela que importa é a do gerador vigente:**
87,5% (7/8) sob prompt **2.2.0**; 9,1% (1/11) sob **2.1.0**; 42,1% (8/19) sobre a
janela inteira. Contra os 4,2% projetados no holdout, o que reprova é o 87,5%.

Em todos os 19, `evidencia_failed: 0`. Isso prova que **toda âncora presente
resolveu certo** — não que todo número tenha âncora atrás: item com `ancoras: []`
não gera entry (fail-open, **RV2-10**).

**A identidade `riscos_count = 12 − items_dropped` é falsa** (afirmada em versão
anterior desta emenda como "exato"): quebra em 2 dos 7 runs completos afetados —
em 2026-07-22 porque `items_dropped` conta itens de **qualquer** tipo (riscos *e*
sugestões), e em 2026-07-20 porque **12 não é constante do gerador**, é o cap ≤12
da [[ADR-202]] §D5, atingido rotineiramente só sob 2.2.0. Consequência para o
KR-1 da §Frente 4 de [[PLAN-report-trust]]: "emitidos" tem de vir de
`publicados + items_dropped + riscos_truncados`, **nunca** da constante 12.

**A causa raiz é uma regressão de gerador, não o enforcement** — e sem nomeá-la a
próxima medição parece defeito endêmico. O enforcement mergeou em 2026-07-08
(#875) e ficou **dormente por 11 runs** (1/11, mediana 0, densidade de âncoras
mediana 9). Em 2026-07-21 o #1004 (exec context do manifest 2.0 — eviction por
seção, blocos densos) bumpou `PROMPT_VERSION` 2.1.0→2.2.0. A partir daí: 7/8
afetados, densidade de âncoras mediana **9 → 5**, tokens monetários na prosa
mediana **0 → 3,5**. O `model_id` não mudou na janela. É experimento natural entre
versões e **confirma** a tese §Não é o fim da pureza de prosa (abaixo): número na
prosa é *sintoma* de âncora ausente. O enforcement foi o amplificador; o gatilho
segue aberto.

**Budget declarado, medido, com unidade explícita** ([[ADR-358]] §Decisão 2 — o
que se declara é a distribuição, não o ideal):

| grandeza | baseline (mediana, n=8, prompt 2.2.0) |
| --- | --- |
| itens ofensores/parecer (`failures_by_layer.number_in_prose`) | **2,5** |
| tokens monetários/parecer (`money_tokens_total`) | **3,5** |
| densidade de âncoras/parecer (`ancoras_total`) | **5** |

Gate = *"não piora vs. este baseline, por `prompt_version`, janela ≥8 runs"*.
**Cuidado de unidade** ([[ADR-358]] §3): `failures_by_layer.number_in_prose` conta
**itens**; o eval publica `money_tokens_total` (**tokens**) sob o mesmo nome
`number_in_prose`. A "mediana 0" da [[ADR-296]] é meta do **gerador** e vira lane
própria (exec context + RV2-10) — não é gate desta camada.

**A evidência de §1 estava inflada na fonte** — registro necessário para que
ninguém re-derive a mesma decisão do mesmo número. O "61→7" foi medido por um
detector que (a) conta *matches*, não valores distintos (`_MONEY_RE` e
`_REAIS_RE` casam ambos "R$ 720 mil reais"; e cada risco tem 2 campos de prosa),
(b) inspeciona 3 campos dos 8+ que a R22 cobre, (c) é cego a `US$`. A direção do
ganho é real; a magnitude não é confiável.

**Erro de categoria registrado:** o KR1 é definido *"== 0 sobre todas as gerações
do **holdout**"* (A27 §KRs). Enforcement no caminho de produção não move um KR
medido em corpus de eval. A prevenção durável está em [[ADR-358]].

**Não é o fim da pureza de prosa.** O caminho de longo prazo é o gerador —
**RV2-10** (sub-citação fail-open: item com `ancoras: []` não gera entry, e o run
do incidente tinha densidade 6 contra mediana 11–14) + cobertura do catálogo de
citação. Número na prosa é *sintoma* de âncora ausente; o guardrail agia na
variável errada.

**O baseline do eval ficou stale, e a §Decisão 4 da [[A40.l16]] se apoia numa
premissa parcial.** "O eval mede o gerador, que está intacto" vale para a reversão
(ela não toca o gerador), mas o gerador **mudou** em 2026-07-21. Logo
`test_number_in_prose_within_budget` (mediana `== 0`) e o piso
`_DENSITY_FLOOR = 5` foram calibrados contra 2.1.0 e provavelmente reprovariam
hoje — a densidade real sob 2.2.0 é exatamente 5, isto é, passa raspando. Não se
re-roda aqui (US$ 26, owner-gated); a re-medição fica registrada em
[`OWNER-GATED-active`](../_MOC/OWNER-GATED-active.md) §2, como manda a [[ADR-358]]
§Corolário.

**O que esta emenda NÃO desfaz.** Os pareceres já entregues seguem truncados: o
artifact em `pipeline_artifacts` é imutável ([[ADR-204]]) e o `PlannerReview` o lê
como fonte de verdade, então a retenção passada continua **não declarada** até
[[A40.l20]]/[[A40.l22]]. As `Suggestion` que nunca nasceram não retroagem ao Inbox
de `/acao`. O bump de `EVIDENCIA_VERIFICATION_VERSION` impede que o cache **sirva**
a mutilação de novo; não repara a já entregue.
