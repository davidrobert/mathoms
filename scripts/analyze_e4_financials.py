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
    with open(receitas_path, 'r', encoding='utf-8') as f:
        receitas = json.load(f)
    
    with open(despesas_path, 'r', encoding='utf-8') as f:
        despesas = json.load(f)
    
    # Define period
    months_list = [
        '2025-05', '2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12',
        '2026-01', '2026-02', '2026-03'
    ]
    
    # ===== RECEITAS ANALYSIS =====
    por_fonte = receitas.get('por_fonte', {})
    pj_sources = ['arvo', 'pj_nao_identificado', 'arbitralis', 'barte', 'brandlovers', 'cnry_canary', 'learntofly']
    non_pj_sources = ['quintoandar']
    
    monthly_receitas = defaultdict(lambda: {'PJ': 0, 'CLT + Alugueis': 0})
    
    for fonte, fonte_data in por_fonte.items():
        por_mes = fonte_data.get('por_mes', {})
        categoria = 'PJ' if fonte in pj_sources else 'CLT + Alugueis'
        
        for month, value in por_mes.items():
            monthly_receitas[month][categoria] += value
    
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
    print("=" * 120)
    print("E3 UNIFIED FINANCIAL ANALYSIS - MAY 2025 TO MARCH 2026")
    print("=" * 120)
    
    print(f"\n{'Mês':<12} {'Receita PJ':<18} {'CLT + Alugueis':<18} {'Total Receita':<18} {'Despesas':<18} {'Saldo':<18}")
    print("-" * 110)
    
    total_pj = 0
    total_aluguel = 0
    total_despesas = 0
    
    for month in months_list:
        pj = monthly_receitas[month].get('PJ', 0)
        aluguel = monthly_receitas[month].get('CLT + Alugueis', 0)
        total_rec = pj + aluguel
        desp = monthly_despesas.get(month, 0)
        saldo = total_rec - desp
        
        total_pj += pj
        total_aluguel += aluguel
        total_despesas += desp
        
        if total_rec > 0 or desp > 0:
            print(f"{month:<12} R$ {pj:>14,.2f}   R$ {aluguel:>14,.2f}   R$ {total_rec:>14,.2f}   R$ {desp:>14,.2f}   R$ {saldo:>14,.2f}")
    
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
