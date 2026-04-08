# Plano de Correção — Relatório Financeiro Ferreira Campos
## Data: 2026-04-06
## Referência: Diagnóstico de causas raiz do relatório v5.3

---

## RESUMO EXECUTIVO

O relatório financeiro apresenta ~25 problemas visíveis ao usuário, originados de **3 causas raiz** que se propagam em cascata:

| # | Causa Raiz | Impacto | Cards afetados |
|---|-----------|---------|----------------|
| CR-1 | **E6 hardcoda dados** em vez de ler o E5 JSON | Dados fictícios ou zerados | ~15 seções |
| CR-2 | **E5 não produz campos** que o E6 espera | Tabelas vazias | 6+ cards |
| CR-3 | **Mismatch de schema** entre E5 output e E6 input | Dados existem mas não são renderizados | 4 tabelas |

A correção está dividida em **5 fases** ordenadas por dependência (não se pode fazer fase 3 sem fase 2). Estimativa total: 4-6 horas de trabalho.

---

## FASE 1 — E5: Produzir os campos que faltam (P0)

**Por que primeiro:** O E6 não tem como renderizar dados que não existem. Precisamos que o E5 produza todos os campos que o E6 precisa.

### 1.1 — Criar `tabela_categorias` no patrimônio (E5)

**Problema:** O E6 (`build_patrimonio_categorias_card`, linha 672) lê `patrimonio.tabela_categorias` — uma lista de `{categoria, valor, pct}`. O E5 produz `patrimonio.composicao` com o **mesmo formato**, mas com chave diferente.

**Correção no `e5_analyze.py`:** Após a linha 352 (`"composicao": composicao`), adicionar alias:

```python
"tabela_categorias": composicao,  # alias para E6 build_patrimonio_categorias_card
```

**Impacto:** Card "Patrimônio por Categoria" sai de vazio para 6 linhas.

### 1.2 — Criar `tabela_receitas` no fluxo de caixa (E5)

**Problema:** O E6 (`build_receitas_fonte_card`, linha 702) lê `fluxo_caixa.tabela_receitas` — lista de `{categoria, valor, pct}`. O E5 produz `fluxo_caixa.por_fonte` como dict `{categoria: valor}`.

**Correção no `e5_analyze.py`:** Na função `analyze_fluxo_caixa`, após calcular `por_fonte`, gerar:

```python
total_receita = sum(por_fonte.values())
tabela_receitas = [
    {"categoria": cat, "valor": val, "pct": round((val / total_receita) * 100, 2) if total_receita else 0}
    for cat, val in sorted(por_fonte.items(), key=lambda x: x[1], reverse=True)
    if val > 0
]
```

E incluir `"tabela_receitas": tabela_receitas` no return dict.

**Impacto:** Card "Receitas por Fonte" sai de R$ 0 para ~R$ 1.3M com 7 categorias.

### 1.3 — Criar `investimentos.tabela_classes` (E5)

**Problema:** O E6 (`build_investimentos_classe_card`, linha 728) lê `investimentos.tabela_classes`. O E5 carrega `investimentos-4_unified.json` mas **nunca o usa** (linha 849).

**Correção no `e5_analyze.py`:** Criar nova função `analyze_investimentos_classes(baseline, investimentos_e4)` que:

1. Agrupe os ativos do baseline por classe (Renda Fixa, Ações, Imóveis Investimento, Cripto, Exterior, Outros)
2. Calcule valor e percentual de cada classe
3. Retorne `{"tabela_classes": [...], "total": X}`

Registrar no output JSON como `"investimentos"`.

**Impacto:** Card "Investimentos por Classe" sai de R$ 0 para ~R$ 2.2M.

### 1.4 — Criar `reserva_emergencia.composicao_liquida` com chaves corretas (E5)

**Problema:** O E6 (`build_reserva_emergencia_card`, linhas 805-810) espera chaves específicas dentro de `composicao_liquida`: `cofrinhos_itau`, `cdb_santander`, `renda_fixa_c6`, `picpay`. O E5 produz `composicao_liquida` com chaves genéricas: `investimentos_david`, `investimentos_mariana`, `caixa_moeda_estrangeira`.

**Correção no `e5_analyze.py`:** Na função `analyze_reserva_emergencia`, decompor os investimentos líquidos em componentes reais (D+0/D+1) a partir do baseline e dos dados E4:

```python
composicao_liquida = {
    "cofrinhos_itau": extrair_valor_cofrinhos(baseline),
    "cdb_santander": extrair_valor_cdb_santander(baseline),
    "renda_fixa_c6": extrair_valor_rf_c6(baseline),
    "picpay": extrair_valor_picpay(baseline),
    "total_liquido": soma,
    "cobertura_meses": soma / despesa_mensal if despesa_mensal > 0 else 0,
}
```

Alternativamente, corrigir o E6 para ler as chaves que o E5 já produz (ver Fase 3).

**Impacto:** Card "Reserva de Emergência" e tabela "Composição da Liquidez" saem de R$ 0.

### 1.5 — Criar `endividamento.dividas` como lista detalhada (E5)

**Problema:** O E6 (`build_endividamento_card`, linha 842) lê `endividamento.dividas` como lista de `{descricao, saldo, parcela, taxa}`. O E5 produz apenas `{total_dividas, percentual_patrimonio, detalhe (string)}`.

**Correção no `e5_analyze.py`:** Na função `analyze_endividamento`, extrair dívidas individuais do baseline (ex: financiamento Itaú) e produzir lista:

```python
"dividas": [
    {"descricao": "Fin. Imobiliário Itaú", "saldo": 234792.61, "parcela": None, "taxa": None}
]
```

**Impacto:** Card "Endividamento" ganha linhas de detalhe.

### 1.6 — Popular `tarefas` e `alertas` (E5)

**Problema:** Ambos são `[]` vazios. Os 6 KPIs do dashboard (Patrimônio Δ, Aportes, Despesas vs Teto, Tarefas, Alerta 1, Alerta 2) todos mostram "—".

**Correção no `e5_analyze.py`:** Criar lógica para gerar tarefas e alertas automaticamente:

```python
tarefas = []
alertas = []

if ratios["taxa_endividamento_pct"] > 30:
    alertas.append({"tipo": "critico", "msg": "Endividamento acima de 30%"})
if reserva_emergencia["cobertura_meses"] < 6:
    alertas.append({"tipo": "atencao", "msg": "Reserva abaixo de 6 meses"})
# ... mais regras baseadas nos ratios calculados
```

**Impacto:** Dashboard KPIs saem de "—" para valores reais.

---

## FASE 2 — E6: Eliminar todos os valores hardcoded (P0)

**Por que agora:** Com o E5 produzindo os dados corretos, o E6 precisa lê-los em vez de usar placeholders.

### 2.1 — `build_charts()` — Substituir 11 blocos hardcoded

Cada item abaixo é uma correção pontual na função `build_charts()`:

| Linha | Chart | Valor hardcoded | Deve ler de |
|-------|-------|----------------|-------------|
| 513 | `alocacao_atual` | `[45, 28, 67, 11, 0.4]` | `e4["investimentos"]["tabela_classes"]` |
| 517 | `alocacao_alvo` | `[60, 25, 10, 5]` | `config/definitions.md` ou campo `meta_alocacao` |
| 524 | `yield_imoveis.renda_aluguel_mensal` | `8571` | Calcular: `sum(alugueis_mensais)` do E4 receitas |
| 526 | `yield_imoveis.yield_anual_pct` | `5.3` | Calcular: `(renda_aluguel * 12 / valor_imoveis) * 100` |
| 529-530 | `custos_f1f2` | `27500 + 16500 USD` | `config/definitions.md` seção educação ou life_plan |
| 536-540 | `cenario_cambial.cambio` | `5.0, 5.5, 4.5` | API ou `config/definitions.md` |
| 546-548 | `projecao_if.retornos` | `4%, 5%, 8%` | `e4["goals"]["if_trs"]` ± spread |
| 555 | `renda_passiva.valor_mensal` | `[8571, 1200, 271]` | Calcular de receitas recorrentes passivas |
| 559 | `impostos_pj.renda_tributavel` | `180000` | Calcular de receitas PJ anualizadas |
| 562 | `impostos_pj.economia_ir` | `5940` | Calcular: `limite_pgbl * aliquota_marginal` |
| 580 | `cenarios_mariana` | `[0, 4000, 7000]` | `config/definitions.md` ou life_plan |

**Abordagem recomendada:** Para cada item, a lógica é:
1. Verificar se o E5 JSON já tem o dado calculado
2. Se sim, ler: `e4["campo"]["subcampo"]`
3. Se não (e é configuração), ler de `definitions.md` e criar constantes no topo do arquivo
4. Se não (e precisa de cálculo), criar helper function no E5 ou E6

### 2.2 — `build_investimentos()` — Substituir blocos hardcoded

| Linha | Campo | Valor hardcoded | Deve ler de |
|-------|-------|----------------|-------------|
| 607 | `yield_medio_pct` | `5.2` | Calcular ou "N/D" |
| 608 | `volatilidade_pct` | `8.5` | Calcular ou "N/D" |
| 611-614 | `blocos` | `[320k, 220k, 3190, 306686]` | `e4["investimentos"]["tabela_classes"]` |
| 616 | `cdi_anual` | `11.5` | `config/definitions.md` ou API |

### 2.3 — `build_orcamento_prospectivo()` — Remover variação hardcoded

| Linha | Campo | Valor hardcoded | Deve ler de |
|-------|-------|----------------|-------------|
| 597 | `variacao_pct` | `15.3` | Calcular: desvio padrão das despesas mensais |

### 2.4 — `build_tactical_dashboard()` — Remover P&L hardcoded

| Linha | Campo | Valor hardcoded | Deve ler de |
|-------|-------|----------------|-------------|
| 660 | `monthly_pnl` | `59404` | `e4["fluxo_caixa"]["fluxo_liquido"] / num_meses` |

### 2.5 — `build_contrafluxo_scenarios()` — Parametrizar SELIC

| Linha | Campo | Valor hardcoded | Deve ler de |
|-------|-------|----------------|-------------|
| 648, 651 | `selic_atual`, cenários | `11.5, 10.5, 12.5` | `config/definitions.md` ou constante versionada |

---

## FASE 3 — Alinhar schemas E5 ↔ E6 (P1)

**Por que agora:** Mesmo com dados e leitura dinâmica, se as chaves não batem, os dados não chegam.

### 3.1 — Opção A (recomendada): Adaptar E5 ao que E6 espera

Criar aliases no output do E5 para que as chaves batam com o que E6 lê:

| E6 espera (chave) | E5 produz (chave) | Ação |
|---|---|---|
| `patrimonio.tabela_categorias` | `patrimonio.composicao` | Adicionar alias (Fase 1.1) |
| `fluxo_caixa.tabela_receitas` | `fluxo_caixa.por_fonte` | Gerar formato tabela (Fase 1.2) |
| `investimentos.tabela_classes` | Não produz | Criar (Fase 1.3) |
| `reserva_emergencia.composicao_liquida.cofrinhos_itau` etc. | `composicao_liquida.investimentos_david` etc. | Decompor (Fase 1.4) |
| `endividamento.dividas` (lista) | `endividamento.detalhe` (string) | Criar lista (Fase 1.5) |
| `reserva_emergencia.composicao_liquida.total_liquido` | `reserva_emergencia.total_liquida` | Alias |
| `reserva_emergencia.composicao_liquida.cobertura_meses` | Não produz | Calcular |

### 3.2 — Opção B (alternativa): Adaptar E6 ao que E5 produz

Se preferir não mexer no E5, alterar as funções `build_*` do E6 para ler as chaves que existem.

**Recomendação:** Opção A para tabelas/cards novos, Opção B para campos simples tipo renaming.

---

## FASE 4 — E5: Corrigir cálculos com defeito (P1)

### 4.1 — `caixa_moeda_estrangeira`: calcular por soma, não resíduo

**Problema:** Linhas 310-319 do `e5_analyze.py` calculam por subtração `bruto - tudo_mais`. Qualquer erro de categorização infla ou zera este campo.

**Correção:** Somar diretamente os saldos de contas em moeda estrangeira do baseline:

```python
caixa_moeda_estrangeira = 0.0
for conta in david_bens.get("contas_bancarias", []):
    if is_moeda_estrangeira(conta):  # Wise, BofA, C6 Global
        caixa_moeda_estrangeira += _investimento_valor(conta)
```

### 4.2 — `previdencia_pgbl`: calcular de receitas PJ

**Problema:** Hardcoded como `"N/D"` (linha 746). Mas o E5 já tem `receita_pj` calculada no fluxo de caixa.

**Correção:**

```python
receita_pj_anual = fluxo_caixa["por_fonte"].get("receita_pj", 0) * (12 / num_months)
renda_tributavel = receita_pj_anual * 0.32  # fator pro-labore/lucro presumido
limite_pgbl = renda_tributavel * 0.12
aliquota_marginal = calcular_aliquota_marginal(renda_tributavel)
economia_ir = limite_pgbl * aliquota_marginal

return {
    "renda_tributavel_anual": renda_tributavel,
    "limite_pgbl_anual": limite_pgbl,
    "aporte_mensal_sugerido": limite_pgbl / 12,
    "aliquota_marginal": aliquota_marginal,
    "economia_ir_anual": economia_ir,
    "status": "Calculado"
}
```

### 4.3 — `equilibrio_cerbasi`: calcular percentuais

**Problema:** Linhas 903-906 são texto estático. O report mostra 0% para `% Presente` e `% Futuro`.

**Correção:** Calcular % do orçamento dedicado a presente vs futuro:

```python
despesas_presente = sum(despesas para categorias "presente": moradia, alimentação, transporte, saúde, lazer)
despesas_futuro = sum(despesas para categorias "futuro": investimento, previdência, educação)
total = despesas_presente + despesas_futuro
pct_presente = (despesas_presente / total) * 100
pct_futuro = (despesas_futuro / total) * 100

return {
    "pct_presente": round(pct_presente, 1),
    "pct_futuro": round(pct_futuro, 1),
    "classificacao": classificar_cerbasi(pct_presente, pct_futuro),
    "presente": "Consolidação patrimonial",
    "futuro": "Independência Financeira"
}
```

### 4.4 — `diagnostico_comportamental`: gerar dinamicamente

**Problema:** Hardcoded com 1 item estático. Card mostra linha vazia no HTML.

**Correção:** Gerar a partir dos ratios:

```python
diagnosticos = []
if taxa_poupanca > 25:
    diagnosticos.append({"comportamento": "Disciplina de poupança acima da média", "recomendacao": "Manter"})
if despesa_categorias.get("lazer", 0) / despesa_total > 0.15:
    diagnosticos.append({"comportamento": "Gastos com lazer acima de 15%", "recomendacao": "Avaliar"})
# ... mais regras
```

### 4.5 — `pontos_urgentes`: gerar dinamicamente

**Problema:** Linhas 783-797 são completamente hardcoded (2 tarefas fixas).

**Correção:** Gerar baseado em condições reais:

```python
urgentes = []
if not seguros_encontrados:
    urgentes.append({"prioridade": "P0", "acao": "Contratar seguro de vida", ...})
if taxa_endividamento > 20:
    urgentes.append({"prioridade": "P0", "acao": "Reduzir endividamento", ...})
```

---

## FASE 5 — Validação e re-execução (P2)

### 5.1 — Criar script de validação E5→E6

Antes de re-renderizar, validar que todos os campos esperados existem:

```python
# validate_e5_for_e6.py
REQUIRED_KEYS = {
    "patrimonio.tabela_categorias": list,
    "fluxo_caixa.tabela_receitas": list,
    "investimentos.tabela_classes": list,
    "reserva_emergencia.composicao_liquida.total_liquido": (int, float),
    "reserva_emergencia.composicao_liquida.cobertura_meses": (int, float),
    "endividamento.dividas": list,
    "previdencia_pgbl.renda_tributavel_anual": (int, float),
    "equilibrio_cerbasi.pct_presente": (int, float),
    "equilibrio_cerbasi.pct_futuro": (int, float),
}
```

### 5.2 — Re-executar pipeline

```bash
python scripts/e5_analyze.py          # Regenera E5 JSON
python scripts/e5n_narrativas.py      # Regenera narrativas (se LLM disponível)
python scripts/e6_render.py           # Regenera relatório HTML
```

### 5.3 — Checklist de validação visual do relatório

| Card | Verificação | Critério de aceite |
|------|------------|-------------------|
| Patrimônio por Categoria | Tabela populada | 6 linhas, bruto ~R$ 3.5M |
| Receitas por Fonte | Tabela populada | 7 linhas, total ~R$ 1.3M |
| Investimentos por Classe | Tabela populada | ≥4 linhas, total ~R$ 778K |
| Reserva de Emergência | Liquidez > 0 | Cobertura ~19 meses |
| Composição Liquidez | Tabela populada | ≥2 componentes |
| Endividamento | Detalhe de dívidas | ≥1 linha com saldo |
| PGBL | Valores calculados | Renda tributável > 0, economia IR > 0 |
| Equilíbrio Cerbasi | % Presente e Futuro | Ambos > 0, soma ~100% |
| Dashboard KPIs | Sem "—" | 6 cards com valores |
| Diagnóstico Comportamental | Sem linhas vazias | ≥2 itens |
| Alocação Atual (gráfico) | Dados reais | Não `[45, 28, 67, 11, 0.4]` |
| Renda Passiva (gráfico) | Dados reais | Não `[8571, 1200, 271]` |

---

## ORDEM DE EXECUÇÃO SUGERIDA

| Passo | Fase | Descrição | Tempo est. | Dependência |
|-------|------|-----------|-----------|-------------|
| 1 | 1.1-1.2 | E5: aliases tabela_categorias + tabela_receitas | 15 min | — |
| 2 | 1.3 | E5: investimentos por classe | 30 min | — |
| 3 | 1.4-1.5 | E5: reserva decomposição + endividamento lista | 30 min | — |
| 4 | 4.1 | E5: caixa_moeda_estrangeira por soma | 20 min | — |
| 5 | 4.2-4.3 | E5: PGBL + Cerbasi cálculos | 30 min | — |
| 6 | 4.4-4.5 | E5: diagnóstico + pontos urgentes dinâmicos | 20 min | — |
| 7 | 1.6 | E5: tarefas + alertas automáticos | 20 min | 5, 6 |
| 8 | 2.1-2.5 | E6: eliminar todos os hardcoded | 60 min | 1-7 |
| 9 | 3.1 | E5/E6: verificar alinhamento de schemas | 15 min | 8 |
| 10 | 5.1 | Criar validador E5→E6 | 15 min | 9 |
| 11 | 5.2-5.3 | Re-executar + validação visual | 15 min | 10 |

**Total estimado: 4h30 – 6h**

---

## NOTAS

- **Não hardcodar patrimônio investível:** Sempre calcular como `bruto − residência − veículos` (memória do pipeline).
- **Não hardcodar rentabilidade:** Sem dados reais de performance → "N/D" + alerta (memória do pipeline).
- **ABDO MOHAMED = Dr. Barakat:** Manter mapeamento na categorização.
- **RECEB PAGFOR = QuintoAndar:** No Bradesco Mariana, é aluguel.
- **POMPEIA MOTOS = venda MT09:** Receita de venda de ativo, não PJ.
