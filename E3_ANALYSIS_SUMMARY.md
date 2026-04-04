# E3 Unified Financial Data Analysis

**Analysis Date:** April 4, 2026  
**Period Analyzed:** May 2025 - March 2026 (11 months)  
**Files Analyzed:** 
- receitas-3_unified.json (14KB)
- despesas-3_unified.json (392KB)

---

## FILE STRUCTURES

### RECEITAS (Revenue) - receitas-3_unified.json

**Top-level structure:**
```json
{
  "tipo": "receitas_unified",
  "data_consolidacao": "2026-04-04",
  "periodo": "2025-05 a 2026-03",
  "moeda": "BRL",
  "total": 1080226.92,
  "count": 91,
  "por_fonte": { ... }
}
```

**Organization:**
- `por_fonte`: Dictionary keyed by revenue source (8 sources total)
  - Each source contains:
    - `total`: Total revenue from that source
    - `count`: Number of transactions
    - `por_mes`: Dictionary with monthly breakdown (month -> amount)
    - `transacoes`: Array of individual transactions

**Sources Identified:**
| Source | Type | Total | Transactions | Months Active |
|--------|------|-------|--------------|---------------|
| Arvo | PJ | R$ 292,666.11 | 8 | Jan-Feb 2026 |
| pj_nao_identificado | PJ | R$ 504,505.67 | 33 | Jan-Mar 2026 |
| Arbitralis | PJ | R$ 5,500.00 | 2 | Feb-Mar 2026 |
| Barte | PJ | R$ 40,000.00 | 2 | Jun, Sep 2026 |
| Brand Lovers | PJ | R$ 50,000.00 | 2 | Jan, Mar 2026 |
| CNRY Canary | PJ | R$ 120,000.00 | 3 | Jul-Aug 2026 |
| Learn to Fly | PJ | R$ 1,750.00 | 1 | Mar 2026 |
| **QuintoAndar** | **Rental** | **R$ 65,805.14** | **40** | **May 2025 - Mar 2026** |

---

### DESPESAS (Expenses) - despesas-3_unified.json

**Top-level structure:**
```json
{
  "tipo": "despesas_unified",
  "data_consolidacao": "2026-04-04",
  "periodo": "2025-05 a 2026-03",
  "moeda": "BRL",
  "total": 298581.6,
  "count": 1032,
  "por_categoria": { ... }
}
```

**Organization:**
- `por_categoria`: Dictionary keyed by expense category (16 categories)
  - Each category contains:
    - `total`: Total expenses in that category
    - `count`: Number of transactions
    - `por_mes`: Dictionary with monthly breakdown
    - `transacoes`: Array of individual transactions

**Categories:**
| Category | Total | Transactions |
|----------|-------|--------------|
| Unidentified | R$ 39,474.55 | 428 |
| Wishes Fund | R$ 73,525.72 | 108 |
| Health | R$ 58,380.07 | 37 |
| Leisure/Travel | R$ 42,796.81 | 44 |
| Food | R$ 21,141.77 | 147 |
| Home Improvement | R$ 14,719.56 | 32 |
| Transport | R$ 14,127.90 | 78 |
| Subscriptions | R$ 9,714.12 | 54 |
| Clothing | R$ 8,321.64 | 6 |
| Insurance | R$ 5,337.90 | 1 |
| Financial | R$ 4,756.43 | 85 |
| Education | R$ 3,197.00 | 1 |
| Domestic Services | R$ 2,489.02 | 7 |
| Housing | R$ 432.21 | 2 |
| Family Support | R$ 89.90 | 1 |
| PJ Taxes | R$ 77.00 | 1 |
| **TOTAL** | **R$ 298,581.60** | **1,032** |

---

## MONTHLY REVENUE & EXPENSE SUMMARY

### For Chart Use - Three Categories:

```
Mês        Receita PJ      CLT + Alugueis   Total Receita   Despesas      Saldo
─────────────────────────────────────────────────────────────────────────────
2025-05    R$        0.00  R$      1,698.39  R$      1,698.39  R$       128.64  R$      1,569.75
2025-06    R$        0.00  R$      3,297.97  R$      3,297.97  R$     1,209.27  R$      2,088.70
2025-07    R$        0.00  R$      6,447.02  R$      6,447.02  R$     5,354.45  R$      1,092.57
2025-08    R$        0.00  R$      6,452.36  R$      6,452.36  R$       735.10  R$      5,717.26
2025-09    R$        0.00  R$      6,844.20  R$      6,844.20  R$       602.94  R$      6,241.26
2025-10    R$        0.00  R$      6,844.20  R$      6,844.20  R$     1,297.05  R$      5,547.15
2025-11    R$        0.00  R$      6,844.20  R$      6,844.20  R$       581.44  R$      6,262.76
2025-12    R$        0.00  R$      6,844.20  R$      6,844.20  R$         0.00  R$      6,844.20
2026-01    R$   165,008.77  R$      6,844.20  R$    171,852.97  R$    32,519.33  R$    139,333.64
2026-02    R$   100,428.77  R$      6,844.20  R$    107,272.97  R$    19,161.49  R$     88,111.48
2026-03    R$    94,750.00  R$      6,844.20  R$    101,594.20  R$    30,171.18  R$     71,423.02
─────────────────────────────────────────────────────────────────────────────
TOTAL      R$   360,187.54  R$     65,805.14  R$    425,992.68  R$    91,760.89  R$    334,231.79
```

---

## KEY FINDINGS FOR CHART

### Revenue Pattern:
1. **May-Dec 2025:** Only QuintoAndar (rental) income = ~R$ 6,844/month
2. **Jan-Mar 2026:** PJ income starts in January with spike:
   - Jan: R$ 165,008.77 (highest PJ month)
   - Feb: R$ 100,428.77
   - Mar: R$ 94,750.00
3. **Total PJ income:** R$ 360,187.54 (concentrated in 3 months)
4. **Total rental income (constant):** R$ 65,805.14 (11 months)

### Expense Pattern:
1. **May-Dec 2025:** Very low expenses (R$ 128-5,354/month)
   - Highest: July 2025 at R$ 5,354.45
2. **Jan-Mar 2026:** High expenses during PJ income:
   - Jan: R$ 32,519.33
   - Feb: R$ 19,161.49
   - Mar: R$ 30,171.18
3. **Total expenses:** R$ 91,760.89
4. **No expenses recorded for Dec 2025**

### Net Position:
- **Total Surplus:** R$ 334,231.79
- **Highest monthly surplus:** Jan 2026 at R$ 139,333.64
- **Consistent positive balance:** Every month shows net positive

---

## PYTHON SCRIPT LOCATION

Script saved for future use:
```
/sessions/nifty-awesome-keller/mnt/Financas Familia/financas-familia/scripts/analyze_e3_financials.py
```

**Usage:**
```bash
python3 analyze_e3_financials.py
```

The script returns both printed output and a dictionary with:
- `months`: List of periods
- `monthly_data`: Detailed breakdown per month
- `totals`: Aggregate totals

---

## NOTES FOR CHART BUILDING

1. **X-axis:** Months (May 2025 - March 2026)
2. **Y-axis:** Amount in BRL
3. **Series:**
   - Receita PJ (stacked bar or separate line)
   - CLT + Alugueis (stacked bar or separate line)
   - Despesas (separate line or bar for reference)
4. **Missing months in data:** Dec 2025 has no expenses; check if this is data entry gap
5. **Chart type recommendation:** Stacked column chart for revenues + line chart overlay for expenses

