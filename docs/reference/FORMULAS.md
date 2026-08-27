# Glossário de fórmulas

Referência canônica **número ↔ regra**. Detalhes de implementação vivem
em `pipeline/domain/services/` e nos scripts do pipeline. Quando uma
fórmula ficar ambígua entre este doc, `methodology.md` e `scoring.json`,
**`scoring.json` vence em parametrização** e este doc vence em
**definição matemática**.

## Patrimônio

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| Patrimônio bruto | `bruto = cat_1 + cat_2 + cat_3 + cat_4 + cat_5 + cat_6 + cat_7` (spec canônica das 7 categorias no docstring de `PatrimonioCalculator`, rules-as-code · ADR-143) | E5 JSON · `patrimonio.bruto` |
| Patrimônio líquido | `liquido = bruto − dividas` | E5 JSON · `patrimonio.liquido` |
| Patrimônio investível (financeiro) | `investivel_financeiro = cat_3 + cat_4 + cat_5 + cat_6` — apenas ativos financeiros líquidos. **Métrica Perini/AUVP correta para `progresso_if`.** | E5 JSON · `patrimonio.investivel_financeiro` |
| Patrimônio investível (total) | `investivel_total = bruto − cat_1 − cat_7` (exclui residência principal e veículos). Métrica retro-compat. | E5 JSON · `patrimonio.investivel_total` |
| Patrimônio investível (efetivo) | `investivel_efetivo = investivel_financeiro + (cat_2 if workspace.imoveis_no_if else 0)` | E5 JSON · `patrimonio.investivel_efetivo` |
| Autonomia financeira (meses) — [[ADR-335]] | `autonomia_financeira_meses = investivel_financeiro ÷ despesa_mensal_media` (janela 12m). Runway de liquidez — usa **`investivel_financeiro`** (sem cat_2 imóvel ilíquido), portanto **toggle-independente**. Distinto da reserva de emergência (§Reserva, denominador `custo_essencial`) e do `progresso_if` (numerador `investivel_efetivo`). Ex-`cobertura_despesas_meses`; alias deprecated por 1 ciclo. | E5 JSON · `ratios.autonomia_financeira_meses` |

## Independência Financeira

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| IF meta bruta | `if_meta_bruta = renda_alvo_mensal × 12 / (trs_pct/100)`. Didática — patrimônio total que sustenta o alvo, sem desconto. Produzida por `compute_if_derived`. | E5 JSON · `goals.if_meta_bruta` · Goal `derived.if_meta_brl` |
| Renda passiva fora do investível — [[ADR-418]] | `renda_passiva_fora_do_investivel_mensal = alugueis ÷ 12 se NÃO workspace.imoveis_no_if senão 0`. Renda de ativo que o numerador **não conta**. | E5 JSON · `goals.renda_passiva_fora_do_investivel_mensal_brl` |
| **IF meta (operacional)** — [[ADR-418]] | `if_meta = MAX(0, if_meta_bruta − renda_passiva_fora_do_investivel_mensal × 12 / (trs_pct/100))`. **Base única** de `if_pct`, `if_gap` e `prazo_anos_realista`. Qual base é esta vai publicada em `goals.if_meta_base`. | E5 JSON · `goals.if_meta` · `compor_meta_if` |
| Progresso IF (%) | `progresso_if_pct = investivel_efetivo / if_meta × 100` | E5 JSON · `goals.if_pct` · score |
| Gap IF | `if_gap_brl = MAX(0, if_meta − investivel_efetivo)` | E5 JSON · `goals.if_gap` |
| Prazo realista (anos) | Ver §Tempo até a meta abaixo — três ramos, um deles **retido por escolha** | E5 JSON · `goals.prazo_anos_realista` · `solve_prazo_anos` |

**O invariante é o par, não a fórmula** ([[ADR-418]] §D1). Renda passiva de ativo **dentro**
de `investivel_efetivo` não desconta a meta — descontar contaria o ativo duas vezes
([[ADR-142]]). Renda de ativo **fora** desconta — não descontar cobra a exclusão duas vezes.
Com `imoveis_no_if = true` o termo é zero e `if_meta == if_meta_bruta`; com `false` (o
**default** desde [[ADR-223]]) o aluguel observado entra no desconto.

`goal.if` **v2** ([[ADR-140]], `renda_passiva_atual_mensal_brl`) segue **candidato, não em
produção** — o termo do desconto é observado pelo pipeline, não declarado pela família.

### Tempo até a meta — [[ADR-373]]

Com `PV = investivel_efetivo`, `FV = if_meta`, `PMT = meta_aporte_mensal` e
`r = (1 + retorno_real_anual_pct/100)^(1/12) − 1` (taxa **mensal** equivalente):

| Ramo | Condição | Fórmula | Resultado |
| --- | --- | --- | --- |
| Meta atingida | `PV ≥ FV` | — | `0` |
| Composto | `PMT > 0` e `r > 0` | `n = ln((FV + PMT/r) / (PV + PMT/r)) / ln(1+r)` | anos = `n/12` |
| Linear | `PMT > 0` e `r == 0` | `n = (FV − PV)/PMT` | anos = `n/12` |
| **Retido** | `PMT == 0` e `r > 0` | `n = ln(FV/PV)/ln(1+r)` **converge** | `null` + motivo |
| Sem trajetória | `PMT == 0` e `r == 0` (ou `PV == 0`) | não converge | `null` + motivo |

O ramo **retido** é uma decisão de metodologia, não uma limitação: aporte zero
não é declarável (`goal.aporte_mensal.schema.json` exige `exclusiveMinimum: 0`),
logo é sempre ausência de insumo, e projetar sobre ele seria o produto escolher
a premissa "você não aporta" em nome da família. Os dois motivos de ausência
nomeiam o insumo que falta; só o de não-convergência afirma inviabilidade.

Ausência de `retorno_real_anual_pct` cai no default de 6% (`default_if_absent`);
`0` **declarado** permanece `0`. Confundir os dois faria o ramo linear projetar
sobre premissa que ninguém escolheu.

## Política de base temporal (mensalização) — [[ADR-306]]

| Família de métrica | Base canônica | Rótulo `janela` |
| --- | --- | --- |
| Ratios/KPIs, score, reserva, Perini (denominador), Cerbasi, folga | **Janela 12m** — últimos 12 meses **documentados** (gap de calendário nunca entra como zero) | `"12m"` |
| Agregados históricos (fluxo top-level, orçamento prospectivo, charts) | Full-period, permitido **apenas com rótulo** | `"full"` |
| Mensalizações fiscais (renda passiva, TRS) | Ano-base IRPF ÷ 12 | `"irpf_<ano>"` |
| Valores mensais por natureza (`parcela_mensal`, `aporte_mensal`) | Não são mensalização de série | isentos |

Todo bloco do payload E5 com campo mensalizado derivado de série temporal
carrega `janela` (tipo conceitual) + `janela_meses` (meses documentados
reais). Invariante testado em `tests/test_e5_janela_labels.py`.

## Reserva de emergência

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| Custo essencial mensal | Média mensal sobre a **janela canônica de 12 meses documentados** ([[ADR-306]] — supersede a regra "média trimestral", nunca implementada; sazonais essenciais como IPTU/IPVA/educação são recorrentes reais) das categorias `moradia, alimentacao, transporte, saude, seguros, servicos_domesticos, educacao, suporte_familiar, financiamentos` + impostos não-PJ (IPTU, IPVA, IRPF). Lista canônica em `scoring.json:reserva_emergencia._base_calculo`. | E5 JSON · `saude_financeira.reserva_emergencia.custo_essencial_mensal_brl` |
| Reserva-alvo | `reserva_alvo = custo_essencial_mensal × meses_alvo`. `meses_alvo` por composição de renda: CLT estável 6, mista 12, PJ-dominante 18 (ver `methodology.md` §RESERVA). | E5 JSON · `saude_financeira.reserva_emergencia.alvo_brl` |
| Cobertura atual (meses) | `cobertura_meses = reserva_liquida_disponivel ÷ custo_essencial_mensal`. Alimenta o componente `cobertura_despesas` do score (peso 1.5). | E5 JSON · `score.componentes[]` |

## Alocação (AUVP)

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| Desvio por classe | `desvio_classe_pct = atual_pct − alvo_pct` (assinado — negativo = subalocado). | E5 JSON · `estrategia_investimentos.alocacao.desvio_por_classe` |
| Desvio máximo | `desvio_max_pct = MAX(\|desvio_classe_pct\|)`. KPI AUVP — sinaliza a classe mais defasada (próximo aporte vai aqui). **Não somar desvios** (zero-soma). | E5 JSON · `estrategia_investimentos.alocacao.desvio_max_pct` · schema `goal.alocacao_alvo.v2` |

## Score financeiro

Definição completa em `methodology.md` §SCORE FINANCEIRO; parametrização
em `scoring.json:score_componentes`. Resumo:

| Componente | Peso | Range |
| --- | --- | --- |
| Taxa Poupança Recorrente | 2.0 | 0% → 50% |
| Cobertura Despesas | 1.5 | 3 → 24 meses |
| Taxa Endividamento (invertido) | 1.5 | 5% → 50% |
| Progresso IF | 2.0 | 5% → 80% |
| Diversificação Patrimonial | 1.0 | 1 → 6 categorias |

`score = Σ(componente_i × peso_i) / Σ(peso_i)` em escala 0-10 com 1
decimal.

## Projeção de aportes

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| Valor futuro (FV) de série de aportes | `FV = aporte × ((1+r)^n − 1) / r`, onde `r = retorno_real_anual_pct/12`, `n = horizonte_anos × 12`. Premissas declaradas no relatório (Trinity ou Perini). | Metas (`goals.json`) · narrativas E5 |
| Aporte necessário | Resolver `FV` para `aporte` dado `if_meta_liquida` e horizonte. | E5 JSON · schema `goal.if.v2:derived.aporte_necessario_mensal_brl` |

A UI nativa (`ReportPremissasBlock`) replica um subconjunto desta tabela
para tooltips e o bloco "Premissas e como calculamos".

## TRS efetiva e renda passiva

Card "Rentabilidade" do relatório (seção S3) mostra **TRS efetiva** — yield
observado de renda passiva sobre patrimônio gerador, **não retorno total**
(yield + capital gain). Decisão arquitetural completa em
[ADR-191](../adr/191-card-rentabilidade-trs-efetiva.md).

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| TRS efetiva (% a.a.) | `trs_efetiva_pct = renda_passiva_anual_brl / patrimonio_gerador_brl × 100`. Renda passiva observada via IRPF (dividendos isentos + JCP + aplicações + ganho de capital + exterior + aluguéis). Patrimônio gerador exclui residência principal, veículos, derivativos; inclui caixa-excedente (caixa − reserva-alvo). | E5 JSON · `passive_income.trs_efetiva_pct` · `ratios.rentabilidade.valor_pct` |
| Meta TRS (yield-alvo) | **Não existe** desde A40.l47 ([[ADR-191]] §emenda 2026-08-14). O card publicava `meta_pct`, e a única chave que poderia alimentá-la (`goals.trs_pct`) é taxa de **saque** — comparar as duas promove decumulação a alvo de retorno (RV4-13). A TRS efetiva é valor observado e não tem comparador. | — (campo removido do payload) |
| Taxa de retirada segura (SWR) ([[ADR-191]] emendas 2026-07-15 · 2026-08-14) | **Um conceito só, hoje.** `trs_pct` (default 5%) é a taxa prudente de **decumulação**: dimensiona a meta de IF (`if_meta = renda × 12 ÷ trs_pct`, regra ×25) e a estimativa de renda passiva sobre o investível. A emenda de 2026-07-15 atribuía essa chave também ao card como "yield-alvo"; a de 2026-08-14 desfaz isso — o `goal.if.v2` a define como retirada, o wizard a coleta como retirada, e há campo separado para retorno (`retorno_real_anual_pct`). | `goals.trs_pct` · `goals.taxa_retirada_segura_pct` (Trinity 4%) |
| Cobertura essencial via renda passiva (%) | `cobertura_despesa_essencial_pct = renda_passiva_mensal_brl / custo_essencial_mensal_brl × 100`. Tradução operacional: "renda passiva atual cobre N% do custo essencial". 100% = independência sobre o essencial. | `ratios.rentabilidade.cobertura_despesa_essencial_pct` |
| Defasagem do dado (meses) | `defasagem_meses = (reference_date − 01-jan(ano_base + 1))`. Mede envelhecimento do IRPF consumido; >18 meses justifica empty state "dado defasado". | `passive_income.defasagem_meses` · `ratios.rentabilidade.defasagem_meses` |

### Status do card

`ratios.rentabilidade.status` é enum de 4 valores, derivado de
`PassiveIncomeResult.status` cruzado com disponibilidade do
`despesa_mensal_essencial`:

| Status | Significado | UI |
| --- | --- | --- |
| `ok` | TRS válida + cobertura calculável. | Mostra valor, meta, cobertura, ano-base, defasagem. |
| `sem_irpf` | Sem declaração IRPF carregada. | Empty state pedindo upload do IRPF. |
| `gerador_zero` | Sem patrimônio gerador identificado. | Empty state explicando ausência de carteira de renda. |
| `sem_dados_essencial` | TRS válida, mas `categorias_in` vazias ou fluxo sem categorias essenciais mapeadas. | Mostra valor + nota "cobertura essencial não disponível — categorização incompleta". |

### Comparativos descartados (ADR-191 §D5 — não fazer)

- **Sem CDI** no card: TRS efetiva é yield diversificado com tax-shield
  parcial (dividendos isentos PF); CDI é taxa nominal pré-IR de RF.
  Comparar induz mau comportamento ("se TRS < CDI, 100% Tesouro Selic
  basta?" — falso, ignora valorização e diversificação).
- **Sem retorno total da carteira** (yield + capital gain): exige NAV
  histórico por holding, não calculado pelo pipeline E2/E3.
- **Sem Trinity 4%** no card: Trinity é SWR de depleção do principal
  (projeção de IF), incomparável com yield de fluxo observado. `trs_trinity_pct`
  em `PassiveIncomeConfig` permanece para uso em projeções de IF, não neste card.

## Imóveis (cap rate, concentração, spread vs benchmarks)

Card S4 ("Real Estate — Imóveis e Renda Passiva"). Decisão arquitetural completa em
[ADR-216](../adr/216-cap-rate-liquido-canonico-imoveis.md); cascade de fontes de aluguel
por imóvel em §D9 da mesma ADR. ADR-216 supersede o display de yield bruto (`yield_imoveis_pct`)
que vivia em [`pipeline/domain/services/narrativas/charts_narrator.py:254`](../../pipeline/domain/services/narrativas/charts_narrator.py).

### Princípio metodológico

Cap rate **líquido pós-IR pós-custos pós-vacância** (não bruto) é a métrica que vai no card.
Yield bruto esconde IR carnê-leão PF (~22-27,5%), taxa de administração da imobiliária (5-12%),
IPTU, condomínio, manutenção (~1% valor/ano), vacância (média BR ~15%). Comparar yield bruto
com CDI nominal pré-IR é maçã/laranja e induz mau comportamento — comparação só vale
**líquido vs líquido**, sob três benchmarks adequados ao framing single-class
("vale a pena manter R$ X em imóveis ou realocar?"):

- **CDI líquido** — custo de oportunidade de renda fixa pós-fixada (default de alocação).
- **NTN-B real** — comparação renda real ↔ renda real (imóvel é hedge inflacionário; NTN-B é renda real explícita).
- **IFIX yield 12m** — classe pareada (FII tijolo isento IR PF).

Imóveis residenciais (cat_1, residência principal) **não entram** no cálculo — só `classification ∈ {investimento_locado, investimento_vago}` (enum em [ADR-215](../adr/215-classificacao-imoveis-override-db-first.md)).

### Fórmulas canônicas

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| Cap rate **bruto** (por imóvel) | `cap_rate_bruto_pct = aluguel_anual_bruto / valor_imovel_irpf × 100`. Preservado para auditoria/tooltip; **não** é a métrica em destaque. | E5 JSON · `real_estate.cap_rate_bruto_pct` |
| Cap rate **líquido** (por imóvel) | `cap_rate_liquido_pct = (aluguel_anual_bruto − taxa_administracao_anual − ir_retido_anual − ir_carne_leao_anual − iptu_anual − condominio_anual − manutencao_anual − vacancia_anual) / valor_imovel_irpf × 100`. Cada componente carrega `origem ∈ {informe, irpf, e4, default, estimado_pro_rata}` no payload — sinaliza confiança no tooltip (ADR-216 D9). | E5 JSON · `real_estate.cap_rate_liquido_pct` |
| Cap rate líquido (agregado da carteira) | Média ponderada pelo `valor_imovel_irpf` dos imóveis com `classification ∈ {investimento_locado, investimento_vago}`. | E5 JSON · `real_estate.cap_rate_liquido_pct` (top-level) |
| Concentração imobiliária (%) | `concentracao_imobiliaria_pct = imoveis_investimento(cat_2) / carteira_produtiva × 100`, onde `carteira_produtiva = investivel_financeiro + cat_2` (FIXA, toggle-independente). **Base carteira** ([[ADR-340]] · C11-Fase2): mede quanto do capital **produtivo** está em classe ilíquida; residência (cat_1) e veículos ficam **fora** do denominador (não são carteira). SSOT computado 1× em `RatiosCalculator` (`compute_concentracao_imobiliaria_pct`). Alerta `concentracao_alta` >50%. Threshold configurável via [[ADR-134]] `ConfigStore`. | E5 JSON · `ratios.concentracao_imobiliaria` (canônico; `real_estate.concentracao_pct` = alias deprecated 1 ciclo) |
| Spread vs benchmark (pp) | `spread_vs_benchmark_pp = cap_rate_liquido_pct − benchmark_liquido_pct`. Calculado para os 3 benchmarks (CDI, NTN-B, IFIX); negativo = imóvel rendendo menos. Spread em **pontos percentuais** (não razão). | E5 JSON · `real_estate.spreads_pp.{vs_cdi,vs_ntnb,vs_ifix}` |
| Spread anual em R$ (sinal natural) | `spread_brl_anual = patrimonio_imobiliario × (cap_rate_liquido_pct − benchmark_liquido_pct) / 100`. **Sinal natural:** positivo = imóvel ganhando do benchmark; negativo = imóvel perdendo. Para o card UX é este número que dói (não pp). Renomeado de `custo_oportunidade_anual_brl` para evitar ambiguidade de sinal no tooltip. | E5 JSON · `real_estate.spread_brl_anual.{vs_cdi,vs_ntnb,vs_ifix}` |
| Gap de reajuste acumulado (%) | `gap_reajuste_pct = indice_acum_12m_pct × meses_sem_reajuste / 12`. Quantifica em % quanto o aluguel está atrasado vs IGPM/IPCA acumulado — alavanca acionável. Por imóvel; índice = `indice_reajuste` do contrato. | E5 JSON · `real_estate.imoveis[].gap_reajuste_pct` |

### Componentes da fórmula líquida — cascade de fontes (ADR-216 D9)

Cada componente é resolvido pela cascade de fontes; sem dado de fonte preferencial,
cai para a próxima na ordem. Componentes individuais expostos no payload para tooltip
de explicação no card.

| Componente | Cascade (alta → baixa) | Fallback `default` |
| --- | --- | --- |
| `aluguel_anual_bruto` | Informe imobiliária → IRPF carnê-leão → E4 receitas categorizadas → pro-rata pelo valor_irpf | — (sem aluguel = `cap_rate = 0%`) |
| `taxa_administracao_anual` | Informe imobiliária (único) | — (omitir do líquido; degradar tooltip) |
| `ir_retido_anual` | Informe imobiliária (PJ pagador retém) | `0` (PF→PF residencial não retém) |
| `ir_carne_leao_anual` | IRPF analyzer (alíquota **marginal** aplicável ao bucket aluguel, [`pipeline/domain/services/irpf_analyzer.py`](../../pipeline/domain/services/irpf_analyzer.py); **não** a média do contribuinte) | Fallback default 27,5% — viés conservador para o ICP HENRY/UHNW (tipicamente no topo da tabela); cap rate líquido pessimista é mais seguro que otimista |
| `iptu_anual` | Informe imobiliária (quando administra) → E4 despesas categorizadas | Estimar 1% × valor_irpf (regra de bolso BR) |
| `condominio_anual` | Informe (raro) → E4 despesas categorizadas | `0` (não declarado) |
| `manutencao_anual` | (nenhuma fonte primária) | Default **1% × valor_irpf** (regra de bolso BR; gradação por idade/tipo do imóvel — ver §Defaults). Inclui **CAPEX recorrente** (pintura, reforma estrutural), não só zelador |
| `vacancia_anual` | Informe — vacância empírica = `(12 − meses_locado) / 12 × aluguel_anual_bruto` | Default **15% × aluguel_anual_bruto** (média BR; urbano premium pode ser <10%) |
| `valor_imovel_irpf` | IRPF E1.6 (`bens_direitos[]` com `codigo_rfb` imóvel). **Limitação importante:** IRPF carrega imóvel pelo **custo histórico de aquisição** (não valor de mercado) — cap rate sobre imóvel antigo fica **inflado artificialmente**. Override opcional `valor_mercado_brl` por workspace via [[ADR-134]] elimina o viés quando informado | — (sem valor = imóvel não entra no cálculo) |

### Defaults configuráveis

| Parâmetro | Default | Range típico | Justificativa metodológica |
| --- | --- | --- | --- |
| `vacancia_pct` | 15% | 5-25% | Média BR residencial (Secovi/FIPE); urbano premium pode ser <10%. Quando Informe traz vacância empírica (`(12 − meses_locado)/12`), default **não** se aplica — empírico vence. |
| `manutencao_pct` | 1% valor/ano | 0,5%-3% | Gradação por idade/tipo: imóvel novo (<10 anos) 0,5%; médio padrão 1%; alto padrão / tombado / histórico com fachada 2-3%. Inclui CAPEX recorrente (pintura, reforma estrutural), não só zelador. |
| `ir_carne_leao_fallback_pct` | **27,5%** | — | Alíquota marginal típica do ICP HENRY/UHNW (topo da tabela progressiva). Viés conservador — cap rate líquido pessimista é mais seguro que otimista. Quando IRPF carregado, derivar alíquota marginal do bucket `rendimentos_pf` ([ADR-157](../adr/157-schema-irpf-completo-stage-extract-irpf-full.md)), **não** a média do contribuinte. |
| `concentracao_alerta_pct` | 50% | 45-60% | Base **carteira** ([[ADR-340]]): leituras ~1,5-2× as da base líquido antiga (a carteira exclui residência/veículos), então o limiar sobe de 40→50. Provisório (N=1, âncora real 60%), recalibrar com N famílias. Co-threshold `spread_critico` sobe 30→45. RL-7 (hard-block) sobe 60→75. |
| `spread_critico_pct_do_benchmark` | **70%** | — | Cap rate líquido < 70% do CDI líquido (combinado com concentração >30%) dispara alerta `revisão estratégica recomendada`. Calibre teórico inicial; ajustar após Onda 1 (auditoria empírica). |
| `valor_imovel_origem` | `irpf` | `irpf` / `mercado` | Quando workspace fornece `valor_mercado_brl` por imóvel via override, usar; senão IRPF (custo histórico, viés inflado para imóvel antigo). |

Overrides por workspace via [[ADR-134]] `ConfigStore` (mesmo padrão de `category_template`).

### Benchmarks — convenção de `pair` em `market_rates`

`market_rates` ([ADR-135](../adr/135-versionamento-temporal-de-series-fiscais-e-cambio.md))
hoje seeda apenas pares FX (USD/BRL, EUR/BRL). Para S4 são necessários **3 novos `pair`s**
seedados em migration dedicada (pré-requisito Onda 2 do
[plano S4_REAL_ESTATE_ENRICHMENT](../plan/S4_REAL_ESTATE_ENRICHMENT/_README.md)):

| `pair` | Tipo | Unidade | Fonte canônica | Cadência |
| --- | --- | --- | --- | --- |
| `CDI` | Taxa nominal anual | % a.a. | Banco Central (SGS série 12) | Diária |
| `NTNB_REAL_10Y` | Yield real anual interpolado p/ vértice 10 anos | % a.a. real (acima IPCA) | Tesouro Direto / ANBIMA | Diária |
| `IFIX_YIELD_12M` | Dividend yield trailing 12m do índice IFIX (misto: tijolo + papel + híbridos) | % a.a. | B3 / ANBIMA | Mensal |

**Notas de fonte:**

- `NTNB_REAL_10Y` é **vértice 10 anos constante** (interpolado entre títulos disponíveis); não fixe um vencimento específico (ex.: NTN-B 2035 vira título de 5 anos em 2030). Padrão ANBIMA.
- `IFIX_YIELD_12M` é **proxy direcional, não pareamento perfeito** com imóvel físico — IFIX é índice misto (tijolo + papel + híbridos). v2 pode expor `IFII_TIJOLO_YIELD_12M` (subsetor tijolo) quando ANBIMA/B3 publicar.

Normalização para "líquido" é responsabilidade do service (não da seed):

- `cdi_liquido_pct = cdi_nominal_pct × (1 − ir_rf_efetivo_pct/100)` — IR RF tabela regressiva 15-22,5%, peso ponderado pela curva de prazo do workspace; default 17,5%.
- `ntnb_liquido_pct = ntnb_real_pct × (1 − 0.15)` — IR longo prazo 15% (>721 dias).
- `ifix_liquido_pct = ifix_yield_pct × 1.0` — FII tijolo isento IR PF (não normalizar).

### Alertas

| Code | Condição | Severidade | Texto UX |
| --- | --- | --- | --- |
| `concentracao_alta` | `concentracao_imobiliaria_pct > concentracao_alerta_pct` (default 50%, base carteira) | warning | "Concentração em imóveis acima de N% da carteira produtiva — revisão de alocação recomendada." |
| `spread_critico` | `cap_rate_liquido_pct < spread_critico_pct_do_benchmark × cdi_liquido_pct / 100` (default 70%) **E** `concentracao_imobiliaria_pct > 45%` (base carteira) | warning | "Cap rate líquido <70% do CDI combinado com concentração imobiliária >45% da carteira — considerar revisão estratégica." |
| `aluguel_sem_dado` | Todos os imóveis com `origem == "estimado_pro_rata"` | info | "Aluguel por imóvel estimado — para precisão, carregue Informe de Rendimentos da Imobiliária." |
| `contrato_reajuste_pendente` | `meses_desde_ultimo_reajuste > 12` para qualquer imóvel | info (por imóvel) | "Contrato sem reajuste há N meses — IGPM/IPCA acumulado: X% (gap acumulado Y%)." |

**Gatilho instantâneo (v1):** `spread_critico` é avaliado por snapshot do relatório, não série temporal. Persistência ("12 meses persistente") fica como métrica derivada de v2 quando houver série temporal de market_rates + snapshots de relatório — débito rastreado.

### Comparativos descartados (não fazer)

**Permanentes (não voltar):**

- **Yield bruto no card** — ADR-216 D1 explicitamente proíbe; mantido só em tooltip/audit.
- **CDI sozinho como único benchmark** — ADR-216 D2 (tríade obrigatória) e [ADR-191 §D5](../adr/191-card-rentabilidade-trs-efetiva.md) (rejeitou CDI no card TRS por motivo análogo). ADR-216 difere de ADR-191 porque cap rate é single-class; tríade resolve a diferença.
- **Pro-rata como fonte primária** de aluguel — só fallback final; sempre flagged como `origem == "estimado_pro_rata"` no UI.
- **Valor de reposição (custo de reconstrução)** no cap rate — métrica de seguradora; mede risco patrimonial, não rentabilidade. Pode aparecer em S4 v2 como métrica **separada** (cobertura de seguro vs valor de reposição), nunca dentro do cap rate.

**Descartados de v1 (promover a v2 quando aplicável):**

- **Valorização patrimonial** no `cap_rate_liquido` — valorização IRPF é fiscal (atualização anual de declaração), não de mercado; misturar yield com valorização fiscal engana. v2 pode expor como métrica separada (`valorizacao_irpf_anual_pct`).
- **Cap rate de mercado da praça vs cap rate observado** — comparação muito útil ("seu imóvel rende 3,5%, praça do bairro rende 5,5% — aluguel subprecificado"). Dependência de fonte externa (FIPE-ZAP, QuintoAndar API) — v2.
- **Net effective rent vs face rent** (descontos, carência) — em comercial high-end importa; em residencial BR é raro. v2 quando S4 cobrir comercial-grade.
- **GLA (Gross Leasable Area) / cap rate por m²** — irrelevante para residencial PF (ICP atual); importante para comercial/sala/galpão. Sem GLA, cap rate de galpão vs cap rate de cobertura ficam comparáveis em pp mas escondem R$/m² muito diferente. v2 quando comercial entrar.
- **Persistência temporal do spread crítico** — exigia série mensal de snapshots de cap rate + market_rates; v1 usa gatilho instantâneo. v2 promove a métrica temporal.

### Débitos rastreados (v2)

| Débito | Lane futura | Bloqueio atual |
| --- | --- | --- |
| `IFII_TIJOLO_YIELD_12M` como pair adicional | Sprint após Onda 6 | ANBIMA/B3 não publica subsetor estável |
| `valor_mercado_brl` por imóvel (substitui IRPF) | Onda 6 v2 | Override via ADR-134 já permite manual; auto-fetch via API externa é v2 |
| Persistência temporal do spread | v2 | Exige série de snapshots em `pipeline_artifacts` |
| Cap rate de mercado da praça | v2 | Fonte externa (FIPE-ZAP) |
| GLA / cap rate por m² | v2 (comercial) | Schema do imóvel não captura GLA hoje |

## Proteção Patrimonial (S_PROTECAO — pilar AUVP)

Fórmulas registradas **antes** da implementação (gate G2 ADR-240). Implementadas
em [`pipeline/domain/services/protecao_analyzer.py`](../../pipeline/domain/services/protecao_analyzer.py).

### `protecao.premio_total_anual` (KPI G — hero)

```
premio_total_anual_brl = Σ premio_total_brl
                          ∀ apolice ∈ apolices_vigentes_em(data_referencia)
```

Onde `apolices_vigentes_em(D) = { a ∈ apolices : a.vigencia_inicio ≤ D ≤ a.vigencia_fim }`.
Vencidas (`a.vigencia_fim < D`) e vencendo (`D ≤ a.vigencia_fim ≤ D + 30d`) entram em
listas separadas no payload — não somam no KPI G.

### `protecao.pct_renda` (KPI B — ancorado Cerbasi)

```
pct_renda_anual = premio_total_anual_brl / renda_anual_liquida_brl
```

| Intervalo | Sinal |
|-----------|-------|
| `pct < 0.01`     | atenção (sub-investido) |
| `0.01 ≤ pct ≤ 0.03` | ok |
| `0.03 < pct ≤ 0.05` | ok-forte |
| `pct > 0.05`     | atenção (sobreposições?) |

Quando `renda_anual_liquida_brl == 0` → KPI ausente (não dividir por zero).

**Escopo do numerador (ADR-240 §Emenda 2026-08-08).** A soma cobre **só** apólice
extraída de documento. As duas fontes de cobertura não compartilham chave de
identidade (o cadastro `Protection` não guarda `apolice_numero`), então uni-las
arriscaria dupla-contagem — pior que omissão num KPI monetário. Consequência:

```
veredito_pct_renda_suprimido = categorias_somente_no_cadastro ≠ ∅
```

Com o veredito suprimido, o **valor** continua reportado e a **faixa não é
emitida** — afirmar suficiência sobre soma sabidamente parcial é o mesmo erro que
afirmar ausência sobre fonte única. O escopo é declarado no payload em
`protecao_patrimonial.escopo_cobertura`; o consumidor de UI é
[`ProtecaoKpiHero.tsx`](../../frontend/src/components/report/sections/SProtecao/ProtecaoKpiHero.tsx).
Mesma regra vale para `protecao.premio_total_anual` (KPI G), que é o numerador.

### `protecao.gap_bem_auto` (KPI C V1)

Por veículo segurado em apólice vigente:

```
gap_pct = (valor_fipe_dezembro_atual - lmi_brl_casco) / valor_fipe_dezembro_atual
```

Onde `lmi_brl_casco` é o LMI da cobertura `material` com `lmi_modo` ∈
{`valor_fixo`, `primeiro_risco_absoluto`} OU `lmi_fipe_percentual * valor_fipe`
quando `lmi_modo='fipe_percentual'`. Sinal:

| Gap | Sinal |
|-----|-------|
| `gap < 0.10`     | ok |
| `0.10 ≤ gap < 0.25` | atenção branda |
| `gap ≥ 0.25`     | atenção |

Quando `valor_fipe == 0` (veículo sem FIPE — depende de A18 L3) → bem sai da lista;
UI mostra placeholder "FIPE pendente — refresh anual".

### `protecao.tem_cobertura` (união das evidências — ADR-240 §Emenda 2026-08-08)

Predicado compartilhado pelos dois flags do KPI F. Cobertura de uma categoria é
afirmada sobre a **união** das fontes, nunca sobre uma só:

```
tem_cobertura(cat) = existe_apolice_extraida_com_cobertura(cat)
                     OR existe_cadastro_vigente_na_categoria(cat)
```

Onde `existe_cadastro_vigente_na_categoria(cat)` percorre `Protection` (ADR-192)
com `status == "Ativa"` e vigência contendo `data_referencia` (`ends_at` nulo =
vitalícia). Vocabulário canônico da união: **apenas `vida` e `saude`** — só esses
descrevem o mesmo produto nos dois lados. `acidentes` (documento) e `invalidez` /
`patrimonial` / `rc_profissional` / `sucessorio` (cadastro) **não** entram: casar
por semelhança faria uma apólice de acidentes silenciar o gap de vida.

Implementação: [`pipeline/domain/services/cobertura_consolidada.py`](../../pipeline/domain/services/cobertura_consolidada.py)
(`consolidar_cobertura` → `CoberturaConsolidada.tem_cobertura`).

### `protecao.flag_vida` (KPI F vida)

```
flag_vida = (
    has_dependentes_menores_18 OR
    has_conjuge_sem_renda_propria OR
    (passivo_total / patrimonio_liquido) > 0.30
) AND NOT tem_cobertura("vida")
```

Sem `family_members` (workspace zero-config) → `flag_vida=False` silenciosamente
(gate G5 — degrada gracioso). O `rationale` distingue a proveniência do
fechamento: `apolice_vida_ativa` quando o documento sustenta, e
`cobertura_vida_cadastrada` quando só o cadastro sustenta.

### `protecao.flag_saude` (KPI F saúde)

```
flag_saude = (
    NOT has_deducao_saude_irpf AND
    NOT has_categoria_saude_e4_3_meses
) AND NOT tem_cobertura("saude")
```

Copy mais branda que vida (PJ comum cobre saúde). ADR-240 D3 detalha texto.

### Custo essencial mensal — base da cobertura

`custo_essencial_mensal_brl` é a soma das médias mensais das **9 categorias
canônicas** declaradas em
`scoring.json:reserva_emergencia._base_calculo.custo_essencial_mensal.categorias_in`
(moradia, alimentação, transporte, saúde, seguros, serviços domésticos,
educação, suporte familiar, financiamentos). Implementação:
[`pipeline/domain/services/essential_expense_calculator.py`](../../pipeline/domain/services/essential_expense_calculator.py)
(helper puro) + [`fluxo_caixa_enricher.py`](../../pipeline/domain/services/fluxo_caixa_enricher.py)
(popula `fluxo.despesa_mensal_essencial` e `fluxo.janela_12m.despesa_mensal_essencial`).

> **Débito conhecido (Track T06):** impostos não-PJ (IPTU, IPVA, IRPF)
> declarados em `_base_calculo.custo_essencial_mensal.impostos.incluir`
> ainda não cruzam com a origem do lançamento para distinguir PF vs PJ —
> v1 trata como categoria comum quando aparece em `categorias_in`.

## PGBL — base dedutível, teto e economia — [[ADR-236]] · [[ADR-375]]

**Teto e restante são grandezas distintas, com donos distintos.** Confundi-las é a
origem do defeito que a [[ADR-375]] fecha: a S7 rotulava *"Limite PGBL/ano (12%)"*
um valor que era o **restante**.

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| Base dedutível (ano-base declarado) | `pgbl_base_anual = renda_tributavel_pf_irpf_anual` — o **total** dos rendimentos tributáveis do IRPF (`rendimentos_pj + rendimentos_pf`), fonte única. O pró-labore do fluxo **não** é somado: ele já está no IRPF, porque a própria PJ é fonte pagadora ([[ADR-236]] §Emenda 2026-08-17). **Lucros distribuídos não entram** — são isentos. Sem IRPF a base **não existe**; ausência não é zero. | `cascata_calculator._compute_layers` · E5 · `tributario.cascata.pgbl_base_anual` O **ano-base** sai de `resolve_ano_base_fiscal` ([[ADR-305]] D1/D2), o mesmo que elege o do Card B — antes a S8 lia o artifact mais recente por `created_at` e os dois podiam publicar sobre anos diferentes ([[A40.l65]] §Escopo 1, #1672). |
| Teto de 12% (ano corrente) | `pgbl_limite_anual = pgbl_base_anual × 0,12` | [`cascata_pgbl.compute_pgbl`](../../pipeline/domain/services/tributario/cascata_pgbl.py) · `tributario.cascata.pgbl_limite_anual` |
| Restante dedutível (ano-base declarado) | `restante = Σ(tributável × 12% − já_aportado)`, clamp ≥ 0 ([[ADR-189]]) | `IRPFAnalyzer.pgbl_capacidade_dedutivel` · `irpf.pgbl_capacidade_dedutivel_brl` |
| Alíquota marginal | Faixa de `fiscal_parameters.ir_brackets` que **contém** a renda — nunca a faixa excedida nem a do topo | [`irpf_faixa_marginal.resolve_faixa_marginal`](../../pipeline/domain/services/irpf_faixa_marginal.py) |

### O que a base do teto NÃO é

O teto de 12% incide sobre o **total dos rendimentos tributáveis** (RIR/2018
art. 68 — *"12% do total dos rendimentos computados na determinação da base de
cálculo"*), **não** sobre a base de cálculo líquida de deduções, e **não** sobre
`receita_pj × 32%`. O proxy de lucro presumido foi **removido**, não recalibrado:
sob lucro presumido ele aproxima o teto da distribuição **isenta** (Lei 9.249/95
art. 10), que é o *complemento* da base PGBL — nenhum coeficiente conserta
referente invertido ([[ADR-375]] §D3).

**A faixa marginal, essa sim, resolve sobre base de cálculo** (líquida das deduções
legais) — é sobre ela que a tabela progressiva é definida. Resolver sobre o bruto
enviesa a faixa **para cima**, e o viés aponta na direção que vende o produto.

### Piso de prescrição — três condições ([[ADR-375]] §D4)

Não se prescreve aporte nem se publica "economia de IR" a menos que **todas**
sejam verdadeiras:

1. `tipo_declaracao_ir == "completa"` **conhecido**, não defaultado — desconhecido
   devolve `pgbl_aplicavel = False` com motivo `tipo_declaracao_desconhecido`;
2. a economia diferencial no ano é positiva;
3. requisitos previdenciários aplicáveis satisfeitos — em regra, contribuição
   ao RGPS/RPPS; aposentados e pensionistas desses regimes são dispensados do
   recolhimento, e PGBL de dependente maior de 16 anos exige contribuição também
   em nome do dependente. Quando desconhecidos, a copy declara a condição sem
   inventar inelegibilidade ([Receita Federal](https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/preenchimento/manual-mir/pagamentos-ou-doacoes/despesas-dedutiveis#previdencia)).

Abaixo do piso a saída **não é número menor: é "não se aplica" com o motivo**. E a
dedução nunca sai em `--semantic-gain` — é **diferimento**, não ganho: o resgate é
tributado sobre o **total** (PGBL), não só sobre o rendimento.

### Economia de IR — a diferencial

Forma canônica: `economia = IR(base) − IR(base − aporte)`, sobre `IR(base, ano)`
progressiva. Ela devolve **zero para o isento por construção**, o que
`limite × aliquota_marginal` não faz — e é por isso que o instrumento antigo está
encerrado ([[ADR-375]] §D5).

| Grandeza | Fórmula | Onde |
| --- | --- | --- |
| Imposto anual devido | `IR(base) = base × alíquota(faixa que CONTÉM a base) − parcela a deduzir`, piso zero | [`irpf_faixa_marginal.ir_devido_anual`](../../pipeline/domain/services/irpf_faixa_marginal.py) |
| Economia do aporte | `IR(base) − IR(base − aporte)` | [`pgbl_economia_ir.economia_diferencial`](../../pipeline/domain/services/pgbl_economia_ir.py) |

> **Implementada em 2026-08-24 ([[A40.l64]] PR2).** A ressalva anterior —
> `deducao_brl_cents` em escala mensal contra faixas anuais — **caiu com a
> [[A40.l56]]**: a row AC2026 que a migration `adr389tabelas` semeia traz parcelas
> anuais (R$ 2.185,92 · 4.729,91 · 8.105,85 · 10.904,66), e o hook
> `fiscal-brackets-continuity` guarda a congruência. Sem tabela configurada — o
> dict legado pré-A7.2b, onde `deducao_brl_cents` é sempre 0 — o analyzer degrada
> para `restante × aliquota_fallback`, como sempre fez.
>
> O diferencial **não modela** o redutor da Lei 15.270/2025 nem o IRPFM. É por isso
> que a row AC2026 nasce `regime_completo: false` e o card retém a economia
> ([[ADR-389]] D4); modelá-los é [[A40.l64]] PR3/PR4. O redutor compõe **dentro**
> de `economia_diferencial`: por ser função do rendimento bruto, ele não se move
> com o aporte e entra dos dois lados da diferença.
