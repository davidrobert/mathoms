---
id: A27.l3
type: lane
title: "A cobertura de lineage é medida contra a fixture e não contra a produção: três raízes monetárias ficam fora do universo do gate (a quarta era contagem lida como R$)"
sprint: A27
status: shipped
ship_date: "2026-09-01"
priority: P1
branch_slug: a27-l3-cobertura-de-lineage-medida-contra-a-fixture
owner: data-engineer
depends_on: []
adrs: ["[[ADR-281]]"]
tags: [type/lane, sprint/a27, status/shipped, priority/p1, area/dados]
---

# A27.l3 — `cobertura-de-lineage-medida-contra-a-fixture`

> **Origem:** `PV13-12` da rodada unificada **U5** ([[PIPELINE-REVIEWS-active]] §r13).
> Sucessora da [[A27.l2]], que **entregou** o gate com controle positivo — o defeito é no
> **universo**, não no mecanismo.

## O defeito

O gate fixa o conjunto de raízes monetárias sobre o payload da **fixture** de dogfood:
**14** raízes. O payload **real** deste run tem **18**. As **4 raízes a mais ficam fora do
universo do gate** — não são medidas como descobertas, e não contam como descobertas.

Efeito no número publicado: a cobertura sai **36%**; medida sobre o universo real é
**28%**. O viés é **otimista**, e cresce sozinho: raiz nova entra na produção sem entrar no
denominador.

## Por que não invalida a A27.l2

O controle positivo dela é real e o mecanismo funciona. O que esta lane conserta é o
**sujeito da medição** — exatamente a distinção que a [[A42.l14]] estabeleceu para
conservação. O gate mede bem o que decidiu medir; decidiu medir a fixture.

## O que foi medido (2026-09-01)

O enunciado **reproduz**, e a composição dele **não**. Medido sobre o artefato
`analyze_finances/analise_financeira` do run `40d1af2a` (ws `1b9f2cf5`), decifrado do
`pipeline_artifacts`:

| Medida | Enunciado (`PV13-12`) | Medido |
| --- | --- | --- |
| Universo da fixture dogfood | 14 | **14** ✓ |
| Universo do payload de produção | 18 | **18** ✓ (e 1 deles é falso-positivo — ver abaixo) |
| Cobertura publicada | 36% | **35,7%** ✓ |
| Cobertura real | 28% | **29,4%** (5/17, não 5/18) |

A fixture é subconjunto **estrito** da produção — as 14 dela estão todas nas 18. As 4 a
mais são `previdencia_pgbl`, `real_estate`, `tributario` e `narrativas`; as três primeiras
são dinheiro de verdade (a fixture dogfood não tem IRPF, imóvel locado nem PJ, então nunca
as emite). O viés é otimista, como o enunciado diz.

**A quarta não é raiz monetária.** A única folha que põe `narrativas` no denominador é
`narrativas.charts.wise_fiscal_flags.pontos_revisao`, que
[`tributario_narrator.py:233`](pipeline/domain/services/narrativas/tributario_narrator.py:233)
computa como `sum(1 for f in flags if f.get("needs_review"))` — **contagem**, lida como R$
pelo monetário-por-default. É a mesma classe já registrada em `golden_diff` para `n_*`,
`prob_*` e `score.*`. Corrigido no classificador (token `pontos`, mais `contagem`, que
`consumo_consciente_calculator.py:162` publica ao lado do irmão que é dinheiro). Raio medido
sobre schema E5 + payload de produção (1.008 nomes): 4 nomes mudam de classe, nenhum
numérico além de `pontos_revisao`; zero tocam `*_brl` ou `valor`.

Com isso o denominador honesto é **17**, e a cobertura publicada cai de **35,7% → 29,4%**.

## O universo: roster de origens, não o que uma fonte emite

A A27.l2 derivava o universo do payload da fixture — o que estava certo como *mecanismo* e
errado como *sujeito*. O universo agora é um **roster** (`dev/snapshots/lineage_coverage_baseline.json`):
cada raiz guarda **as origens em que foi observada**, e o número publicado é sobre o
universo inteiro.

| Origem | Raízes monetárias | Cobertas |
| --- | --- | --- |
| `fixture` (dogfood determinística) | 14 | 5 |
| `producao:40d1af2a` | 17 | 5 |
| **Roster publicado** | **17** | **5** → **29,4%** |

**Por que não o schema E5.** Medido e **rejeitado**: caminhando
`config/schemas/e5_analysis.schema.json` com o mesmo predicado, ele declara monetário em 14
raízes que **não são superconjunto da produção** — não declara `tributario`, que a produção
emite por `additionalProperties: true` — e declara `proventos_por_ativo`, que **nenhum** dos
40 artefatos E5 do DB emite. Seria teto inalcançável de novo, que é justamente o que a
A27.l2 evitou ao recusar as 38 raízes cruas.

**Limite declarado.** O roster cobre o que já foi **medido**. Raiz que só apareça num
workspace ainda não medido fica fora até alguém rodar o CLI sobre aquele artefato — e é
para isso que ele reprova por raiz-fora-do-roster. O DB local tem **1** workspace; a
estabilidade foi medida em 40 artefatos E5 (as 17 aparecem em 38–40 deles; `ratios` em 4,
porque é recente).

## Critério de aceite

- [x] **1. O universo é derivado do payload sob medição, não de constante.** O roster é
      construído por `Roster.observing(origem, measure_coverage(payload))` — fixture pelo
      rebaseline do pytest, produção pelo CLI. Nenhuma raiz é digitada à mão.
- [x] **2. Raiz monetária presente na produção e ausente do universo reprova.**
      `Roster.outside()` + `test_nenhuma_raiz_monetaria_fora_do_roster` (fixture, no CI) e
      `dev/lineage_coverage.py <payload> --origem <x>` (produção, exit 1). Falsificado:
      payload sintético com `raiz_nova_de_producao.total_brl` ⇒ CLI reprova com a raiz
      nomeada; run `7d860f0b` (outro run de produção) ⇒ exit 0, o roster generaliza.
- [x] **3. O número publicado declara denominador e origem.** `cobertura_publicada`
      no roster (`numerador`/`denominador`/`ratio_pct`/`origens`), asseverado contra a
      medida por `test_o_numero_publicado_declara_denominador_e_origem`, que também exige
      **≥2 origens** — roster de origem única é o defeito voltando.
- [x] **4. A queda é registrada como correção.** 35,7% → **29,4%**, propagada para
      [[ADR-281]], [[A27.l2]], o `_README` da sprint e o `PV13-12`.

## A prova de não-inércia

`test_o_denominador_publicado_nao_e_o_da_fixture` é o contrafactual que discrimina os dois
desenhos: ele exige que o roster conheça raiz além das da fixture **e** que a medida
só-fixture seja **mais alta** que a publicada — o viés, com sinal. Falsificado ponta-a-ponta:
reconstruído o roster single-origin do desenho anterior, ele reproduz exatamente
**5/14 = 35,7%** e **2 dos 6 testes reprovam** (este e o de origem/denominador declarados);
os outros 4 passam, porque o mecanismo da A27.l2 estava certo.

## Achado roteado, fora do escopo

`tributario` é emitido pelo E5 e **não é declarado** em `config/schemas/e5_analysis.schema.json`
— passa por `additionalProperties: true` com 15 folhas monetárias. Não é defeito de lineage
(é de contrato do E5), e por isso não foi consertado aqui.

## O que esta lane NÃO fecha

As raízes monetárias sem rastro continuam sem rastro — a lane conserta o **denominador**,
não a cobertura. A dívida contável passa de **9** (o que a A27.l2 publicava) para **12**:
`previdencia_pgbl`, `real_estate` e `tributario` sempre estiveram sem rastro, e agora
aparecem. Não são 13 porque `narrativas` nunca foi dívida — nunca publicou dinheiro.
