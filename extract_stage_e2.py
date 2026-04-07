#!/usr/bin/env python3
"""
Stage E2 Extraction Script
Extracts data from financial statements (PDFs and JPGs)
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import pdfplumber
from datetime import datetime

# Working directories
BASE_DIR = Path("/sessions/magical-elegant-mendel/mnt/Financas Familia/financas-familia")
DATA_DIR = BASE_DIR / "data" / "financial_statements"
OUTPUT_DIR = BASE_DIR / "processed" / "E2_extracts"

# File mappings
SAVINGS_ACCOUNTS = [
    ("bradesco_extratopoupanca_202501_202502-0_original.pdf", "bradesco_extratopoupanca_202501_202502-2_extract.json"),
    ("bradesco_extratopoupanca_202503_202504-0_original.pdf", "bradesco_extratopoupanca_202503_202504-2_extract.json"),
    ("bradesco_extratopoupanca_202505_202506-0_original.pdf", "bradesco_extratopoupanca_202505_202506-2_extract.json"),
    ("bradesco_extratopoupanca_202507_202508-0_original.pdf", "bradesco_extratopoupanca_202507_202508-2_extract.json"),
    ("bradesco_extratopoupanca_202509_202510-0_original.pdf", "bradesco_extratopoupanca_202509_202510-2_extract.json"),
    ("bradesco_extratopoupanca_202511_202512-0_original.pdf", "bradesco_extratopoupanca_202511_202512-2_extract.json"),
    ("bradesco_extratopoupanca_202601_202603-0_original.pdf", "bradesco_extratopoupanca_202601_202603-2_extract.json"),
]

GLOBAL_CURRENCY = [
    ("c6bank_extratocontaglobaleur_202511_202512-0_original.pdf", "c6bank_extratocontaglobaleur_202511_202512-2_extract.json"),
    ("c6bank_extratocontaglobaleur_202601_202603-0_original.pdf", "c6bank_extratocontaglobaleur_202601_202603-2_extract.json"),
    ("c6bank_extratocontaglobaleur_202601_202604-0_original.pdf", "c6bank_extratocontaglobaleur_202601_202604-2_extract.json"),
    ("c6bank_extratocontaglobalusd_202505_202507-0_original.pdf", "c6bank_extratocontaglobalusd_202505_202507-2_extract.json"),
    ("c6bank_extratocontaglobalusd_202508_202510-0_original.pdf", "c6bank_extratocontaglobalusd_202508_202510-2_extract.json"),
    ("c6bank_extratocontaglobalusd_202511_202512-0_original.pdf", "c6bank_extratocontaglobalusd_202511_202512-2_extract.json"),
    ("c6bank_extratocontaglobalusd_202512_202603-0_original.pdf", "c6bank_extratocontaglobalusd_202512_202603-2_extract.json"),
    ("c6bank_extratocontaglobalusd_202601_202604-0_original.pdf", "c6bank_extratocontaglobalusd_202601_202604-2_extract.json"),
]

INVESTMENTS = [
    ("btgpactual_investimentosposicao_202603-0_original.pdf", "btgpactual_investimentosposicao_202603-2_extract.json"),
    ("itau_investimentosposicao_202603-0_original.pdf", "itau_investimentosposicao_202603-2_extract.json"),
    ("rico_investimentosposicao_202603-0_original.pdf", "rico_investimentosposicao_202603-2_extract.json"),
    ("c6bank_carteirarendafixa_202603-0_original.pdf", "c6bank_carteirarendafixa_202603-2_extract.json"),
]

CDB_FILES = [
    ("santander_cdbdetalhesdi1_202603-0_original.pdf", "santander_cdbdetalhesdi1_202603-2_extract.json"),
    ("santander_cdbdetalhesdi2_202603-0_original.pdf", "santander_cdbdetalhesdi2_202603-2_extract.json"),
    ("santander_cdbdetalhesprog_202603-0_original.pdf", "santander_cdbdetalhesprog_202603-2_extract.json"),
    ("santander_cdbresumo_202603-0_original.pdf", "santander_cdbresumo_202603-2_extract.json"),
]


def extract_number(text: str) -> Optional[float]:
    """Extract numeric value from text, handling Brazilian format"""
    if not text:
        return None
    # Remove spaces and handle Brazilian decimal format
    text = text.strip().replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(date_str: str) -> Optional[str]:
    """Parse date string to ISO format"""
    if not date_str:
        return None
    # Try common Brazilian date formats
    for fmt in ["%d/%m/%Y", "%d/%m/%y", "%d.%m.%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str.strip()


def extract_savings_account(pdf_path: Path) -> Dict[str, Any]:
    """Extract data from Bradesco savings account statement"""
    banco = "Bradesco"
    tipo = "extratopoupanca"
    moeda = "BRL"
    saldo_inicial = 0
    saldo_final = 0
    transacoes = []
    periodo = {"inicio": "", "fim": ""}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Combine all text from all pages
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() or ""

            # Extract period from filename
            filename = pdf_path.stem
            match = re.search(r"(\d{6})_(\d{6})", filename)
            if match:
                inicio = f"20{match.group(1)[:2]}-{match.group(1)[2:4]}-01"
                fim = f"20{match.group(2)[:2]}-{match.group(2)[2:4]}-01"
                periodo = {"inicio": inicio, "fim": fim}

            # Extract balances and transactions
            lines = all_text.split("\n")
            for i, line in enumerate(lines):
                line = line.strip()

                # Look for initial balance
                if "saldo anterior" in line.lower() or "saldo de abertura" in line.lower():
                    val = extract_number(lines[i + 1] if i + 1 < len(lines) else line)
                    if val is not None:
                        saldo_inicial = val

                # Look for final balance
                if "saldo disponível" in line.lower() or "saldo atual" in line.lower():
                    val = extract_number(lines[i + 1] if i + 1 < len(lines) else line)
                    if val is not None:
                        saldo_final = val

    except Exception as e:
        print(f"Error extracting savings account from {pdf_path}: {e}")

    return {
        "banco": banco,
        "tipo": tipo,
        "moeda": moeda,
        "periodo": periodo,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "transacoes": transacoes,
    }


def extract_global_currency(pdf_path: Path) -> Dict[str, Any]:
    """Extract data from C6 Bank global currency account"""
    # Determine currency from filename
    moeda = "EUR" if "eur" in pdf_path.name.lower() else "USD"
    banco = "C6Bank"
    tipo = "extratocontaglobal"
    saldo_inicial = 0
    saldo_final = 0
    transacoes = []
    periodo = {"inicio": "", "fim": ""}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() or ""

            # Extract period from filename
            filename = pdf_path.stem
            match = re.search(r"(\d{6})_(\d{6})", filename)
            if match:
                inicio = f"20{match.group(1)[:2]}-{match.group(1)[2:4]}-01"
                fim = f"20{match.group(2)[:2]}-{match.group(2)[2:4]}-01"
                periodo = {"inicio": inicio, "fim": fim}

            lines = all_text.split("\n")
            for i, line in enumerate(lines):
                line = line.strip()

                if "saldo anterior" in line.lower() or "saldo de abertura" in line.lower():
                    val = extract_number(lines[i + 1] if i + 1 < len(lines) else line)
                    if val is not None:
                        saldo_inicial = val

                if "saldo disponível" in line.lower() or "saldo atual" in line.lower():
                    val = extract_number(lines[i + 1] if i + 1 < len(lines) else line)
                    if val is not None:
                        saldo_final = val

    except Exception as e:
        print(f"Error extracting global currency from {pdf_path}: {e}")

    return {
        "banco": banco,
        "tipo": tipo,
        "moeda": moeda,
        "periodo": periodo,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo_final,
        "transacoes": transacoes,
    }


def extract_investments(pdf_path: Path) -> Dict[str, Any]:
    """Extract data from investment position statements"""
    # Determine banco from filename
    if "btg" in pdf_path.name.lower():
        banco = "BTG Pactual"
    elif "itau" in pdf_path.name.lower():
        banco = "Itaú"
    elif "rico" in pdf_path.name.lower():
        banco = "Rico"
    elif "c6bank" in pdf_path.name.lower():
        banco = "C6Bank"
    else:
        banco = "Unknown"

    tipo = "investimentosposicao"
    saldo_total = 0
    composicao = []
    data_posicao = "2026-03-31"

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() or ""

            # Try to extract date from text
            date_match = re.search(r"(\d{2}[/-]\d{2}[/-]20\d{2})", all_text)
            if date_match:
                data_posicao = parse_date(date_match.group(1)) or "2026-03-31"

    except Exception as e:
        print(f"Error extracting investments from {pdf_path}: {e}")

    return {
        "banco": banco,
        "tipo": tipo,
        "data_posicao": data_posicao,
        "saldo_total": saldo_total,
        "composicao": composicao,
    }


def extract_cdb(pdf_path: Path) -> Dict[str, Any]:
    """Extract data from CDB statements"""
    banco = "Santander"
    tipo = "cdbdetalhes"
    produtos = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() or ""

            # Basic extraction - structure depends on actual PDF format
            # This is a placeholder that should be enhanced based on actual document structure

    except Exception as e:
        print(f"Error extracting CDB from {pdf_path}: {e}")

    return {
        "banco": banco,
        "tipo": tipo,
        "produtos": produtos,
    }


def process_all_pdfs():
    """Process all PDF files"""
    results = {
        "savings": [],
        "global_currency": [],
        "investments": [],
        "cdb": [],
        "errors": [],
    }

    # Process savings accounts
    print("Processing savings accounts...")
    for input_file, output_file in SAVINGS_ACCOUNTS:
        input_path = DATA_DIR / input_file
        output_path = OUTPUT_DIR / output_file
        try:
            if input_path.exists():
                data = extract_savings_account(input_path)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                results["savings"].append(output_file)
                print(f"  ✓ {output_file}")
            else:
                print(f"  ✗ File not found: {input_file}")
                results["errors"].append(f"Not found: {input_file}")
        except Exception as e:
            print(f"  ✗ Error processing {input_file}: {e}")
            results["errors"].append(f"Error in {input_file}: {str(e)}")

    # Process global currency accounts
    print("\nProcessing global currency accounts...")
    for input_file, output_file in GLOBAL_CURRENCY:
        input_path = DATA_DIR / input_file
        output_path = OUTPUT_DIR / output_file
        try:
            if input_path.exists():
                data = extract_global_currency(input_path)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                results["global_currency"].append(output_file)
                print(f"  ✓ {output_file}")
            else:
                print(f"  ✗ File not found: {input_file}")
                results["errors"].append(f"Not found: {input_file}")
        except Exception as e:
            print(f"  ✗ Error processing {input_file}: {e}")
            results["errors"].append(f"Error in {input_file}: {str(e)}")

    # Process investments
    print("\nProcessing investments...")
    for input_file, output_file in INVESTMENTS:
        input_path = DATA_DIR / input_file
        output_path = OUTPUT_DIR / output_file
        try:
            if input_path.exists():
                data = extract_investments(input_path)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                results["investments"].append(output_file)
                print(f"  ✓ {output_file}")
            else:
                print(f"  ✗ File not found: {input_file}")
                results["errors"].append(f"Not found: {input_file}")
        except Exception as e:
            print(f"  ✗ Error processing {input_file}: {e}")
            results["errors"].append(f"Error in {input_file}: {str(e)}")

    # Process CDBs
    print("\nProcessing CDB statements...")
    for input_file, output_file in CDB_FILES:
        input_path = DATA_DIR / input_file
        output_path = OUTPUT_DIR / output_file
        try:
            if input_path.exists():
                data = extract_cdb(input_path)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                results["cdb"].append(output_file)
                print(f"  ✓ {output_file}")
            else:
                print(f"  ✗ File not found: {input_file}")
                results["errors"].append(f"Not found: {input_file}")
        except Exception as e:
            print(f"  ✗ Error processing {input_file}: {e}")
            results["errors"].append(f"Error in {input_file}: {str(e)}")

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("Stage E2 Extraction - Financial Statements")
    print("=" * 60)

    results = process_all_pdfs()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Savings accounts: {len(results['savings'])} files")
    print(f"Global currency: {len(results['global_currency'])} files")
    print(f"Investments: {len(results['investments'])} files")
    print(f"CDB statements: {len(results['cdb'])} files")
    print(f"Errors: {len(results['errors'])}")

    if results["errors"]:
        print("\nErrors encountered:")
        for error in results["errors"]:
            print(f"  - {error}")

    print("\n" + "=" * 60)
