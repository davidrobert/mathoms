#!/usr/bin/env python3
"""
E4 Unified Financial Data Analyzer
Extracts monthly revenue and expense data from E4_unified JSON files
Period: May 2025 - March 2026 (11 months)
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_financials():
    # File paths
    base = Path(__file__).resolve().parent.parent
    receitas_path = str(base / "processed" / "E4_unified" / "receitas-4_unified.json")
    despesas_path = str(base / "processed" / "E4_unified" / "despesas-4_unified.json")
    
    # Read files
    try:
        with open(receitas_path, 'r', encoding='utf-8') as f:
            receitas = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Arquivo não encontrado: {receitas_path}")
        print("  Execute e4_categorize.py primeiro.")
        import sys
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON malformado em {receitas_path}: {e}")
        import sys
        sys.exit(1)

    try:
        with open(despesas_path, 'r', encoding='utf-8') as f:
            despesas = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Arquivo não encontrado: {despesas_path}")
        print("  Execute e4_categorize.py primeiro.")
        import sys
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON malformado em {despesas_path}: {e}")
        import sys
        sys.exit(1)
    
    # Derive period dynamically from available data
    all_months = set()
    for fonte_data in receitas.get('por_fonte', {}).values():
        all_months.update(fonte_data.get('por_mes', {}).keys())
    for cat_data in despesas.get('por_categoria', {}).values():
        all_months.update(cat_data.get('por_mes', {}).keys())
    months_list = sorted(all_months) if all_months else []
    
    # ===== RECEITAS ANALYSIS =====
    por_fonte = receitas.get('por_fonte', {})
    # FIXME: Lista hardcoded — manter sincronizada com e4_categorize.py PJ_SOURCE_MAPPING
    pj_sources = ['arvo', 'pj_nao_identificado', 'arbitralis', 'barte', 'brandlovers', 'cnry_canary', 'learntofly']
    non_pj_sources = ['quintoandar']
    unknown_sources = set()

    monthly_receitas = defaultdict(lambda: {'PJ': 0, 'CLT + Alugueis': 0})

    for fonte, fonte_data in por_fonte.items():
        por_mes = fonte_data.get('por_mes', {})
        fonte_lower = fonte.lower()
        if fonte_lower in pj_sources:
            categoria = 'PJ'
        elif fonte_lower in non_pj_sources:
            categoria = 'CLT + Alugueis'
        else:
            unknown_sources.add(fonte)
            categoria = 'CLT + Alugueis'  # default

        for month, value in por_mes.items():
            monthly_receitas[month][categoria] += value

    # Report any sources not in either list
    if unknown_sources:
        print(f"  [WARN] Fontes de receita não classificadas (defaulting para CLT+Alugueis): {unknown_sources}")
    
    # ===== DESPESAS ANALYSIS =====
    por_categoria = despesas.get('por_categoria', {})
    monthly_despesas = {}
    
    for categoria, cat_data in por_categoria.items():
        por_mes = cat_data.get('por_mes', {})
        for month, value in por_mes.items():
            if month not in monthly_despesas:
                monthly_despesas[month] = 0
            monthly_despesas[month] += value
    
    # ===== OUTPUT =====
    period_label = f"{months_list[0]} TO {months_list[-1]}" if months_list else "NO DATA"
    print("=" * 120)
    print(f"E4 UNIFIED FINANCIAL ANALYSIS - {period_label}")
    print("=" * 120)
    
    print(f"\n{'Mês':<12} {'Receita PJ':<18} {'CLT + Alugueis':<18} {'Total Receita':<18} {'Despesas':<18} {'Saldo':<18}")
    print("-" * 110)
    
    total_pj = 0
    total_aluguel = 0
    total_despesas = 0
    
    for month in months_list:
        pj = monthly_receitas[month].get('PJ', 0)
        clt_aluguel = monthly_receitas[month].get('CLT + Alugueis', 0)
        total_rec = pj + clt_aluguel
        desp = monthly_despesas.get(month, 0)
        saldo = total_rec - desp

        total_pj += pj
        total_aluguel += clt_aluguel
        total_despesas += desp
        
        if total_rec > 0 or desp > 0:
            print(f"{month:<12} R$ {pj:>14,.2f}   R$ {clt_aluguel:>14,.2f}   R$ {total_rec:>14,.2f}   R$ {desp:>14,.2f}   R$ {saldo:>14,.2f}")
    
    print("-" * 110)
    total_rec = total_pj + total_aluguel
    saldo_total = total_rec - total_despesas
    print(f"{'TOTAL':<12} R$ {total_pj:>14,.2f}   R$ {total_aluguel:>14,.2f}   R$ {total_rec:>14,.2f}   R$ {total_despesas:>14,.2f}   R$ {saldo_total:>14,.2f}")
    
    # Return as dict for programmatic access
    return {
        'months': months_list,
        'monthly_data': {
            month: {
                'pj': monthly_receitas[month].get('PJ', 0),
                'aluguel': monthly_receitas[month].get('CLT + Alugueis', 0),
                'total_receita': monthly_receitas[month].get('PJ', 0) + monthly_receitas[month].get('CLT + Alugueis', 0),
                'despesas': monthly_despesas.get(month, 0),
            }
            for month in months_list
        },
        'totals': {
            'pj': total_pj,
            'aluguel': total_aluguel,
            'total_receita': total_rec,
            'despesas': total_despesas,
            'saldo': saldo_total
        }
    }

if __name__ == '__main__':
    data = analyze_financials()
