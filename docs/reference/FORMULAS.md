# Glossário de fórmulas

Referência canônica **número ↔ regra**. Detalhes de implementação vivem
em `pipeline/domain/services/` e nos scripts do pipeline. Quando uma
fórmula ficar ambígua entre este doc, `methodology.md` e `scoring.json`,
**`scoring.json` vence em parametrização** e este doc vence em
**definição matemática**.

## Patrimônio

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| Patrimônio bruto | `bruto = cat_1 + cat_2 + cat_3 + cat_4 + cat_5 + cat_6 + cat_7` (categorias em `definitions.md` §FÓRMULAS PATRIMONIAIS) | E5 JSON · `patrimonio.bruto` |
| Patrimônio líquido | `liquido = bruto − dividas` | E5 JSON · `patrimonio.liquido` |
| Patrimônio investível (financeiro) | `investivel_financeiro = cat_3 + cat_4 + cat_5 + cat_6` — apenas ativos financeiros líquidos. **Métrica Perini/AUVP correta para `progresso_if`.** | E5 JSON · `patrimonio.investivel_financeiro` |
| Patrimônio investível (total) | `investivel_total = bruto − cat_1 − cat_7` (exclui residência principal e veículos). Métrica retro-compat. | E5 JSON · `patrimonio.investivel_total` |
| Patrimônio investível (efetivo) | `investivel_efetivo = investivel_financeiro + (cat_2 if workspace.imoveis_no_if else 0)` | E5 JSON · `patrimonio.investivel_efetivo` |

## Independência Financeira

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| IF meta bruta | `if_meta_bruta_brl = renda_passiva_mensal_brl × 12 / (trs_pct/100)`. Didático — patrimônio total que sustenta o alvo. | E5 JSON · `independencia_financeira.meta_bruta` · schema `goal.if.v2` |
| IF meta líquida | `if_meta_liquida_brl = MAX(0, (renda_passiva_mensal_brl − renda_passiva_atual_mensal_brl) × 12 / (trs_pct/100))`. Operacional — quanto **falta** acumular. **Métrica usada em `progresso_if`.** | E5 JSON · `independencia_financeira.meta_liquida` |
| Progresso IF (%) | `progresso_if_pct = investivel_efetivo / if_meta_liquida × 100` | E5 JSON · `goals.if_pct` · score |
| Gap IF | `if_gap_brl = MAX(0, if_meta_liquida − investivel_efetivo)` | E5 JSON · `goals.if_gap` |

## Reserva de emergência

| Conceito | Fórmula | Onde no código |
| --- | --- | --- |
| Custo essencial mensal | Média **trimestral** das categorias `moradia, alimentacao, transporte, saude, seguros, servicos_domesticos, educacao, suporte_familiar, financiamentos` + impostos não-PJ (IPTU, IPVA, IRPF). Lista canônica em `scoring.json:reserva_emergencia._base_calculo`. | E5 JSON · `saude_financeira.reserva_emergencia.custo_essencial_mensal_brl` |
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
| Meta TRS | Referência consagrada de **5% a.a.** (yield diversificado de carteira de renda). Configurável via `RentabilidadeConfig.meta_pct`. | `ratios.rentabilidade.meta_pct` |
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
