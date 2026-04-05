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

**⚠️ ERRO COMUM:** Incluir apenas imóveis de David. Mariana possui 2 apartamentos de investimento
que DEVEM ser contados aqui.

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

**Regra:** Categoria RESIDUAL. Calculada por diferença.

**Fórmula:**
```
caixa_moeda = patrimonio.bruto − (cat_1 + cat_2 + cat_3 + cat_4 + cat_5 + cat_7)
```

**Deve conter apenas:**
- Contas corrente puras (saldo em CC sem aplicação)
- Moeda estrangeira em espécie ou depósito
- Qualquer ativo não classificado nas outras 6 categorias

**⚠️ VALIDAÇÃO:** Se `caixa_moeda` > 5% do bruto, o E4 DEVE emitir um warning no `qa_log.md`
solicitando revisão manual — pode indicar que ativos de investimento foram classificados erroneamente
como caixa. Valor esperado típico: 1-3% do bruto (contas corrente + USD + resíduos).

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

## FÓRMULAS DERIVADAS (recapitulação de definitions.md)

```
patrimonio.bruto         = SUM(total_bens de cada membro)
patrimonio.investivel    = bruto − residencia − veiculos
patrimonio.liquido       = bruto − dividas
patrimonio.residencia    = cat_1
patrimonio.imoveis_investimento = cat_2
patrimonio.investimentos_david  = cat_3
patrimonio.investimentos_mariana = cat_4
patrimonio.caixa_moeda_estrangeira = cat_6
```

---

## INVARIANTES DE VALIDAÇÃO (E4 DEVE verificar)

1. `SUM(composicao[].valor) == patrimonio.bruto` (diferença tolerada: ≤ R$ 1,00)
2. `SUM(composicao[].pct_bruto) == 100.0%`
3. `patrimonio.investivel < patrimonio.bruto`
4. `patrimonio.investivel == bruto − cat_1 − cat_7`
5. **Os campos top-level do E4 (`patrimonio.investimentos_david`, etc.) DEVEM ser idênticos aos valores correspondentes em `composicao[]`** — proibido ter dois conjuntos de números divergentes
6. `cat_6 (Caixa + ME) < 5% do bruto` → warning se violado (vide regra da categoria 6)

---

## TÍTULO DO CARD NO RELATÓRIO

O canvas `chart-patrimonio-doughnut` deve ter o título **"Distribuição Patrimonial"**
(não "Patrimônio Doughnut" nem "Patrimonio Doughnut").

---

## HISTÓRICO

| Data | Mudança | Motivo |
|---|---|---|
| 2026-04-04 | Criação do arquivo v1.0 | Corrigir erros de classificação no E4: imóveis Mariana faltando, contas investimento (CDB/RDB) classificadas como Caixa, inconsistência entre campos top-level e composicao |
