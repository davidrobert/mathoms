---
id: A40.l114
type: lane
title: "O ano de referência é saída crua do LLM, e o total de dívida vira zero quando esse ano não existe em documento nenhum"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l114-ano-de-referencia-sem-documento-atras
owner: data-engineer
depends_on: []
adrs: ["[[ADR-301]]", "[[ADR-401]]", "[[ADR-431]]"]
tags: [type/lane, sprint/a40, status/open, priority/p0, area/pipeline, area/financial-planning]
---

# A40.l114 — `ano-de-referencia-sem-documento-atras`

> **Origem:** `RR9-02` (Cadeia B) da rodada unificada **U5**
> ([[REPORT-REVIEWS-active]] §r9). **CONFIRMADO** por medição A/B entre dois runs sobre
> corpus idêntico, com o mecanismo lido no produtor.

## O que está publicado

`endividamento.total_dividas` sai **zero** enquanto `endividamento.dividas` lista
**4 financiamentos imobiliários** com saldo. `percentual_patrimonio` sai **zero** junto, e
`score.componentes[taxa_endividamento]` sai `valor=0,0 · peso=1,5 (**18,8%** do score) ·
**nota=10,0** · status="emitted"`. A superfície publica *"Endividamento Mínimo/Nulo"* como
**Ponto Forte** em 2 inventários. `patrimonio.liquido` fica **idêntico ao bruto**.

Nas três rodadas unificadas anteriores o total saía correto. **Três totais de dívida
coexistem nos artefatos deste run**: o publicado (zero), o da lista de itens, e o de
`patrimonio_por_ano.total_dividas` — três valores distintos para a mesma pergunta.

## A cadeia, elo a elo

1. `pipeline/stages/extract_baseline.py:96` — `"ano_referencia": output.reference_year`,
   com `_meta.source: "E1.5-llm"`. **É saída crua do LLM, e nada a confronta com os anos
   que os documentos têm.** O valor derivado do documento é computável **no mesmo arquivo,
   linha 173** (`max(years) if years else 0`).
2. O LLM carimbou o **ano seguinte** ao da declaração mais recente do corpus. Nenhum
   documento é desse ano.
3. `scripts/consolidate_baseline.py` **re-rotula** `patrimonio_por_ano` para o ano novo com
   o conteúdo **byte-idêntico** ao do run anterior (`total_bens` e `total_dividas` iguais).
   O ano mudou; os números, não. Cada dívida mantém o `ano_referencia` **correto** e
   `saldo_31_12` com as chaves dos anos que existem.
4. `resolve_value_year` propaga o ano carimbado.
5. `pipeline/domain/services/patrimonio_resolvers.py:561` `_split_dividas` faz
   `safe_float(saldo.get(ano_ref, 0))` — **sem fallback** ⇒ zero nas quatro.

## O irmão do mesmo campo TEM fallback — e é por isso que o relatório se contradiz

`_resolve_saldo` (`pipeline/domain/services/endividamento_analyzer.py:140`, [[ADR-401]])
lê o mesmo `saldo_31_12` e **cai para `anos[-1]`** quando `ano_ref` falta. Daí a lista de
itens continuar somando o valor certo **na mesma página** em que o total sai zero: **dois
leitores do mesmo campo discordam sobre o que fazer quando o ano não existe**, e cada um
alimenta uma superfície diferente.

## Correção de atribuição herdada de comentário

O comentário em `endividamento_analyzer.py:138` nomeia `patrimonio_resolvers._total_dividas_for`
como *"defeito vivo"*. Ele **é** defeito real — `safe_float` sobre o objeto por ano
([[ADR-301]]) devolve zero — mas está **dormente**: este corpus segue
`build_members_from_consolidated`, que usa `_split_dividas`. A prova de que
`_total_dividas_for` não é a causa **deste** zero: `saldo_31_12` já era objeto por ano no
run anterior, quando o número saiu **certo**. Quem for consertar deve tratar os dois — o
que dispara e o que espera.

## Por que é P0, e por que a ADR da própria sprint dá o remédio

A [[ADR-431]] decidiu que **publicar zero onde o valor não foi apurado é afirmação sobre o
patrimônio da pessoa** e deve virar `null` + declarado. O total de dívida faz exatamente o
proibido, na direção **inversa** — subdeclara **passivo** em vez de ativo — e ainda credita
**nota máxima** por isso. Amortizar-vs-investir é a decisão que o relatório existe para
informar, e ela sai invertida.

## Critério de aceite

1. `ano_referencia` do LLM é **reconciliado** contra os anos presentes nos documentos: se
   excede o máximo observado, o valor observado prevalece e a divergência é declarada
   (`review_reason`), nunca silenciosa.
2. `_split_dividas` **não publica zero** por ano ausente: ou cai para o ano mais recente
   disponível como o irmão `_resolve_saldo`, ou declara `não apurado` no espírito da
   [[ADR-431]]. As duas rotas exigem decisão do `financial-planner` — subdeclarar passivo
   e omitir passivo têm consequências diferentes na prescrição.
3. `score.componentes[taxa_endividamento]` **não emite nota** sobre total suprimido:
   `status` reflete a supressão, e o peso sai do denominador.
4. Tripwire: `total_dividas == 0` com `len(dividas) > 0` é **contradição interna** e reprova
   antes de publicar. Custa uma linha e pega a classe inteira.
5. Regressão: fixture com `ano_ref` fora das chaves de `saldo_31_12`; asserção de que o
   total publicado **não** é zero silencioso e que os três produtores concordam.
