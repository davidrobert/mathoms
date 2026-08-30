---
id: A40.l94
type: lane
title: "Folga mensal reclassifica gasto pontual realizado como sobra recuperável"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1828
ship_date: "2026-08-29"
priority: P0
branch_slug: a40-l94-folga-reclassifica-gasto-realizado
owner: financial-planner
depends_on: []
adrs:
  - "[[ADR-422]]"
  - "[[ADR-306]]"
  - "[[ADR-333]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l94 — `folga-reclassifica-gasto-realizado`

> **Origem:** `RR6-01` da rodada unificada **U2** ([[REPORT-REVIEWS-active]] §r6,
> merge `47970706`). Medido pelo braço cego e confirmado ao centavo pelo loop principal.

## O defeito

A identidade fecha ao centavo (resíduo de arredondamento):

```
folga_mensal × 12  ==  poupança 12m + gastos pontuais 12m
```

Os dois percentuais de "quanto sobra" dividem o **mesmo** denominador
(`fluxo_caixa.janela_12m.receita_recorrente` == `equilibrio_cerbasi.componentes.base`)
e divergem em **19,4 pp** — e a diferença é exatamente `total_pontuais_janela`. Gasto
pontual **realizado** está sendo reclassificado como folga recuperável. A soma fecha dos
dois lados, então nenhuma conservação vê.

**Alcança o usuário:** quem dimensiona aporte pela folga dimensiona **27% acima** do que
a poupança medida sustenta. E a maior das duas sobras é a que **prescreve**.

Irmão na mesma superfície: `equivalente_meses_aporte` mede o estoque de pontuais contra o
aporte **declarado**, não contra a poupança realizada ⇒ fator de inflação **4,9×**.

## §Sequência — leia antes de escolher o fix

O `LC6-05` ([[LEDGER-CERTIFY-active]] §r6) mediu que a base de `total_pontuais`
**inclui aporte e transferência interna**. Consertar a folga sem consertar a base move o
número para **outro valor errado**. O separador de transferência patrimonial **existe** e
é aplicado à janela 12m — não é aplicado à janela que produz `total_pontuais`. Uma
aplicação, dois pontos.

**Não encodei isto como `depends_on`** porque a dependência é de **ordem do fix**, não de
início do trabalho: medir e desenhar pode começar já. Quem executar decide a ordem e a
declara no PR.

## Critério de aceite

- Invariante `|folga_mensal − taxa_poupança × receita_recorrente| ≤ ε` implementado como
  gate, **com prova de que ele reprova com o defeito presente** — gate que nasce verde não
  conta.
- Uma só definição de "quanto sobra" na superfície, ou duas com rótulo de base explícito.
- `equivalente_meses_aporte` declara contra qual grandeza mede.

## Já registrado — marque `MEDIÇÃO-DE-CONHECIDO`

`PV9-13` (a divergência de ~19pp já fora vista no U1; o novo é a identidade exata) ·
`PV9-11` (separador de transferência inerte) · `PV9-12` (moeda como despesa e ativo).

## Re-medição

Cru com valores (off-git): `storage/<ws>/reviews/U2-2026-08-29/SINTESE.md` §"A identidade
sum-preserving que alcançou o usuário".

## Execução (2026-08-29)

### A ordem escolhida, e por que a trava se dissolveu em vez de ser respeitada

A §Sequência supõe que consertar a folga sem a base move o número para outro
valor errado. Isso é verdade **sob o fix que a lane imaginava** (manter a folga
como "sobra recuperável" e limpar o que volta). O co-design com `financial-planner`
recusou esse desenho: manter dois "quanto sobra" com rótulo resolve ambiguidade de
**escopo**, não dois **vereditos** sobre o mesmo denominador.

Sob a decisão adotada ([[ADR-422]] D1), a folga **deixa de ler pontuais** — e o
acoplamento desaparece. Cada delta fica atribuível a uma causa, que é o que a
§Débito de método da sprint pede. A base é lane própria.

**Correção de premissa, medida:** no dogfood o `aporte_investimento` é R$ 190.000
de `total_pontuais` (20,6%) mas está em **2025-07, fora da janela** —
`janela_12m.despesas_por_categoria.aporte_investimento` é `0,0`. Neste corpus a
contaminação por aporte atinge `total_pontuais`, `equivalente_meses_aporte`, a
prosa e a âncora de evidência do parecer, e **não** move `folga_mensal`. A trava é
estrutural (na fixture nova, com aporte dentro da janela, ela morde), não deste run.

### Prova de que o gate reprova com o defeito presente

Nenhuma fixture do repo tinha **um único** gasto pontual ≥ R$ 2.000, e as duas que
o invariante rodava têm `n_meses == 1`. Medido antes do fix:

| payload | folga | poupança | delta | invariante |
| --- | --- | --- | --- | --- |
| `minimal` | 70,00 | 70,00 | 0,00 | passa (**vácuo**) |
| `dogfood` (golden) | 1.500,00 | 1.500,00 | 0,00 | passa (**vácuo**) |
| `pontuais-com-aporte` (**nova**) | 15.000,00 | 14.250,00 | **750,00** | **REPROVA** |

Daí `test_fixture_discrimina_folga` vir **antes** dos invariantes e vigiar a própria
fixture: trocá-la devolveria o gate à vacuidade em silêncio. Era o `RR6-07`.

O snapshot `dogfood_view_model.json` **não testemunha** este conserto pela mesma
razão — `folga_mensal` não se move nele. Quem testemunha é a fixture nova.

### Entregue

- `folga_mensal = receita_recorrente_mensal − despesa_consumo_mensal` ([[ADR-333]]).
- `teto_sugerido` **removido** do contrato (payload, schema, codegen, card, parecer).
- `equivalente_meses_aporte` → `equivalente_meses_poupanca`, numerador e denominador
  na mesma janela: 46,1 → 4,1 no dogfood.
- Prosa do E5 declara as duas janelas.
- Cópia **morta** de `analyze_consumo_consciente` (`analyze_finances.py`) deletada —
  sem chamador e com a fórmula antiga **sem** filtro de janela.
- `manifest_version` do parecer 2.7.0 → 2.8.0 (cobra a frota: a folga mudou de VALOR
  sem mudar de nome, e o cache tem TTL de 7 dias).

### Deferido — §Deferimento datado 2026-08-29 · **Dono: [[A40.l97]]** (aberta 2026-08-30)

Os três itens abaixo foram para a [[A40.l97]] (`base-dos-pontuais-tres-produtores`), com
`LC6-06`/`LC6-07` roteados junto por serem da mesma família. **Condição de retomada:** nenhuma —
a lane está `open` e é pegável.

> **Correção 2026-08-30.** Este bloco dizia "vai para a lane da base dos pontuais (`LC6-05`)" e
> essa lane **não existia**: `LC6-05` é código de achado, não wikilink, então o destino era
> fantasma e invisível ao `check_doc_links`. O `check_closure.py` também não pegou — qualquer
> `[[ADR-…]]` citado como contexto absolve o bloco inteiro, e o `[[ADR-333]]` do item 1 absolveu
> (registrado como follow-up de gate, não consertado aqui).

1. **Aplicar `transfer_categories` ([[ADR-333]]) ao `_collect_candidates`.** Hoje há **três**
   definições disjuntas de "gasto pontual" em produção — a do enricher, a da **lista** do card
   (`consumo_pontuais.py`, que aplica `InternalTransferDetector`) e a do **KPI** (que não aplica
   nenhuma das duas). Lista e KPI do mesmo card filtram coisas diferentes.
2. **Regra de domínio decidida no co-design, ainda não implementada:** `nao_identificado`
   não entra em número que **prescreve** — fica no inventário, com o residual impresso
   (contagem + valor). É o que contém a contaminação sem depender do detector.
3. **`pontual_mensal`** (o ritmo do pontual) entra **junto com a base limpa**: publicá-lo hoje
   imprimiria um número cuja base é 57,5% movimentação patrimonial no dogfood; emiti-lo sem
   leitor criaria a classe emissor-sem-leitor que a [[A40.l88]] gateia. **Nome canônico é
   `pontual_mensal`**, da [[A40.l15]], que precede o `provisao_pontual_mensal` que o co-design
   desta lane propôs — um campo, um nome.

### Achado lateral, registrado

`dev/check_float_money.py` tem falso-positivo de forma conhecida no scan **diff-based**:
`FIELD_FLOAT` casa parâmetro de função quebrado em várias linhas (`total_pontuais: float,`),
que é exatamente a forma que o scan irmão de `pipeline/llm/schemas/**` documenta filtrar
(`_SCHEMA_FIELD_FLOAT` exige `=` ou fim de linha). Declarado na allowlist com o WHY em vez
de estreitar o regex: mudança de gate merece revisão própria, e não cabe no PR que a
descobriu.

## Fecho (2026-08-30)

Mergeada em `main` como `05561dc0` ([#1828](https://github.com/davidrobert/mathoms/pull/1828)),
10/10 checks obrigatórios verdes. A [[ADR-422]] passou a `Decidido` no closeout.

**Pendência roteada — dono: [[A40.l46]]** (lane `open`, já dona da classe "baseline de print
não provada"): a baseline de pixel do PDF ficou stale (19.503px contra tolerância de 500)
porque o card perdeu um KPI. Não bloqueia — `print.@critical` é
exclusão nominal do gate de merge, e `print-chrome`/`print-text`, que medem **conteúdo**,
seguem dentro e passam. Regeneração é `workflow_dispatch` com `run_print=true` +
`UPDATE_PRINT_BASELINE=1`, disparo do dono. Não rebaselinado local por decisão registrada:
a baseline nasce em runner Linux/UTC e o macOS diverge por fuso e antialiasing.

**Auditoria de closeout (2026-08-30).** 56 agentes, 49 achados, 45 confirmados: a vault
afirmava o mundo pré-merge em 22 sítios. Consertados nesta rodada. Dois defeitos eram desta
lane: o §Deferimento apontava para lane inexistente (acima) e três citações a `ADR-420` ficaram
em `frontend/tests/components/report/janelaCanonica.contract.test.tsx` — a verificação da
renumeração varreu `frontend/src` e **não** `frontend/tests`, onde o teste de frontend mora.
