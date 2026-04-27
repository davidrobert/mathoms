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
