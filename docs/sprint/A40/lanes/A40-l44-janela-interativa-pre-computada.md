---
id: A40.l44
type: lane
title: "Janela interativa pré-computada: o cliente para de ser um segundo motor de agregação"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1462
ship_date: "2026-08-14"
priority: P0
branch_slug: a40-l44-janela-interativa-pre-computada
adrs:
  - "[[ADR-377]]"
  - "[[ADR-306]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/frontend
  - area/pipeline
  - area/backend
---

# A40.l44 — `janela-interativa-pre-computada`

> **Aberta em 2026-08-11**, da revisão r4 registrada em
> [[REPORT-REVIEWS-active]] §r4 (report `7a7d7115` sobre run `ee124571`).
> Disparada por report de uso do dono: *o card de receita por fonte parecia
> subcontar*. **Procede.** Decisão de forma e escopo escrita na
> **[[ADR-377]] (`Decidido`)** — o gate de "ADR antes de PR P0" foi
> cumprido no #1397; o flip é deste closeout.

> **Fronteira com a [[A42.l8]] (auditoria 2026-08-14).** Esta lane é dona do
> corte de **futuro** (D3 emendado 2026-08-11) e do deferimento do **mês em
> curso**. A [[A42.l8]] **não reabre** nenhum dos dois. O que sobra lá é zero
> por falha de extração (PC11), união das pernas com zero-fill, e piso de
> publicação. A l8 declara `depends_on: [[A40.l44]]` por colisão em
> `fluxo_caixa_enricher.py`.

## Problema

Dois cards do relatório — `ReceitasFonteCard.tsx:43` e
`OrcamentoProspectivoCard.tsx:30` — abandonaram o view-model E5 e re-derivam
agregados monetários no cliente, via `usePeriodTransactions` → `GET /transactions`.

Um agregado tem **três** insumos e o cliente re-deriva os três: substrato
(`listTransactions`, `page_size: 500`), predicado (`isIncomeCategory`,
`periodUtils.ts:106`) e denominador (`getPeriodMonths`, `periodUtils.ts:83`).
Cada defeito medido na r4 atingiu um insumo diferente — âncora no futuro
(RV4-01), denominador constante (RV4-06), taxonomia divergente (RV4-03),
truncagem silenciosa (RV4-07).

**O que faz disto P0 não é a soma dos quatro:** número nascido no cliente é
**inauditável por construção**. Não está no artefato, logo `dev/explain_number.py`,
`_lineage`, o golden de execução, o snapshot do view-model e a verificação de
ancorabilidade do parecer passam **todos verdes** sobre ele. A r4 mediu o
contraste: *o parecer leu o número certo* — ancorou em campo determinístico da
janela de 12m — enquanto o card exibia o derivado quebrado.

## Achados cobertos

| Achado | Onde morre |
|---|---|
| RV4-01 âncora derivada da última label da série | PR1 (corte de futuro no produtor) |
| RV4-07 truncagem silenciosa de paginação | PR2 (guarda) e depois PR5 (a página some) |
| RV4-02 cliente é segundo motor de agregação | PR3 → PR5 |
| RV4-06 denominador é a constante do enum | PR4 (`janela_meses` vem do produtor) |
| RV4-03 taxonomia de receita divergente | PR5 (o predicado deixa de existir no cliente) |
| RV4-05 loading renderiza dataset alternativo | PR5 (seleção não tem estado assíncrono) |
| RV4-08 `receita_por_natureza` com zero consumidores | PR6 |

**Fora desta lane, declarado:** RV4-04 (três agregados de "receita mensal" na
mesma leitura) segue como copy e contrato de estados — dono
`product-designer`, lane própria. **RV4-10 foi absorvido pelo PR5** após
co-design: o card agora imprime `janela_meses · mes_inicio — mes_fim`, sem
transformar “3M” em promessa de três meses civis contíguos. RV4-09 (exposição
cambial) é outro card e não tem relação.

## Escopo — 6 PRs sequenciais

A ordem **não é negociável** nos dois primeiros passos: corrigir a taxonomia
antes da âncora faz o divisor parecer validado e o gate fechar verde com o número
ainda errado — **anti-fix registrado** no RV4-03.

### PR1 — corte de futuro no produtor — ✅ shipped

> **Entregue 2026-08-12** — #1396 (`f1cad2e4`). O aceite foi cumprido por outro
> caminho que o escrito aqui: o corte é **por transação** (`data > data_corte`),
> não por filtro de `meses_ordenados`, e o denominador não mudou nesta PR —
> `meses_com_dado` segue a convenção atual, de propósito, para o diff do golden
> ser atribuível **só ao corte**. O que saiu do realizado virou o bloco irmão
> `fluxo_caixa.provisionado`, e o snapshot de dogfood não moveu **nenhum valor
> monetário** (a fixture não tem transação futura). Invariantes I5/I6/I7 em
> tolerância zero; mutação que torna o corte no-op derruba 2 deles.

`fluxo_caixa_enricher.py`: `meses_ordenados` deixa de entrar cru no denominador.
Mês entra se tem **movimento** (receita ou despesa) e **não é posterior à data de
corte do run**. Implementa a [[ADR-306]] §Emenda 2026-08-11.

**Aceite:** fixture com lançamento de data futura ⇒ o mês futuro **não** aparece
em `janela_meses` · delta declarado e conferido por `dev/golden_diff.py`, sinal
esperado `↑` na média mensal (denominador cai) · **um delta, uma causa** — o corte
do mês em curso está deferido justamente para não misturar as duas causas.

### PR2 — guarda de truncagem — ✅ shipped

> **Entregue 2026-08-12** — #1398 (`38a7742d`). Hook devolve `isTruncated`; os
> dois cards suprimem a tabela e declaram a degradação (COPY_GUIDELINES §7.2).
> Sem paginação, como planejado. Mutação derruba 5 testes.

`usePeriodTransactions.ts:50` descarta `total` e `summary` que a resposta **já
traz** (o `summary` é calculado antes do slice, no servidor). Passa a ler `total`
e, quando `total > transactions.length`, o card **declara truncagem** em vez de
publicar média sobre conjunto cortado.

**Ponte declarada:** PR2 existe porque PR4/PR5 dependem de re-run e rebaseline, e
não se deixa número truncado publicando no intervalo. PR5 remove os dois
consumidores do hook; se `usePeriodTransactions` ficar órfão, **PR5 o deleta** —
órfão criado por esta lane morre nesta lane, não vai para a [[A40.l14]].

**Aceite:** teste com `total` maior que a página ⇒ estado de truncagem, não média.

### PR3 — ADR + emenda + lane (doc-only) — ✅ shipped

> **Entregue 2026-08-11** — #1397 (`3fafe676`). Saiu **antes** do PR1 no fim,
> não depois: CLAUDE.md §Política operacional exige ADR `Proposto` antes do PR
> de implementação, e a ordem escrita aqui originalmente estava errada.

[[ADR-377]] `Proposto`, emenda datada na [[ADR-306]] com `amended_at`, esta lane.
Vem **depois** de PR1/PR2 porque aqueles conformam a um `Decidido` existente
(correção), e **antes** de PR4/PR5 porque estes mudam contrato de artefato
(decisão). É o gate de `CLAUDE.md` §"ADR `Proposto` antes de PR P0/P1".

**Aceite:** gates de doc verdes (`validate_frontmatter`, `check_doc_filename_id`,
`check_doc_links`, `check_adr_anchors`, `check_adr_amendment_signal`,
`build_doc_index --inline`) · zero wikilink quebrado.

### PR4 — `janelas` no produtor — ✅ shipped

> **Entregue 2026-08-14** — #1449 (`da91a181`). As quatro janelas, três
> tabelas table-ready, conservação ao centavo, lineage, schema strict, teste
> real do `DBArtifactStore` e rebaseline isolado foram mergeados com CI verde.

`fluxo_caixa.janelas` = `3m` | `6m` | `12m` | `ytd`, cada uma com
`receita_total`, `despesa_total`, `receita_mensal_media`, `despesa_mensal_media`,
`despesa_consumo_mensal_media`, `transferencia_patrimonial_mensal`, `janela`,
`janela_meses`, `mes_inicio`, `mes_fim` e três tabelas prontas: receita por fonte,
receita por natureza e consumo por categoria ([[ADR-377]] D1/D2). Rows trazem
média, percentual e, no consumo, Pareto acumulado; o cliente não ordena nem
calcula. O orçamento exclui `transfer_categories` conforme [[ADR-333]].
Co-change obrigatório: `config/schemas/e5_analysis.schema.json`, DTO do
view-model, tipos do frontend e `_lineage` dos valores renderizados.

**Aceite:** as quatro janelas emitidas sobre a mesma série · `janela_meses` reflete
meses **com movimento**, não a constante do enum · schema declarado e validado no
hook pré-persistência do `DBArtifactStore` ([[ADR-212]]) · snapshot do view-model
rebaselinado com delta declarado · **o quociente é emitido pronto** — emitir
numerador e denominador convidaria o cliente a dividir de novo · rows fecham em
centavos e 100,00% sem balde de ajuste · YTD usa o ano do último movimento ·
`janelas["12m"]` reconcilia com `janela_12m` · `explain_number.py` alcança os
valores monetários table-ready.

### PR5 — o cliente seleciona e a agregação é deletada — ✅ shipped

> **Entregue 2026-08-14** — #1456 (`5194115a`). Os dois cards selecionam
> `janelas[period]`. `usePeriodTransactions` e `listTransactions` saíram do
> caminho do relatório (gate ESLint). Quatro janelas, tela e print.

Os dois cards leem `janelas[period]`. **Deletados** do caminho do relatório:
`aggregateReceitas`, `aggregateDespesasMediaMensal`, `getPeriodMonths`,
`isIncomeCategory` e o uso de `usePeriodTransactions`. Não `deprecated`, não
comentado — deletados; código morto que agrega dinheiro volta.

**Aceite (é aqui que o gate nasce):**

- Invariante de seção de `janelaCanonica.contract.test.tsx` **estendido à S1** — a
  varredura de `X/mês` já existe e já é o gate da [[ADR-306]].
- `no-restricted-imports` **novo** em `frontend/eslint.config.mjs` (regra
  adicional, ao lado do `no-restricted-syntax` da [[ADR-306]] D1): `src/components/report/**`
  não importa `usePeriodTransactions` nem `listTransactions`. **Prova do gate:**
  arquivo de fixture com o import ⇒ `eslint` sai ≠ 0.
- **Zero aritmética monetária no cliente** nos dois cards: nem `+`, nem `/`, nem
  filtro/ordenação por valor nem cálculo de percentual/Pareto.
- O orçamento usa `despesa_consumo_mensal_media`, rotulado como média histórica
  ex-transferências; `despesa_mensal_media` permanece a saída bruta conservada.
- Tela e PDF exibem o **mesmo** número nas quatro janelas do toggle — verificação
  renderizada, capturando **as quatro**, não só a default (§Débito de método da r4
  nº 3).

### PR6 — consumidor para `receita_por_natureza` — ✅ shipped

> **Entregue 2026-08-14** — #1462 (`8d07c4fb`). Co-design `product-designer`:
> um card, um toggle, um KPI. Faixa **Por tipo** lê
> `janelas[period].tabela_receita_por_natureza_mensal`. Identidade ao
> centavo nas quatro janelas. Título `Composição das Receitas`. Inventário
> ADR-370 e 6 baselines Linux (S1 desta lane; S2 herdado do PR5; APP-B wrap).

`fluxo_caixa.receita_por_natureza` tem contrato em `e5_analysis.schema.json`, é
consumido por `parecer_ancorabilidade.py` e pelo prompt do parecer, e tem **zero
consumidores** em `frontend/src` — a tela re-deriva pior a mesma resposta (RV4-08,
mesma família do RV3-02).

**Aceite:** o corte por natureza da S1 lê
`janelas[period].tabela_receita_por_natureza_mensal` (o bloco top-level é full e
não serve ao toggle) · a r4 já mediu que a natureza **fecha com o total de receita
ao centavo** — o teste ancora nessa identidade, não em valor literal.

**Forma (co-design product-designer, 2026-08-14):** um card, um toggle, um KPI.
A faixa **Por tipo** (as 4 naturezas da ADR-330) e a tabela **Fonte** ficam
sempre visíveis. Título `Composição das Receitas`. Sem card irmão — dois KPIs
do mesmo `receita_mensal_media` reabririam o RV4-04. Sem tabs: o PDF imprime
os dois recortes.

## Critério de aceite da lane

- **Invariante publicado e testado:** todo valor monetário renderizado existe, com
  esse valor e essa base declarada, num campo do E5 ([[ADR-377]] §Invariante).
- **A fronteira do gate está escrita** ([[ADR-377]] §"O que este gate NÃO pega"):
  número errado já no payload, valor fora da forma `X/mês`, fetch novo com outro
  nome, superfície só-print. Gate cuja fronteira não está escrita vira garantia
  presumida.
- **Dois deltas de golden declarados separadamente** — PR1 (corte de futuro) e PR4
  (`janelas`). Agregar os dois esconde que se movem por causas distintas.
- **Nenhum `skip`/`xfail`** para teste que passava sobre a agregação do cliente:
  o que especificava a derivação deletada é **deletado** ([[ADR-375]] D7 é o
  precedente no vault).

## Não-objetivos com rota declarada

- **`consumo_pontuais.py:23-42`** — o clone Python de `getPeriodDates` que **já
  divergiu** (`timedelta(days=31 * 3)` vs `setMonth(-3)`) é a **evidência** que
  derruba a alternativa (a) da [[ADR-377]]; consertá-lo é da [[A40.l15]], dona da
  base do card Consumo Consciente. Esta lane não o toca.
- **Exclusão do mês em curso** — deferida em [[ADR-306]] §Deferimento datado
  (dono `senior-cto`, lane própria): é flip de denominador e exige diff
  atribuível separado do corte de futuro do PR1.
- **Range customizado (date picker livre)** — incompatível com conjunto fechado
  por decisão, não por omissão ([[ADR-377]] §Consequências).

## Colisão declarada

- `fluxo_caixa_enricher.py` é tocado também pela [[A40.l15]] (`planned`, P2), que
  mexe na fronteira D1/D6 da [[ADR-306]]. Sem colisão de conteúdo — a l15 muda
  **qual base** o card de pontuais declara; esta lane muda **quem calcula** a
  janela. Quem mergear depois rebaseia.
- `S1PatrimonioSection.tsx` não tem outra lane viva; a âncora que ele deriva
  (`:56-58`) deixa de existir no PR5.

## Entrega

`shipped` 2026-08-14. `ship_pr: 1462` nomeia o último código; os outros cinco
PRs estão no corpo.

| PR | Merge | SHA |
|---|---|---|
| PR3 ADR + lane | #1397 | `3fafe676` |
| PR1 corte de futuro | #1396 | `f1cad2e4` |
| PR2 guarda de truncagem | #1398 | `38a7742d` |
| PR4 `janelas` | #1449 | `da91a181` |
| PR5 cliente seleciona | #1456 | `5194115a` |
| PR6 faixa Por tipo | #1462 | `8d07c4fb` |

**Medido no closeout:** `rg usePeriodTransactions frontend/src/components/report`
→ 0. Consumidor vivo da tabela de natureza: `ReceitasFonteCard` /
`ReceitasNaturezaStrip`. Bloco top-level `receita_por_natureza` não é lido pela
tela.

**Continua aberto, com dono:** residual de copy do RV4-04 (rótulo que reconcilie
bases se "receita mensal" ainda aparecer com outra janela) → `product-designer`,
**lane a abrir** — não aponta para esta. Exclusão do mês em curso → [[ADR-306]]
§Deferimento, `senior-cto` (condição de retomada = l44 fechada, agora
satisfeita). Clone Python de `getPeriodDates` → [[A40.l15]].
