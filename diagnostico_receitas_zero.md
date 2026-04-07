# Diagnóstico: Causa Raiz das Receitas Zeradas

**Data:** 2026-04-07
**Investigado por:** Claude Sonnet 4.6
**Status atual:** `receita_total: R$0,00` em `E5_analysis/analise_financeira-5_analysis.json`

---

## Resumo Executivo

O pipeline reporta R$0 em receitas porque **261 transações de crédito (R$1.184.353,65) estão sendo categorizadas como despesas** no estágio E4. A causa raiz é uma única linha de código em `scripts/e4_categorize.py` que compara `tipo == "credito"` (sem acento), enquanto o E3 preserva `"tipo": "crédito"` (com acento, vindo do E2). Há também 6 bugs secundários que afetam a qualidade da categorização após a correção principal.

---

## Mapeamento Completo dos Pontos de Falha

### BUG #1 — CRÍTICO (causa raiz do R$0)

**Arquivo:** `scripts/e4_categorize.py`, linha 313
**Caminho:** E3 → E4

```python
# CÓDIGO ATUAL (com bug):
if tipo == "credito":          # ← FALHA: "crédito" ≠ "credito"
    category = categorize_income(...)
else:                          # ← TODOS os 261 créditos caem aqui
    category = categorize_expense(...)
```

**Raiz técnica:**

| Estágio | Campo tipo nas transações |
|---------|--------------------------|
| E2 LLM gera | `"tipo": "crédito"` (com acento, UTF-8) |
| E3 preserva | `"tipo": "crédito"` (inalterado) |
| E4 compara | `if tipo == "credito"` (sem acento) → **FALHA** |

O mesmo arquivo já tem a função `normalize_text()` (linha 64) que remove acentos via `unicodedata.normalize('NFD')`, mas ela **não é usada** na comparação de tipo.

**Impacto total:**

| Categoria (perdida) | Transações | Valor |
|--------------------|-----------|-------|
| receita_pj | 39 txs | R$679.092,10 |
| receita_clt | 26 txs | R$110.529,57 |
| receita_investimento | 60 txs | R$5.350,32 |
| receita_aluguel | 6 txs | R$10.266,30 |
| receita_resgate | 15 txs | R$7,92 |
| outras_receitas (sem keyword) | 115 txs | R$379.107,44 |
| **TOTAL** | **261 txs** | **R$1.184.353,65** |

**Correção:**
```python
# OPÇÃO A — simples e explícita:
if tipo in ("credito", "crédito"):

# OPÇÃO B — usando normalize_text() já existente:
if normalize_text(tipo) == "CREDITO":
```

---

### BUG #2 — MÉDIO (qualidade de categorização)

**Arquivo:** `config/categorization.json` — faltam keywords em `income_keywords`
**Caminho:** E4 → categorização incorreta após fix do Bug #1

Após corrigir o Bug #1, 105 transações de crédito (R$312.952,78) não terão keyword correspondente e cairão em `outras_receitas` em vez das categorias corretas:

#### 2a. `Saldo Invest Fácil` → deveria ser `receita_investimento`
- **Qtd:** 82 transações | **Valor:** R$252.739,06
- **Descrição:** Resgate diário do produto Bradesco Invest Fácil
- **Correção:** Adicionar `"Saldo Invest Fácil"` a `income_keywords.receita_investimento`

#### 2b. `SALÁRIO DEPOSITO` → deveria ser `receita_clt`
- **Qtd:** 3 transações | **Valor:** R$36.000,00 (R$12.000 × 3 meses, C6 Bank)
- **Descrição:** Depósito de salário CLT de Mariana no C6 Bank
- **Correção:** Adicionar `"SALÁRIO DEPOSITO"` a `income_keywords.receita_clt`

#### 2c. `Pix recebido de LEARNTOEIV DESENVOLVIMEN` → deveria ser `receita_pj`
- **Qtd:** 2 transações | **Valor:** R$2.250,00
- **Descrição:** Aparentemente receita de cliente PJ
- **Correção:** Verificar origem e adicionar keyword em `income_keywords.receita_pj`

#### 2d. `Transf C6 Conta Global Líquido` → deveria ser transferência interna
- **Qtd:** 4 transações | **Valor:** R$1.100,00
- **Descrição:** Transferência entre C6 Global e C6 conta corrente = interno
- **Correção:** Adicionar `"Transf C6 Conta Global"` a `internal_transfer_patterns`

---

### BUG #3 — MÉDIO (filtro incorreto de receitas de investimento)

**Arquivo:** `config/categorization.json` — `internal_transfer_patterns`
**Caminho:** E4 → `is_internal_transfer()` filtra receitas legítimas

O padrão `"LIQ BOLSA"` está na lista de transferências internas, mas representa **créditos de liquidação de posições na bolsa** (BTG Pactual) — são receitas de investimento, não transferências internas.

- **Qtd:** 7 transações | **Valor:** R$5.821,66
- **Correção:**
  1. Remover `"LIQ BOLSA"` de `internal_transfer_patterns`
  2. Adicionar `"LIQ BOLSA"` a `income_keywords.receita_investimento`

---

### BUG #4 — MÉDIO (transferências Wise não detectadas como internas)

**Arquivo:** `config/categorization.json` — `internal_transfer_patterns`
**Caminho:** E4 → créditos Wise viram falsas receitas

`"Dinheiro adicionado à conta"` é a descrição do Wise quando David transfere dinheiro do Bradesco para a conta Wise (carregamento interno). Sem padrão correspondente, 6 dessas transações viram `outras_receitas`.

- **Qtd:** 6 transações | **Valor:** R$15.000,00
- **Correção:** Adicionar `"Dinheiro adicionado à conta"` a `internal_transfer_patterns`

---

### BUG #5 — MÉDIO (moeda errada em E3 para contas Wise USD)

**Arquivo:** `scripts/e3_reconcile.py`, função `reconcile_account()`, linha ~651
**Caminho:** E2 → E3

A função `get_account_key()` detecta corretamente a moeda USD da Wise (lê `conta.moeda`), mas `reconcile_account()` usa apenas `data.get('moeda', '')` (campo top-level, ausente) e ao falhar, define `moeda = 'BRL'` como default.

```python
# CÓDIGO ATUAL em reconcile_account():
moeda = first_data.get('moeda', '').strip()
if not moeda:
    moeda = 'BRL'   # ← BUG: ignora conta.moeda

# get_account_key() FAZ corretamente:
moeda = data.get('moeda', '').strip()
if not moeda:
    conta = data.get('conta', {})
    moeda = conta.get('moeda', 'BRL')  # ← correto
```

**Resultado:** 31 transações Wise (11 créditos, valores em USD) são gravadas no E3 como `moeda=BRL`, causando super-contagem de receitas quando convertidas para R$ no E5.

**Correção:** Replicar a lógica de `get_account_key()` em `reconcile_account()`:
```python
moeda = first_data.get('moeda', '').strip()
if not moeda:
    conta = first_data.get('conta', {})
    if isinstance(conta, dict):
        moeda = conta.get('moeda', 'BRL').strip()
    if not moeda:
        moeda = 'BRL'
```

---

### BUG #6 — BAIXO (E2 LLM não define campo `banco`)

**Arquivo:** Saída do LLM E2 (todos os extratos, exceto faturas)
**Caminho:** E2 → E3

Todos os arquivos `*-2_extract.json` de extrato de conta usam `"instituicao"` em vez de `"banco"`. O E3 compensa corretamente via fallback, mas gera inconsistências de nomenclatura:

| E2 `instituicao` | E3 `banco` resultante |
|-----------------|----------------------|
| `"bradesco"` | `"bradesco"` (minúsculo) |
| `"BTG Pactual"` | `"BTG Pactual"` (misto) |
| `"c6bank"` | `"c6bank"` (sem espaço) |
| `"Wise"` | `"Wise"` (maiúsculo) |

**Impacto:** Nenhum dado perdido (E3 compensa), mas nomes de banco inconsistentes em E4/E5/E6.
**Correção:** Atualizar prompt E2 para incluir campo `banco` padronizado nos extratos.

---

### BUG #7 — BAIXO (datas ausentes em filenames do E3)

**Arquivo:** `scripts/e3_reconcile.py`, função `reconcile_account()`, linha ~681
**Caminho:** E3 → nomes de arquivo

```python
# CÓDIGO ATUAL (usa chave errada):
periodo_inicio = sorted_group[0][1].get('periodo', {}).get('inicio', '')
#                                                           ^^^^^^ deveria ser 'data_inicio'

# E2 usa:
"periodo": {"data_inicio": "2025-01-01", "data_fim": "2026-03-29"}
```

Todos os 14 arquivos E3 têm `__` no nome (ex: `bradesco_extratoconta_BRL__-3_reconciled.json`) porque o range de datas não é encontrado.

**Impacto:** Apenas estético — nomes sem datas. Dados internos corretos.
**Correção:** `get('data_inicio', '')` e `get('data_fim', '')`

---

## Sumário das Correções Prioritizadas

| # | Arquivo | Severidade | Impacto Financeiro | Esforço |
|---|---------|------------|-------------------|---------|
| 1 | `scripts/e4_categorize.py` linha 313 | **CRÍTICO** | R$1.184.353,65 (100% receitas) | 1 linha |
| 2a | `config/categorization.json` — adicionar `Saldo Invest Fácil` | MÉDIO | R$252.739,06 mal-classificado | 1 keyword |
| 2b | `config/categorization.json` — adicionar `SALÁRIO DEPOSITO` | MÉDIO | R$36.000,00 mal-classificado | 1 keyword |
| 3 | `config/categorization.json` — mover `LIQ BOLSA` | MÉDIO | R$5.821,66 perdido | 2 linhas config |
| 4 | `config/categorization.json` — adicionar padrão Wise | MÉDIO | R$15.000,00 falsa receita | 1 padrão |
| 5 | `scripts/e3_reconcile.py` — moeda Wise USD | MÉDIO | 11 créditos USD como BRL | 5 linhas |
| 6 | E2 prompt — campo `banco` | BAIXO | Nenhum dado perdido | Prompt |
| 7 | `scripts/e3_reconcile.py` — datas nos filenames | BAIXO | Apenas estético | 2 linhas |

---

## Receitas Esperadas Após Todas as Correções

| Categoria | Valor Estimado | Notas |
|-----------|---------------|-------|
| receita_pj | R$681.342,10 | ARVO, BRANDLOVERS, LEARNTOEIV |
| receita_clt | R$146.529,57 | Einstein (Mariana) + KIWIFY + SALÁRIO DEPOSITO |
| receita_investimento | R$263.911,30 | Invest Fácil + Rendimentos + LIQ BOLSA BTG |
| receita_aluguel | R$10.266,30 | QuintoAndar (SISPAG GRPQA) |
| receita_resgate | R$7,92 | Resgates menores |
| outras_receitas | ~R$5.000 | Wise Recebeu dinheiro + PIX outros |
| **TOTAL ESTIMADO** | **~R$1.107.000** | vs R$0 atual |

---

## Fluxo de Dados (Rastreamento do Bug #1)

```
E2 LLM (extrato)
  └─ transacoes[].tipo = "crédito"  (com acento, correto)

E3 reconcile (e3_reconcile.py)
  └─ Preserva tipo = "crédito"  (sem transformação, correto)

E4 categorize (e4_categorize.py)
  └─ tipo = tx.get("tipo")  → "crédito"
  └─ if tipo == "credito":  ← FALHA — acento mismatch!
  └─ else:  ← TODOS os 261 créditos caem aqui
       └─ category = categorize_expense(...)
       └─ despesas.append(...)  ← receitas viram despesas!

E4 output (receitas-4_unified.json)
  └─ "total_transacoes": 0
  └─ "total_geral": 0

E5 analyze (e5_analyze.py)
  └─ receita_total = receitas.get("total_geral", 0) = 0.0

E6 render (relatório HTML)
  └─ Exibe R$0 em todas as métricas de receita
```
