# Regras de Classificação — Composição Patrimonial (Doughnut)
## Versão: 1.0 — abr/2026

---

## CONTEXTO

Este arquivo define as regras **determinísticas** para classificar cada ativo do baseline patrimonial
(`patrimonio-3_unified.json`) nas 7 categorias da composição usada no gráfico "Distribuição Patrimonial"
(canvas `chart-patrimonio-doughnut`) e nos campos `patrimonio.composicao[]` do E4.

**Problema resolvido:** versões anteriores do E4 classificavam ativos de forma inconsistente porque
as regras no `definitions.md` eram ambíguas em dois pontos críticos:
1. "E4.imoveis" não explicitava que inclui imóveis de TODOS os membros (David + Mariana)
2. "baseline.investimentos[]" não incluía contas bancárias de investimento (CDB, RDB, Renda Fixa),
   fazendo esses ativos cair no residual "Caixa + Moeda Estrangeira" e inflando esse bucket

---

## AS 7 CATEGORIAS (ordem canônica)

| # | Categoria | Label no gráfico |
|---|---|---|
| 1 | Residência própria | Residência própria |
| 2 | Imóveis investimento | Imóveis investimento |
| 3 | Investimentos David | Investimentos David |
| 4 | Investimentos Mariana | Investimentos Mariana |
| 5 | Criptoativos | Criptoativos |
| 6 | Caixa + Moeda Estrangeira | Caixa + Moeda Estrangeira |
| 7 | Veículos | Veículos |

---

## REGRAS DE CLASSIFICAÇÃO POR CATEGORIA

### 1. Residência própria

**Regra:** imóvel identificado como moradia principal da família.

**Fonte:** `baseline.david.imoveis[]` → item com description contendo "TASSO DA SILVEIRA"

**Valor:** `valor_31_12_ano_base` do imóvel identificado.

**Notas:**
- Sempre exatamente 1 imóvel nesta categoria
- Atualmente: Casa Tasso da Silveira (996.821,46 em 31/12/2023)

---

### 2. Imóveis investimento

**Regra:** TODOS os imóveis de TODOS os membros, EXCETO a residência principal (categoria 1).

**Fórmula:**
```
imoveis_investimento = SUM(david.imoveis[].valor_31_12_ano_base)
                     + SUM(mariana.imoveis[].valor_31_12_ano_base)
                     − residencia_propria
```

**Inclui explicitamente:**
- David: Benedito Calixto (350.000), Major Freire (212.706,24), Leonardo da Vinci (80.000)
- Mariana: Living Concept (270.000), Living Wish (530.000)

**⚠️ ERRO COMUM:** Incluir apenas imóveis de David. Mariana possui 2 apartamentos de investimento que DEVEM ser contados aqui.

---

### 3. Investimentos David

**Regra:** TODOS os ativos financeiros de David que geram rendimento ou têm prazo de aplicação.
Inclui tanto `baseline.david.investimentos[]` quanto `baseline.david.contas_bancarias[]` de tipo investimento.

**Inclui:**
- `investimentos[]` com `valor_31_12_ano_base > 0` (fundos de investimento, ações, CDBs, CRAs)
  - EXCETO: Hashdex crypto (que fica aqui mesmo — é fundo regulado FIC FIM, NÃO crypto direta)
- `contas_bancarias[]` cujo `tipo` contenha qualquer um dos seguintes termos (case-insensitive):
  - `RDB`, `CDB`, `CDP`, `Renda Fixa`, `Investimento`, `Aplicacao`, `Poupança`
  - Inclui também: saldo em conta de corretora (Rico/XP)

**Exclui de investimentos (vai para Caixa — categoria 6):**
- `contas_bancarias[]` cujo `tipo` contenha `Conta Corrente` (sem "Investimento" no mesmo campo)
- `contas_bancarias[]` cujo `tipo` contenha `Moeda Estrangeira`

**Termos de matching para contas_bancarias (campo `tipo`):**

| Padrão no campo `tipo` | Classificação | Exemplo |
|---|---|---|
| `Aplicacao RDB/CDP` | ✅ Investimento | Itaú Personnalité |
| `Aplicacao CDB` | ✅ Investimento | Santander |
| `Aplicacao Renda Fixa` | ✅ Investimento | C6 |
| `RDB` | ✅ Investimento | Nubank |
| `Conta Investimento` | ✅ Investimento | PicPay |
| `Conta Corrente Investimento` | ✅ Investimento | Banco 336 (C6 PJ) |
| `Saldo em Conta` (corretora) | ✅ Investimento | Rico/XP |
| `Poupança` | ✅ Investimento | Bradesco, Caixa |
| `Conta Corrente` | ❌ → Caixa | Caixa, Itaú |
| `Moeda Estrangeira` | ❌ → Caixa + ME | USD, Cayman |

---

### 4. Investimentos Mariana

**Regra:** TODOS os ativos financeiros de Mariana (fundos + CDBs + CRAs no BTG).
Mesma lógica da categoria 3, aplicada ao baseline de Mariana.

**Inclui:**
- `baseline.mariana.investimentos[]` com `valor_31_12_ano_base > 0`
- `baseline.mariana.contas_bancarias[]` de tipo investimento (mesma tabela de matching acima)

**Notas:**
- Atualmente todas as contas bancárias de Mariana estão fechadas (valor 0), então na prática
  esta categoria = sum dos investimentos BTG
- Se Mariana abrir contas de investimento no futuro, elas entram aqui automaticamente pela regra

---

### 5. Criptoativos

**Regra:** Crypto direta (BTC, ETH, ADA, AXS, etc.) mantida em exchanges.

**Fonte:** Extratos Binance processados em E2 → saldo consolidado em BRL.

**NÃO inclui:**
- Fundos crypto regulados (ex: Hashdex NASDAQ Crypto Index FIC FIM) → esses vão para Investimentos David (categoria 3)

**Notas:**
- Se não houver extratos Binance processados, usar valor 0
- Fundos que contêm "crypto" ou "cripto" no nome mas são FIC/FIM/FIA regulados NÃO são criptoativos

---

### 6. Caixa + Moeda Estrangeira

**Regra:** Calculada a partir dos **saldos finais do E3 reconciliado** (contas correntes + moeda estrangeira).

**Quando `fonte_investimentos = "posicoes_atuais"` (fluxo normal):**

O E5 lê todos os arquivos `*-3_reconciled.json` em `processed/E3_reconciled/` e soma os `saldo_final`
das contas classificadas como caixa ou moeda estrangeira:

| Tipo de conta (E3)               | Classificação       | Exemplo                      |
|-----------------------------------|---------------------|------------------------------|
| `extratoconta` BRL (banco trad.)  | ✅ Caixa             | Itaú CC, Santander CC        |
| `extratoconta` USD/EUR            | ✅ Moeda Estrangeira | Bank of America, C6 Global   |
| `extratocontausd` / `extratocontaeur` | ✅ Moeda Estrangeira | Wise USD                |
| `extratocontabrl`                 | ✅ Caixa             | Wise BRL                     |
| `extratopoupanca`                 | ❌ → Investimentos   | Bradesco Poupança            |
| `extratocontapj`                  | ❌ → Investimentos   | C6 PJ (Banco 336)           |
| `*fatura*`                        | ❌ → skip            | faturas de cartão            |
| Corretora/fintech invest.         | ❌ → Investimentos   | BTG, Rico, PicPay, Binance   |

Contas em moeda estrangeira são convertidas para BRL usando `config/taxas.json`
(`cambio_usd_brl`, `cambio_eur_brl`).

**Quando `fonte_investimentos = "irpf"` (fallback):**

Mantém a fórmula residual original:
```
caixa_moeda = total_bens_irpf − (cat_1 + cat_2 + cat_3 + cat_4 + cat_7)
```

**⚠️ VALIDAÇÃO:** Se `caixa_moeda` > 5% do bruto, o E5 DEVE emitir um warning
solicitando revisão manual. Valor esperado típico: 1-3% do bruto.

---

### 7. Veículos

**Regra:** Soma de todos os veículos de todos os membros.

**Fórmula:**
```
veiculos = SUM(david.veiculos[].valor_31_12_ano_base)
         + SUM(mariana.veiculos[].valor_31_12_ano_base)
```

**Notas:**
- Mariana atualmente não possui veículos no baseline
- Inclui motos, carros, e qualquer veículo declarado no IRPF

---

## FÓRMULAS DERIVADAS (cross-ref de definitions.md §FÓRMULAS PATRIMONIAIS)

```
patrimonio.bruto                 = cat_1 + cat_2 + cat_3 + cat_4 + cat_5 + cat_6 + cat_7
patrimonio.investivel_financeiro = cat_3 + cat_4 + cat_5 + cat_6
patrimonio.investivel_total      = bruto − cat_1 − cat_7
patrimonio.investivel_efetivo    = investivel_financeiro
                                 + (cat_2 if workspace.imoveis_no_if else 0)
patrimonio.liquido               = bruto − dividas
patrimonio.residencia            = cat_1
patrimonio.imoveis_investimento  = cat_2
patrimonio.investimentos_david   = cat_3
patrimonio.investimentos_mariana = cat_4
patrimonio.criptoativos          = cat_5
patrimonio.caixa_moeda_estrangeira = cat_6  (E3 saldos CC + FX)
patrimonio.veiculos              = cat_7
```

**cat_5 sempre presente** mesmo com saldo zero — emitir
`{valor: 0, pct_bruto: 0.0}` para preservar invariantes da UI e do schema.

> **Cross-ref:** este bloco é espelho de
> `definitions.md §FÓRMULAS PATRIMONIAIS`. Mudar um exige mudar o outro
> no mesmo commit.

---

## INVARIANTES DE VALIDAÇÃO (E4 DEVE verificar)

1. `SUM(composicao[].valor) == patrimonio.bruto` (diferença tolerada: ≤ R$ 1,00)
2. `SUM(composicao[].pct_bruto) == 100.0%`
3. `patrimonio.investivel_total < patrimonio.bruto` (sempre — bruto inclui residência e veículos que estão fora do investível total)
4. `patrimonio.investivel_total == bruto − cat_1 − cat_7`
5. `patrimonio.investivel_financeiro <= patrimonio.investivel_total` (financeiro = subset do total que exclui imóveis investimento)
6. `patrimonio.investivel_financeiro == cat_3 + cat_4 + cat_5 + cat_6` (definição direta)
7. **Os campos top-level do E4 (`patrimonio.investimentos_david`, etc.) DEVEM ser idênticos aos valores correspondentes em `composicao[]`** — proibido ter dois conjuntos de números divergentes.
8. `cat_6 (Caixa + ME) < 5% do bruto` → warning se violado (vide regra da categoria 6).
9. **Anti-dupla-contagem ([ADR-142](../docs/DECISIONS.md#adr-142--toggle-imoveis_no_if-em-pipelinejson--invariante-anti-dupla-contagem)):**
   se `pipeline.json:patrimonio_composicao.imoveis_no_if = true` e há
   `goal.if.inputs.renda_passiva_atual_mensal_brl > 0`, então o valor
   declarado **deve excluir** aluguéis líquidos de cat_2 (já contabilizados
   no `investivel_efetivo`). Caso contrário, dupla contagem do patrimônio
   imobiliário. E4 emite warning quando `imoveis_no_if=true` e
   `renda_passiva_atual > sum(aluguéis_categorizados_recorrentes)`.

---

## TÍTULO DO CARD NO RELATÓRIO

O canvas `chart-patrimonio-doughnut` deve ter o título **"Distribuição Patrimonial"**
(não "Patrimônio Doughnut" nem "Patrimonio Doughnut").

---

## HISTÓRICO

| Data | Mudança | Motivo |
|---|---|---|
| 2026-04-04 | Criação do arquivo v1.0 | Corrigir erros de classificação no E4: imóveis Mariana faltando, contas investimento (CDB/RDB) classificadas como Caixa, inconsistência entre campos top-level e composicao |
| 2026-04-10 | v1.1 — Cat 6 via E3 saldos | Caixa+ME agora lido dos saldo_final do E3 reconciliado (CC + FX) em vez de fórmula residual que dava sempre zero quando posicoes_atuais ativo. Câmbio via taxas.json. |
