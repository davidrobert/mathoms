---
id: ADR-377
type: adr
title: "Janela interativa do relatório é conjunto fechado pré-computado — o cliente seleciona, não recomputa"
status: Decidido
phase: A40.l44
date: "2026-08-11"
relates_to:
  - "[[ADR-306]]"
  - "[[ADR-333]]"
  - "[[ADR-212]]"
  - "[[ADR-090]]"
  - "[[ADR-370]]"
supersedes: []
superseded_by: []
aliases: ["ADR 377", "janela interativa pré-computada", "cliente não agrega"]
tags:
  - type/adr
  - status/decidido
  - area/frontend
  - area/e5
  - area/pipeline
  - phase/a40
---

# ADR-377 — Janela interativa é conjunto fechado pré-computado

> **Decidida na [[A40.l44]]** — último código #1462 (`8d07c4fb`, 2026-08-14).
> O cliente seleciona `fluxo_caixa.janelas[period]`; não recomputa.

> Esta ADR **não decide base temporal nova**. A [[ADR-306]] já fixou a política de
> janela e rótulo no E5, e o gate dela vigia o **produtor**. O que esta ADR fecha é
> o buraco do outro lado: dois cards deixaram de consumir o artefato e passaram a
> **produzir** os próprios agregados, onde nenhum gate alcança.

## Contexto

Dois cards do relatório — `ReceitasFonteCard.tsx:43` e
`OrcamentoProspectivoCard.tsx:30` — abandonaram o view-model E5 e re-derivam
agregados monetários no cliente, via `usePeriodTransactions` → `GET /transactions`.

Um agregado monetário tem **três** insumos — substrato, predicado e denominador —
e o cliente re-deriva os três:

| Insumo | Onde o cliente o re-deriva | Quem é o dono no produtor |
|---|---|---|
| substrato | `listTransactions(..., page_size: 500)` (`usePeriodTransactions.ts:47`) | `fluxo_mensal_detalhado` (E4) → `fluxo_caixa_enricher.py` |
| predicado | `isIncomeCategory` (`periodUtils.ts:106`) | classificação do E4 + `compute_receita_por_natureza` |
| denominador | `getPeriodMonths` (`periodUtils.ts:83`) | `janela_meses` ([[ADR-306]] D2/D3) |

**Medido na revisão r4** ([[REPORT-REVIEWS-active]] §r4), cada defeito atingindo um
insumo diferente:

- **Janela ancorada em mês sem atividade** (RV4-01). A âncora sai da **última
  label da série mensal** (`S1PatrimonioSection.tsx:56-58` via
  `parseChartMonthLabel`); um lançamento com data de pagamento futura estica a
  série além do mês corrente, e a janela de média cai sobre meses sem movimento.
  Contrafactual medido: consertar só a âncora fecha 100% do gap.
- **Denominador constante desacoplado dos meses com dado** (RV4-06).
  `getPeriodMonths` devolve a constante do enum do toggle — 3, 6, 12 — não os
  meses documentados. É a [[ADR-306]] D3 violada **no consumidor**.
- **Taxonomia de receita divergente do produtor** (RV4-03). Categoria de crédito
  fora do whitelist do cliente sai da receita **e entra no balde de despesa**
  (`aggregateDespesasMediaMensal` usa `!isIncomeCategory`, `periodUtils.ts:132`):
  um recebimento vira teto de gasto.
- **Truncagem silenciosa de paginação** (RV4-07). `page_size: 500` sem paginação;
  a resposta **já traz** `total` e um `summary` uncapped calculado antes do slice,
  e o hook descarta ambos (`usePeriodTransactions.ts:50`).

### O que torna isto estrutural, e não quatro bugs

**Número nascido no cliente é inauditável por construção.** Ele não está no
artefato, logo passa **verde** por todo instrumento que este repo construiu para
não publicar número errado:

| Instrumento | Por que não alcança |
|---|---|
| `dev/explain_number.py` / `_lineage` | tracejam campos do E5; o campo não existe |
| golden de execução (`tests/test_e5_golden_execution.py`) | compara artefato contra artefato |
| snapshot do view-model (`backend/tests/test_report_view_model_snapshot.py`) | congela o que o backend serializa |
| ancorabilidade do parecer (`parecer_ancorabilidade.py`) | exige JSONPath em campo do E5 |
| gate de mensalização da [[ADR-306]] (`no-restricted-syntax`) | detém **acesso a campo**; aritmética sobre `fetch` não lê campo restrito |

O sinal decisivo da r4 é que **o parecer leu o número certo** (ancorou em campo
determinístico da janela de 12m) enquanto o card exibia o derivado quebrado: o
produtor está correto e a divergência nasce inteira na derivação do cliente.

## Decisão

**D1 — Conjunto fechado, pré-computado pelo produtor.** `fluxo_caixa.janelas` é um
mapa de chaves fixas — `3m`, `6m`, `12m`, `ytd` — emitido por
`fluxo_caixa_enricher.py`, a partir da mesma série (`meses_ordenados`) que já
alimenta a `janela_12m`. `3m`/`6m`/`12m` selecionam os últimos N meses
documentados com movimento, mesmo quando há gaps civis; `ytd` seleciona os meses
documentados do ano do último mês realizado. O breakdown de receita usa as
categorias canônicas de `receitas.dados`, restritas ao mesmo conjunto de meses —
nunca `origem`, que pode carregar detalhe livre/PII.

**D2 — Cada janela carrega o quociente, não os ingredientes:**

| Campo | Papel |
|---|---|
| `receita_total`, `despesa_total` | totais da janela |
| `receita_mensal_media`, `despesa_mensal_media` | **o quociente já calculado** |
| `janela`, `janela_meses` | vocabulário [[ADR-306]] D2 — rótulo impresso, não tooltip |
| `mes_inicio`, `mes_fim` | fronteira da janela, para o rodapé declarar o que mediu |
| `despesa_consumo_mensal_media`, `transferencia_patrimonial_mensal` | separação [[ADR-333]]: orçamento é consumo ex-aporte; saída bruta continua conservada |

Emitir numerador e denominador separados convidaria o cliente a dividir de novo —
que é exatamente a classe que esta ADR fecha.

Os dois cards também recebem **rows table-ready**, já ordenadas e com percentuais:
`tabela_receitas_por_fonte_mensal`,
`tabela_receita_por_natureza_mensal` e
`tabela_consumo_por_categoria_mensal`. A última inclui o Pareto acumulado. Totais,
médias por row e percentuais fecham em centavos/basis points por alocação
determinística do resíduo — nunca por bucket fictício "Ajuste". A tabela de
consumo exclui todas as `transfer_categories`; a identidade publicada é
`despesa_mensal_media = despesa_consumo_mensal_media +
transferencia_patrimonial_mensal`.

**D3 — O toggle seleciona bloco; não calcula.** O cliente **não faz aritmética
monetária nem tabular**: não soma, divide, filtra, ordena valores nem calcula
percentual/Pareto. Trocar de janela é trocar de chave no mapa.

### Invariante (o que o gate enforça)

> **Todo valor monetário renderizado no relatório existe, com esse valor e essa
> base declarada, num campo do artefato E5.**

## Alternativas rejeitadas

**(a) Endpoint dedicado que espelha a lógica do cliente.** Rejeitada com
**evidência empírica no próprio repo**: o clone já existe e **já divergiu
numericamente**. `backend/app/application/report/consumo_pontuais.py:23-42`
declara na docstring *"Replica `frontend/src/lib/periodUtils.ts::getPeriodDates`"*
e resolve `3m` como `today - timedelta(days=31 * 3)`, enquanto o original faz
`start.setMonth(end.getMonth() - 3)`. São duas janelas diferentes sob o **mesmo
rótulo**. Um segundo produtor da mesma regra não fecha a classe — replica-a numa
linguagem a mais.

**(b) Manter a agregação no cliente, com testes.** Rejeitada: teste de componente
prova que o cliente calcula o que o teste espera, não que o relatório publica o
que o artefato contém. O número segue **fora de todo instrumento de auditoria** —
a propriedade que motiva esta ADR permanece intacta.

## Consequências

- **Payload cresce poucos/dezenas de KB** — quatro blocos de escalares e três
  tabelas pequenas, preço aceito para seleção atômica e auditável.
- **Janela nova exige re-run e rebaseline de golden.** Adicionar `24m` deixa de
  ser mudança de front-end.
- **Range customizado (date picker livre) deixa de ser possível sem re-run.**
  Aceito: o toggle é enum fechado, e sempre foi — `VALID_PERIODS` já é
  `("3m", "6m", "12m", "ytd")` no backend.
- Em troca: **um produtor único**, número **auditável por lineage** ([[ADR-370]]
  conta o que o relatório publica; agora o que ele publica existe no artefato), e
  **PDF idêntico ao interativo** — hoje print e tela divergem quando um caminho
  renderiza o fallback estático e o outro o derivado (RV4-05).
- Conforma à fronteira da [[ADR-212]] (o relatório lê artefato, não o razão) e não
  introduz float novo: **remove** a aritmética que o JavaScript fazia em `number`
  sobre dinheiro ([[ADR-090]]).
- `receita_por_natureza` top-level continua full-period. A superfície com toggle
  consome a projeção **da janela selecionada**; usar o bloco top-level sob 3M/6M
  seria misturar bases.

## Gate

1. **Invariante de seção estendido à S1.** `janelaCanonica.contract.test.tsx` já
   varre todo `X/mês` renderizado por `S2FluxoCaixaSection` composta — é o gate da
   [[ADR-306]], e a varredura **já existe**. Estender à S1 é acrescentar a seção à
   composição varrida, não escrever instrumento novo.
2. **`no-restricted-imports` em `frontend/eslint.config.mjs`.** Regra **nova**, ao
   lado do `no-restricted-syntax` da [[ADR-306]] D1 (que restringe *campo*, não
   *import*): `src/components/report/**` não importa `usePeriodTransactions` nem
   `listTransactions`.
3. **Lineage dos campos renderizados.** Totais, médias e valores monetários das
   rows de cada janela têm entrada em `_lineage`, com `rule_ref` desta ADR; existir
   no JSON sem ser alcançável por `explain_number.py` não cumpre o invariante.

### O que este gate NÃO pega

Registrado porque gate cuja fronteira não está escrita vira garantia presumida:

- **Número errado que já está no payload.** O invariante prova *procedência*, não
  *correção*. Base errada no produtor passa verde.
- **Valor fora da forma `X/mês`.** A varredura casa a forma mensalizada; total,
  percentual e saldo não entram nela.
- **Fetch novo com outro nome.** O `no-restricted-imports` nomeia dois símbolos;
  um hook novo que chame `fetch` direto não é alcançado.
- **Superfície só-print.** Componente renderizado apenas sob `useIsPrint` não é
  exercitado pela composição varrida — o gate de pixel também não vê texto
  ([[ADR-370]] §Débito).

## Co-design

`senior-cto` + `data-engineer`, 2026-08-11, sobre a revisão r4
([[REPORT-REVIEWS-active]] §r4). Implementação em [[A40.l44]], seis PRs —
**ordem obrigatória**: o corte de futuro no produtor vem **antes** da correção da
taxonomia, senão o divisor parece validado e o gate fecha verde com o número
ainda errado (anti-fix registrado no RV4-03).

**Emenda de implementação 2026-08-14:** `senior-cto` + `data-engineer` +
`financial-planner` fecharam rows table-ready, natureza por janela, alocação de
resíduo, YTD histórico e orçamento ex-aporte. Sem esses campos, PR5/PR6 exigiriam
reagregação no cliente e contradiriam D3.
