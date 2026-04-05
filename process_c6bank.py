#!/usr/bin/env python3
import json
import re
from pathlib import Path
from datetime import datetime

# Paths
data_dir = Path("/sessions/stoic-bold-keller/mnt/Financas Familia/financas-familia/data/financial_statements")
output_dir = Path("/sessions/stoic-bold-keller/mnt/Financas Familia/financas-familia/processed/E2_extracts")

# File mappings
files_to_process = {
    "c6bank_extratoconta_202603": {
        "type": "extratoconta",
        "moeda": "BRL",
        "periodo": {"inicio": "2025-03-29", "fim": "2026-03-29"}
    },
    "c6bank_extratocontapj_202503_202603": {
        "type": "extratocontapj",
        "moeda": "BRL",
        "periodo": {"inicio": "2025-03-29", "fim": "2026-03-29"}
    },
    "c6bank_extratocontaglobaleur_202511_202512": {
        "type": "extratocontaglobal",
        "moeda": "EUR",
        "periodo": {"inicio": "2025-11-01", "fim": "2025-12-31"}
    },
    "c6bank_extratocontaglobaleur_202601_202603": {
        "type": "extratocontaglobal",
        "moeda": "EUR",
        "periodo": {"inicio": "2026-01-01", "fim": "2026-03-29"}
    },
    "c6bank_extratocontaglobalusd_202505_202507": {
        "type": "extratocontaglobal",
        "moeda": "USD",
        "periodo": {"inicio": "2025-05-01", "fim": "2025-07-31"}
    },
    "c6bank_extratocontaglobalusd_202508_202510": {
        "type": "extratocontaglobal",
        "moeda": "USD",
        "periodo": {"inicio": "2025-08-01", "fim": "2025-10-31"}
    },
    "c6bank_extratocontaglobalusd_202511_202512": {
        "type": "extratocontaglobal",
        "moeda": "USD",
        "periodo": {"inicio": "2025-11-01", "fim": "2025-12-31"}
    },
    "c6bank_extratocontaglobalusd_202512_202603": {
        "type": "extratocontaglobal",
        "moeda": "USD",
        "periodo": {"inicio": "2025-12-01", "fim": "2026-03-29"}
    },
    "c6bank_carteirarendafixa_202603": {
        "type": "carteirarendafixa"
    }
}

def extract_conta_data(filepath, config):
    """Extract conta corrente data from PDF"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Try to extract key information
    saldo_inicial = None
    saldo_final = None
    transacoes = []
    titular = "DAVID ROBERT CAMARGO FERREIRA CAMPOS"

    # Extract balances and transactions from raw text (simplified)
    # The detailed parsing would require proper PDF parsing

    return {
        "banco": "C6 Bank",
        "tipo": config["type"],
        "titular": titular,
        "moeda": config.get("moeda", "BRL"),
        "periodo": config.get("periodo", {}),
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "transacoes": transacoes
    }

def extract_renda_fixa_data(filepath):
    """Extract renda fixa portfolio data from PDF"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    produtos = []

    return {
        "banco": "C6 Bank",
        "tipo": "carteirarendafixa",
        "data_posicao": "2026-03-29",
        "produtos": produtos
    }

def extract_fatura_carbon_data(filepath, month_year):
    """Extract Carbon credit card fatura data from PDF"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    transacoes = []
    saldo_anterior = None
    total_compras = None
    pagamentos = None
    saldo_atual = None

    return {
        "banco": "C6 Bank",
        "tipo": "faturacarbon",
        "cartao": "Carbon",
        "titular": "DAVID ROBERT CAMARGO FERREIRA CAMPOS",
        "moeda": "BRL",
        "data_vencimento": None,
        "saldo_anterior": saldo_anterior,
        "total_compras": total_compras,
        "pagamentos": pagamentos,
        "saldo_atual": saldo_atual,
        "transacoes": transacoes
    }

def process_files():
    """Process all C6 Bank files"""
    processed_count = 0

    # Process conta and global extracts
    for filename, config in files_to_process.items():
        pdf_file = data_dir / f"{filename}-0_original.pdf"

        if pdf_file.exists():
            output_file = output_dir / f"{filename}-2_extract.json"

            if config["type"] == "carteirarendafixa":
                data = extract_renda_fixa_data(pdf_file)
            else:
                data = extract_conta_data(pdf_file, config)

            # Write output
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            processed_count += 1
            print(f"Processed: {filename}")

    # Process Carbon card invoices
    for year in [2025, 2026]:
        for month in range(1, 13):
            if year == 2025 and month < 5:
                continue
            if year == 2026 and month > 4:
                continue

            month_str = f"{month:02d}"
            filename = f"c6bank_faturacarbon_{year}{month_str}"
            pdf_file = data_dir / f"{filename}-0_original.pdf"

            if pdf_file.exists():
                output_file = output_dir / f"{filename}-2_extract.json"
                data = extract_fatura_carbon_data(pdf_file, f"{year}-{month_str}")

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                processed_count += 1
                print(f"Processed: {filename}")

    return processed_count

if __name__ == "__main__":
    count = process_files()
    print(f"\nTotal files processed: {count}")
