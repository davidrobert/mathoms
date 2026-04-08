#!/usr/bin/env python3
"""
LLM Fallback: Extract Itaú Pão de Açúcar and QuintoAndar invoices using pdfplumber.
Overwrites existing empty JSON files with proper data extraction.
"""

import json
import re
from pathlib import Path
from datetime import datetime
import pdfplumber

# Base paths
BASE_DIR = Path("/sessions/magical-elegant-mendel/mnt/Financas Familia/financas-familia")
DATA_DIR = BASE_DIR / "data/financial_statements"
OUTPUT_DIR = BASE_DIR / "processed/E2_extracts"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_currency(value_str):
    """Convert Brazilian currency string to float."""
    if not value_str:
        return 0.0
    # Remove spaces, convert comma to dot for decimal
    value_str = value_str.strip().replace(".", "").replace(",", ".")
    try:
        return float(value_str)
    except ValueError:
        return 0.0


def extract_itau_paoacucar(pdf_path):
    """Extract transactions from Itaú Pão de Açúcar credit card invoice."""
    result = {
        "banco": "itau",
        "tipo": "faturapaoacucar",
        "moeda": "BRL",
        "periodo": {"inicio": None, "fim": None},
        "data_vencimento": None,
        "valor_total": 0,
        "transacoes": []
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            page_texts = []

            # Extract text from all pages
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    page_texts.append(text)
                    all_text += text + "\n"

            # Parse period from filename (YYYYMM)
            filename = pdf_path.name
            match = re.search(r'(\d{6})', filename)
            if match:
                period = match.group(1)
                year = int(period[:4])
                month = int(period[4:6])
                result["periodo"]["inicio"] = f"{year}-{month:02d}-01"
                # Calculate last day of month
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                result["periodo"]["fim"] = f"{year}-{month:02d}-{last_day:02d}"

            # Extract data from text
            lines = all_text.split('\n')

            # Find vencimento (payment due date) - appears in first page
            for line in lines[:50]:  # Check first page
                if 'vencimento:' in line.lower():
                    date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', line)
                    if date_match:
                        day, month, year = date_match.groups()
                        result["data_vencimento"] = f"{year}-{month}-{day}"
                        break

            # Find TOTAL desta fatura or "= Total desta fatura"
            for line in lines[:100]:
                if 'total desta fatura' in line.lower():
                    # Look for value after equals sign or at end of line
                    # Match pattern: "= Total desta fatura XXX,XX" or just the number
                    value_match = re.search(r'([\d.,]+)\s*$', line.strip())
                    if value_match:
                        result["valor_total"] = parse_currency(value_match.group(1))
                        break

            # Extract transactions using a more robust approach
            # Look through ALL pages for transactions
            all_transaction_lines = []
            for page_idx, page_text in enumerate(page_texts):
                page_lines = page_text.split('\n')

                in_transactions = False
                for i, line in enumerate(page_lines):
                    # Start of transactions section
                    if 'DATA ESTABELECIMENTO' in line.upper() and 'VALOR' in line.upper():
                        in_transactions = True
                        continue

                    if in_transactions:
                        # Stop conditions - more restrictive
                        if 'Compras parceladas' in line or 'Limites de crédito' in line or 'Crédito Rotativo' in line:
                            in_transactions = False
                            continue

                        line = line.strip()
                        if not line or len(line) < 10:
                            continue

                        # Try to parse transaction line
                        # Format: DD/MM MERCHANT_CODE VALUE [EXTRA_STUFF]
                        # Match: (date) (merchant + code) (currency: digits,digits)
                        match = re.match(r'(\d{2}/\d{2})\s+(.+?)\s(\d+,\d{2})', line)
                        if match:
                            date_str, description, value_str = match.groups()
                            all_transaction_lines.append((date_str, description.strip(), value_str))

            # Process all collected transactions
            for date_str, description, value_str in all_transaction_lines:
                # Convert DD/MM to YYYY-MM-DD
                if result["periodo"]["inicio"]:
                    value = parse_currency(value_str)
                    # Transactions are debits by default (negative)
                    if value > 0:
                        value = -value

                    # Use transaction date from PDF, extracting day/month
                    day = date_str.split('/')[0]
                    month = date_str.split('/')[1]
                    year = result["periodo"]["inicio"][:4]

                    # Transactions are typically in the billing period month
                    # If a transaction appears in the next month (common for late statements),
                    # we keep the year the same since the billing month already accounts for this
                    # The invoice period is typically the month shown in the filename

                    result["transacoes"].append({
                        "data": f"{year}-{month}-{day}",
                        "descricao": description,
                        "valor": value,
                        "cartao": "titular"
                    })

    except Exception as e:
        result["erro"] = str(e)
        print(f"Error processing {pdf_path}: {e}")

    return result


def extract_quintoandar(pdf_path):
    """Extract invoice items from QuintoAndar rental invoice."""
    # Determine property from filename
    property_name = "calixto" if "calixto" in pdf_path.name else "majorfreire"

    result = {
        "banco": "quintoandar",
        "tipo": "faturaaluguel",
        "propriedade": property_name,
        "periodo": None,
        "data_vencimento": None,
        "itens": [],
        "valor_total": 0
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""

            # Extract text from all pages
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text += text + "\n"

            # Parse period from filename (YYYYMM)
            filename = pdf_path.name
            match = re.search(r'(\d{6})', filename)
            if match:
                period = match.group(1)
                result["periodo"] = f"{period[:4]}-{period[4:6]}"

            lines = all_text.split('\n')

            # Find vencimento (due date) - look for "Receber até DD/MM/YYYY"
            for line in lines:
                if 'receber até' in line.lower():
                    date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', line)
                    if date_match:
                        day, month, year = date_match.groups()
                        result["data_vencimento"] = f"{year}-{month}-{day}"
                        break

            # Extract itemized charges
            current_total = 0
            for line in lines:
                line = line.strip()
                if not line or len(line) < 5:
                    continue

                # Look for lines with monetary values (R$ or -R$)
                if re.search(r'[\d.,]+\s*$', line):
                    # Try to match: description + optional -R$ + value
                    match = re.search(r'(.+?)\s+-?R\$\s*([\d.,]+)\s*$', line)
                    if match:
                        description = match.group(1).strip()
                        value_str = match.group(2)

                        # Filter for common rental invoice items
                        keywords = ['ALUGUEL', 'CONDOMÍNIO', 'TAXA', 'ÁGUA', 'LUZ', 'GÁS', 'IPTU', 'SEGURO', 'SERVIÇO', 'ADMINISTRAÇÃO', 'FUNDO', 'RESERVA', 'DESPESA']
                        if any(keyword in description.upper() for keyword in keywords):
                            value = parse_currency(value_str)
                            if value > 0:  # Only include positive values (income/charges)
                                result["itens"].append({
                                    "descricao": description,
                                    "valor": value
                                })
                                current_total += value

            # Set total from items
            result["valor_total"] = current_total

    except Exception as e:
        result["erro"] = str(e)
        print(f"Error processing {pdf_path}: {e}")

    return result


def main():
    """Process all invoices."""

    # Itaú Pão de Açúcar invoices
    itau_files = [
        "itau_faturapaoacucar_202505-0_original.pdf",
        "itau_faturapaoacucar_202506-0_original.pdf",
        "itau_faturapaoacucar_202507-0_original.pdf",
        "itau_faturapaoacucar_202508-0_original.pdf",
        "itau_faturapaoacucar_202509-0_original.pdf",
        "itau_faturapaoacucar_202510-0_original.pdf",
        "itau_faturapaoacucar_202511-0_original.pdf",
        "itau_faturapaoacucar_202512-0_original.pdf",
        "itau_faturapaoacucar_202601-0_original.pdf",
        "itau_faturapaoacucar_202602-0_original.pdf",
        "itau_faturapaoacucar_202603-0_original.pdf",
    ]

    # QuintoAndar invoices
    quintoandar_files = [
        "quintoandar_faturaaluguelcalixto_202602-0_original.pdf",
        "quintoandar_faturaaluguelmajorfreire_202602-0_original.pdf",
    ]

    print("=" * 80)
    print("PROCESSING ITAÚ PÃO DE AÇÚCAR INVOICES")
    print("=" * 80)

    for filename in itau_files:
        pdf_path = DATA_DIR / filename
        if pdf_path.exists():
            print(f"\nProcessing: {filename}")
            data = extract_itau_paoacucar(pdf_path)

            # Determine output filename
            base_name = filename.replace("-0_original.pdf", "")
            output_path = OUTPUT_DIR / f"{base_name}-2_extract.json"

            # Save to JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            tx_count = len(data.get("transacoes", []))
            print(f"  ✓ Saved to {output_path.name}")
            print(f"  Transactions: {tx_count}, Total: R$ {data.get('valor_total', 0):.2f}")
        else:
            print(f"  ✗ File not found: {pdf_path}")

    print("\n" + "=" * 80)
    print("PROCESSING QUINTOANDAR INVOICES")
    print("=" * 80)

    for filename in quintoandar_files:
        pdf_path = DATA_DIR / filename
        if pdf_path.exists():
            print(f"\nProcessing: {filename}")
            data = extract_quintoandar(pdf_path)

            # Determine output filename
            base_name = filename.replace("-0_original.pdf", "")
            output_path = OUTPUT_DIR / f"{base_name}-2_extract.json"

            # Save to JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            item_count = len(data.get("itens", []))
            print(f"  ✓ Saved to {output_path.name}")
            print(f"  Items: {item_count}, Total: R$ {data.get('valor_total', 0):.2f}")
        else:
            print(f"  ✗ File not found: {pdf_path}")

    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
