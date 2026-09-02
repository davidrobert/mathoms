---
id: A42.l24
type: lane
title: "Três checks meus publicam verde sobre população em que a falha é impossível por construção — e um deles exclui justamente o stage sob suspeita"
sprint: A42
status: shipped
ship_pr: 1958
ship_date: "2026-09-01"
priority: P1
branch_slug: a42-l24-check-cujo-denominador-torna-a-falha-impossivel
owner: senior-cto
depends_on: []
adrs: ["[[ADR-416]]", "[[ADR-341]]", "[[ADR-296]]"]
tags: [type/lane, sprint/a42, status/shipped, priority/p1, area/dados]
---

# A42.l24 — `check-cujo-denominador-torna-a-falha-impossivel`

> **Origem:** `LC9-04` + `LC9-05` (§r9) + `PV13-10` (§r13) da rodada unificada **U5**
> ([[LEDGER-CERTIFY-active]] §r9). **Achado do instrumento contra si mesmo**, na mesma
> classe que a [[A42.l21]] e o `LC8-01` da rodada anterior.

## Os três

1. **X4 (ancoragem do parecer) é falso-verde.** Dos 10 literais monetários do parecer,
   **9** vivem num campo que o **backend** preenche copiando `path → valor` do **mesmo
   payload** que o check relê. **Órfão é impossível por construção.** A superfície
   monetária **autoral do modelo** é **n=1**. Publiquei `FECHA ✅ n=10/10` sobre um
   denominador em que 9 de 10 não podiam falhar.
2. **X5 (proveniência de execução) examina 17 de 18 stages** — `n_esperado=17` — e o
   excluído é o stage em `needs_review` que **constrói o payload que carrega a regressão
   desta rodada**. O check consertado para *"poder sair verde"* sai verde **ignorando
   exatamente o stage sob suspeita**.
3. **Teto de iterações de ferramenta é medido sobre população distinta do emissor:** o run
   registra **19** contra teto **6** — estourado **3,2×** sem alarme — porque as 19 são
   carimbos do backend e **zero** foram iniciadas pelo modelo. Emissor e teto contam coisas
   diferentes.

## O eixo, e por que a lane é de saúde-harness

O anti-vácuo do runbook exige `n_comparado` **e** `n_esperado`, e os três **publicam os
dois** — o guard funciona. O que ele não pega é **denominador tautológico**: população
grande, verdadeira, e incapaz de exibir a falha. `n_esperado` alto **parece** cobertura.

## Critério de aceite

1. Cada check declara, junto do par `n_comparado`/`n_esperado`, **quantos elementos da
   população poderiam exibir a falha**. Zero ⇒ `INAPLICÁVEL`, nunca ✅.
2. X4 mede **só** prosa autoral; com `n=1` o veredito é `INAPLICÁVEL`, e isso é resultado.
3. X5 fecha sobre **todos** os stages logados, ou nomeia a exclusão **no veredito** — não
   no denominador.
4. O teto de iterações compara a população que o emissor conta.
5. Controle positivo por check: mutação que **deve** reprovar, e reprova.

---

## Entregue (2026-09-01)

**O eixo virou guarda executável.** `veredito()` passa a exigir um **terceiro
denominador** — `n_falsificavel`, *quantos elementos da população podiam
reprovar* — **keyword-only e obrigatório**: parâmetro opcional é exatamente
como esta guarda ficaria inerte. Zero ⇒ `INAPLICÁVEL`, jamais ✅; e a linha
publica a fração dele sobre o examinado, porque `FECHA` sobre 10% não é o mesmo
fato que `FECHA` sobre 100%. A regra está inscrita no runbook
([[runbook-unified-certify-review]] §checklist + §10 emenda 2026-09-01).

### Os três, medidos no run `40d1af2a` do `U5`

| check | antes | depois |
|---|---|---|
| **X4** | `FECHA ✅ n=10/10` | `FECHA ✅ n_comparado=10 n_esperado=10 **n_falsificavel=1 (10%)**` |
| **X5** | `FECHA ✅ 17/17` (de 18) | `FECHA ✅ **18/18** n_falsificavel=14 (78%) · fora do predicado por status: `analyze_finances` (needs_review)` |
| **X7** (novo) | não existia; o `19 > 6` era lido à mão | `INAPLICÁVEL ⛔ n_falsificavel=0` — o teto governa população vazia |

**X4** separa carimbado de autoral pelo resolvedor do **próprio estampador**
(`PlannerDrillDown` sobre o E5 do run) e **por ocorrência**, nunca por valor:
medido, o único literal autoral (`riscos[8].evidencia`) repete o **mesmo número**
de uma âncora carimbada, e subtrair por valor apagaria justamente a cópia
autoral. Instrumento cego (manifesto/drill ilegíveis) sai `INAPLICÁVEL` — chutar
`autoral` publicaria `DIVERGE` fabricado.

**X5** deriva `n_esperado` de **todos os stages logados**, não de
`len(completos)`. A exclusão é legítima e continua existindo; o que muda é onde
ela aparece — **no veredito, nomeada**, nunca no denominador.

**X7** compara o teto com a população que o emissor conta, por **assinatura**:
`LLMService.call` não aceita `tools` ⇒ round-trip iniciado pelo modelo é
estruturalmente 0. O `maximum: 6` de `_meta.tool_iterations` em
`config/schemas/parecer_planejador.schema.json` anotava o campo do **emissor** e
foi corrigido para conformar a semântica que a [[ADR-341]] já decidira (OBS-1 ·
A37.l1: *"telemetria, NÃO o cap"*).

## O que a medição refutou

⚠️ **O §Critério de aceite 2 pedia `INAPLICÁVEL` com `n=1`; isso não procede.**
O literal autoral vive em `riscos[].evidencia`, campo que **nada sobrescreve** —
ele *pode* reprovar, e não reprovou. Marcá-lo `INAPLICÁVEL` apagaria medição
verdadeira e criaria a tautologia inversa: excluir do denominador uma população
que **pode** falhar. Um corte `n == 1 ⇒ INAPLICÁVEL` também é arbitrário — `n=2`
passaria. O que protege o leitor é publicar os **10%**, não trocar o rótulo.
Vale o mesmo para a atribuição de path do enunciado: os 9 carimbados não estão
todos em `riscos` — são 6 em `riscos`, 2 em `sugestoes_estrategicas`, 1 em
`sugestoes_taticas`. A contagem 9/1 procede; a localização era mais estreita que
o fato.

⚠️ **A origem citava `LC9-10`; o terceiro achado é `PV13-10`** ([[PIPELINE-REVIEWS-active]]
§r13). `LC9-10` é a sonda de imóveis, dona [[A40.l113]]. Corrigido no cabeçalho.

## Aberto, com dono

- **`_meta.tool_iterations` não é validado**: `SCHEMA_BY_STAGE` não tem entrada
  para `review_finances_holistic` (`RV4-23`), então a correção do schema é hoje
  declaração dormente. Gatear é da [[A42.l6]], que já registra a ordem
  obrigatória (*corrigir o schema antes de gatear*) — esta lane paga a primeira
  metade dela.
- **`valor_renderizado` não é `SkipJsonSchema`**, ao contrário de
  `Metrica.nome/valor_atual/target` ([[ADR-399]] D1). O comentário do campo diz
  *"escrito pelo finalize, não pelo LLM"* e **nada o enforça**: âncora cujo path
  não resolve publica o número do **modelo**. Neste run isso é vazio (9 de 9
  resolvem) e o X4 já o trata como autoral quando ocorrer — mas fechar a porta é
  do produtor. ~~Dono: [[A40.l117]]~~ · ✅ **CUMPRIDO** no fecho da A40.l117
  ([#1996](https://github.com/davidrobert/mathoms/pull/1996) `1583cf97`, [[ADR-438]]):
  `Ancora.valor_renderizado` **e** `.label` passaram a `SkipJsonSchema`, pelo mesmo
  argumento da [[ADR-399]] D1 — campo escrito pela máquina sai do contrato enviado a ela.
  O comentário *"escrito pelo finalize"* deixou de ser promessa e virou contrato.
- **Buraco de cobertura declarado no X4**: só `R$` explícito. Prosa monetária por
  extenso (*"350 mil"*) fica fora e **não** está contada.

## Closeout (2026-09-02) — a entrega quebrou três checks e o closeout os achou

**`CLOSE-BLOCK`, meu.** Tornar `n_falsificavel` **obrigatório** foi a decisão certa —
e eu atualizei só os três call-sites que estava consertando. Os outros três vivem em
`dev/_unified_xchecks/razao.py` e ficaram sem o argumento: **X2, X3 e X3b morriam com
`TypeError` na linha do veredito**, depois de imprimir a tabela inteira. Em `main`, do
merge do [#1958](https://github.com/davidrobert/mathoms/pull/1958) até o conserto, os três
checks do **razão** — o núcleo da rodada — estavam quebrados.

**Por que nada pegou.** `tests/test_dev_unified_xchecks.py` exercita `base`, `execucao` e
`ancoragem`; **nunca** `razao`, porque X2/X3/X3b precisam de DB e de um run real. `ruff`
não confere argumento de call-site. O CI ficou verde sobre um pacote com metade dos
consumidores quebrada — a mesma classe de *verde e cego* que esta lane existe para atacar,
desta vez cometida pelo conserto dela.

**Conserto, com o controle que faltava.** Os três declaram `n_falsificavel` na unidade do
próprio veredito, e um **teste estático (AST)** varre todo call-site de `veredito(` em
`dev/_unified_xchecks/` e reprova o que omitir o argumento. Ele é o controle que a
assinatura sozinha não dá: keyword-only obriga o **autor** a responder; o AST obriga o
**repo** a não esquecer nenhum sítio que não tem teste de execução. Falsificador junto —
sobre a forma que estava em `main`, o teste acusa `razao.py:248`.

**Segundo defeito, achado ao rodar de verdade.** O X2 publicou
`n_falsificavel=2289 (76300% do examinado)`: passei célula contra um denominador em
**balde**. `lidos` já conta só balde com ≥1 célula — que é a condição de o balde poder
exibir a falha —, e a profundidade continua em `celulas=` na nota. O guard passa a recusar
razão impossível (`> n_comparado` sai `⚠️ UNIDADE DIVERGE`, nunca como porcentagem):
número absurdo é lido como ruído e some.

**Os seis checks rodados fim-a-fim** contra o run `40d1af2a` do `U5`, que é o que prova
que o conserto não é de papel:

| | veredito |
|---|---|
| X2 | `FECHA ✅ 3/3 · n_falsificavel=3 (100%)` · celulas=2289, 0 divergentes |
| X3 | `FECHA ✅ 1540/1540 · n_falsificavel=1540 (100%)` |
| X3b | `FECHA ✅ 112/112 · n_falsificavel=112 (100%)` · delta=0 |
| X4 | `FECHA ✅ 10/10 · n_falsificavel=1 (10%)` |
| X5 | `FECHA ✅ 18/18 · n_falsificavel=14 (78%)` |
| X7 | `INAPLICAVEL ⛔ 19/19 · n_falsificavel=0` |

**As duas rotas do §Aberto continuam válidas, re-medidas** (não relidas): `SCHEMA_BY_STAGE`
tem **25** entradas e **nenhuma** casa `review_finances_holistic` ⇒ a correção do schema
segue dormente, dona [[A42.l6]] (`planned`); e `Ancora.valor_renderizado` continua
`Optional[str]` **sem** `SkipJsonSchema`, dona [[A40.l117]] (`open`).

**Corroboração independente:** a [[A40.l117]] emendou a [[ADR-203]] em 2026-09-01 medindo
o mesmo fato do `PV13-10` — `LLMService.call` sem `tools`, as 19 entradas todas pós-LLM —
e cita esta lane. Duas medições, mesma conclusão.
