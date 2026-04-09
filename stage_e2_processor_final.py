#!/usr/bin/env python3
"""
STAGE E2-extratos-llm Final: Enhanced extraction with text pattern matching
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

try:
    import pdfplumber
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber", "--break-system-packages"])
    import pdfplumber

try:
    import openpyxl
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "--break-system-packages"])
    import openpyxl

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4", "--break-system-packages"])
    from bs4 import BeautifulSoup

# Base paths
BASE_DIR = Path("/sessions/peaceful-clever-fermi/mnt/Financas Familia/financas-familia")
DATA_DIR = BASE_DIR / "data" / "financial_statements"
OUTPUT_DIR = BASE_DIR / "processed" / "E2_extracts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def normalize_decimal(value: str) -> float:
    """Convert Brazilian decimal format to float"""
    if not value or not isinstance(value, str):
        return 0.0
    value = value.strip()
    if not value or value.upper() in ["N/A", "NA", "-", "", "TOTAL"]:
        return 0.0

    # Remove currency symbols and text
    value = re.sub(r'[R$\s]', '', value)

    # Handle Brazilian format: 1.234.567,89 -> 1234567.89
    if value.count(',') > 0 and value.count('.') > 0:
        last_comma = value.rfind(',')
        last_dot = value.rfind('.')
        if last_comma > last_dot:
            value = value.replace('.', '').replace(',', '.')
        else:
            value = value.replace(',', '')
    elif value.count(',') == 1 and len(value.split(',')[1]) == 2:
        value = value.replace(',', '.')

    try:
        return float(value)
    except:
        return 0.0

def extract_date(date_str: str) -> Optional[str]:
    """Extract date in YYYY-MM-DD format"""
    if not date_str:
        return None
    date_str = date_str.strip()

    formats = ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            pass
    return None

def extract_pdf_full_content(pdf_path: str) -> tuple:
    """Extract complete text and tables from PDF"""
    full_text = ""
    all_tables = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
    except Exception as e:
        pass

    return full_text, all_tables

# ============================================================================
# INVESTMENT POSITIONS EXTRACTORS
# ============================================================================

def extract_rico_investimentosposicao(pdf_path: str) -> Dict[str, Any]:
    """Extract Rico investment positions using pattern matching"""
    result = {
        "tipo": "investimentosposicao",
        "banco": "rico",
        "data_posicao": None,
        "moeda": "BRL",
        "posicoes": [],
        "total": 0.0
    }

    try:
        text, tables = extract_pdf_full_content(pdf_path)

        # Extract date - look for pattern like "29/03/2026"
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        if date_match:
            result["data_posicao"] = extract_date(date_match.group(1))

        # Extract investment positions using pattern matching
        # Pattern: Fund name with value (R$ format)
        patterns = [
            r'([A-Za-z0-9\s\-\.]+?)\s+R\$\s*([\d.,]+)',  # Name followed by R$ value
        ]

        # Find all fund/investment mentions with values
        seen_names = set()
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                value_str = match.group(2) if match.lastindex >= 2 else None

                # Filter out non-investment entries
                if not name or len(name) < 2:
                    continue
                if any(x in name.upper() for x in ["SALDO", "TOTAL", "MENU", "EXPANDIR", "REDUZIR", "ÁREAS", "DASHBOARD", "CARTEIRA", "HISTÓRICO"]):
                    continue

                value = normalize_decimal(value_str) if value_str else 0.0

                if value > 100 and name not in seen_names:  # Only meaningful values
                    seen_names.add(name)
                    posicao = {
                        "product_type": "FundoInvestimento",
                        "name": name[:100],
                        "applied_value": None,
                        "current_value": value,
                        "quantity": None,
                        "unit_price": None,
                        "issuer": None,
                        "rate": None,
                        "maturity": None,
                        "rentabilidade_pct": None
                    }
                    result["posicoes"].append(posicao)
                    result["total"] += value

    except Exception as e:
        print(f"Error extracting Rico positions: {e}")

    return result

def extract_btgpactual_investimentosposicao(pdf_path: str) -> Dict[str, Any]:
    """Extract BTG Pactual investment positions"""
    result = {
        "tipo": "investimentosposicao",
        "banco": "btgpactual",
        "data_posicao": None,
        "moeda": "BRL",
        "posicoes": [],
        "total": 0.0
    }

    try:
        text, tables = extract_pdf_full_content(pdf_path)

        # Extract date
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        if date_match:
            result["data_posicao"] = extract_date(date_match.group(1))

        # Use table extraction for BTG
        for table in tables:
            for row in table:
                if row and len(row) >= 2:
                    name = str(row[0]).strip() if row[0] else ""
                    if not name or len(name) < 2:
                        continue

                    # Try each column for numeric values
                    for col in row[1:]:
                        if col:
                            value = normalize_decimal(str(col))
                            if value > 100:
                                posicao = {
                                    "product_type": "FundoInvestimento",
                                    "name": name[:100],
                                    "applied_value": None,
                                    "current_value": value,
                                    "quantity": None,
                                    "unit_price": None,
                                    "issuer": None,
                                    "rate": None,
                                    "maturity": None,
                                    "rentabilidade_pct": None
                                }
                                result["posicoes"].append(posicao)
                                result["total"] += value
                                break

    except Exception as e:
        print(f"Error extracting BTG Pactual: {e}")

    return result

def extract_c6bank_carteirarendafixa(pdf_path: str) -> Dict[str, Any]:
    """Extract C6 Bank fixed income portfolio"""
    result = {
        "tipo": "investimentosposicao",
        "banco": "c6bank",
        "data_posicao": None,
        "moeda": "BRL",
        "posicoes": [],
        "total": 0.0
    }

    try:
        text, tables = extract_pdf_full_content(pdf_path)

        # Extract date
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        if date_match:
            result["data_posicao"] = extract_date(date_match.group(1))

        # Extract from tables
        for table in tables:
            for row in table:
                if row and len(row) >= 1:
                    name = str(row[0]).strip() if row[0] else ""
                    if not name or len(name) < 2:
                        continue

                    # Get numeric value from last columns
                    for col in reversed(row[1:]):
                        if col:
                            value = normalize_decimal(str(col))
                            if value > 100:
                                posicao = {
                                    "product_type": "RendaFixa",
                                    "name": name[:100],
                                    "applied_value": value,
                                    "current_value": value,
                                    "quantity": None,
                                    "unit_price": None,
                                    "issuer": None,
                                    "rate": None,
                                    "maturity": None,
                                    "rentabilidade_pct": None
                                }
                                result["posicoes"].append(posicao)
                                result["total"] += value
                                break

    except Exception as e:
        print(f"Error extracting C6 Bank: {e}")

    return result

def extract_itau_investimentosposicao(pdf_path: str) -> Dict[str, Any]:
    """Extract Itau investment positions"""
    result = {
        "tipo": "investimentosposicao",
        "banco": "itau",
        "data_posicao": None,
        "moeda": "BRL",
        "posicoes": [],
        "total": 0.0
    }

    try:
        text, tables = extract_pdf_full_content(pdf_path)

        # Extract date
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        if date_match:
            result["data_posicao"] = extract_date(date_match.group(1))

        # Extract from tables
        for table in tables:
            for row in table:
                if row and len(row) >= 1:
                    name = str(row[0]).strip() if row[0] else ""
                    if not name or len(name) < 2:
                        continue

                    # Get numeric values
                    for col in reversed(row[1:]):
                        if col:
                            value = normalize_decimal(str(col))
                            if value > 100:
                                posicao = {
                                    "product_type": "FundoInvestimento",
                                    "name": name[:100],
                                    "applied_value": value,
                                    "current_value": value,
                                    "quantity": None,
                                    "unit_price": None,
                                    "issuer": None,
                                    "rate": None,
                                    "maturity": None,
                                    "rentabilidade_pct": None
                                }
                                result["posicoes"].append(posicao)
                                result["total"] += value
                                break

    except Exception as e:
        print(f"Error extracting Itau investment positions: {e}")

    return result

# ============================================================================
# CDB DETAIL EXTRACTORS
# ============================================================================

def extract_santander_cdbdetalhes_pdf(pdf_path: str, filename: str) -> Dict[str, Any]:
    """Extract Santander CDB details from PDF"""
    result = {
        "tipo": "cdbdetalhes",
        "banco": "santander",
        "data_posicao": None,
        "moeda": "BRL",
        "produtos": [],
        "total_bruto": 0.0,
        "total_liquido": 0.0
    }

    try:
        text, tables = extract_pdf_full_content(pdf_path)

        # Extract date
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        if date_match:
            result["data_posicao"] = extract_date(date_match.group(1))

        # Extract products from tables
        for table in tables:
            for row in table:
                if row and len(row) >= 2:
                    name = str(row[0]).strip() if row[0] else ""
                    if not name or len(name) < 2:
                        continue

                    try:
                        produto = {
                            "nome": name,
                            "valor_aplicado": normalize_decimal(str(row[1]) if len(row) > 1 and row[1] else "0"),
                            "data_aplicacao": extract_date(str(row[2])) if len(row) > 2 and row[2] else None,
                            "taxa": str(row[3]).strip() if len(row) > 3 and row[3] else None,
                            "vencimento": extract_date(str(row[4])) if len(row) > 4 and row[4] else None,
                            "saldo_bruto": normalize_decimal(str(row[5]) if len(row) > 5 and row[5] else "0"),
                            "saldo_liquido": normalize_decimal(str(row[6]) if len(row) > 6 and row[6] else "0"),
                            "ir_provisao": normalize_decimal(str(row[7]) if len(row) > 7 and row[7] else "0")
                        }
                        result["produtos"].append(produto)
                        result["total_bruto"] += produto["saldo_bruto"]
                        result["total_liquido"] += produto["saldo_liquido"]
                    except:
                        pass
    except Exception as e:
        print(f"Error extracting Santander CDB details: {e}")

    return result

def extract_santander_cdbresumo_pdf(pdf_path: str) -> Dict[str, Any]:
    """Extract Santander CDB summary from PDF"""
    result = {
        "tipo": "cdbdetalhes",
        "banco": "santander",
        "data_posicao": None,
        "moeda": "BRL",
        "produtos": [],
        "total_bruto": 0.0,
        "total_liquido": 0.0
    }

    try:
        text, tables = extract_pdf_full_content(pdf_path)

        # Extract date
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        if date_match:
            result["data_posicao"] = extract_date(date_match.group(1))

        # Extract products
        for table in tables:
            for row in table:
                if row and len(row) >= 2:
                    name = str(row[0]).strip() if row[0] else ""
                    if not name or len(name) < 2:
                        continue

                    try:
                        produto = {
                            "nome": name,
                            "valor_aplicado": 0.0,
                            "data_aplicacao": None,
                            "taxa": None,
                            "vencimento": None,
                            "saldo_bruto": normalize_decimal(str(row[1]) if row[1] else "0"),
                            "saldo_liquido": normalize_decimal(str(row[2]) if len(row) > 2 and row[2] else "0"),
                            "ir_provisao": 0.0
                        }
                        result["produtos"].append(produto)
                        result["total_bruto"] += produto["saldo_bruto"]
                        result["total_liquido"] += produto["saldo_liquido"]
                    except:
                        pass
    except Exception as e:
        print(f"Error extracting Santander CDB resume: {e}")

    return result

def extract_xlsx_santander_cdbresumo(xlsx_path: str) -> Dict[str, Any]:
    """Extract Santander CDB resume from XLSX"""
    result = {
        "tipo": "cdbdetalhes",
        "banco": "santander",
        "data_posicao": None,
        "moeda": "BRL",
        "produtos": [],
        "total_bruto": 0.0,
        "total_liquido": 0.0
    }

    try:
        wb = openpyxl.load_workbook(xlsx_path)
        ws = wb.active

        for row in ws.iter_rows(min_row=2, values_only=True):
            if row and row[0]:
                try:
                    produto = {
                        "nome": str(row[0]).strip() if row[0] else "",
                        "valor_aplicado": normalize_decimal(str(row[1])) if len(row) > 1 and row[1] else 0.0,
                        "data_aplicacao": None,
                        "taxa": str(row[2]).strip() if len(row) > 2 and row[2] else None,
                        "vencimento": None,
                        "saldo_bruto": normalize_decimal(str(row[3])) if len(row) > 3 and row[3] else 0.0,
                        "saldo_liquido": normalize_decimal(str(row[4])) if len(row) > 4 and row[4] else 0.0,
                        "ir_provisao": 0.0
                    }
                    if produto["nome"]:
                        result["produtos"].append(produto)
                        result["total_bruto"] += produto["saldo_bruto"]
                        result["total_liquido"] += produto["saldo_liquido"]
                except:
                    pass
    except Exception as e:
        print(f"Error extracting XLSX: {e}")

    return result

def extract_html_xls_santander(xls_path: str) -> Dict[str, Any]:
    """Extract HTML-disguised XLS files"""
    result = {
        "tipo": "cdbdetalhes",
        "banco": "santander",
        "data_posicao": None,
        "moeda": "BRL",
        "produtos": [],
        "total_bruto": 0.0,
        "total_liquido": 0.0
    }

    try:
        with open(xls_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract date
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', html_content)
        if date_match:
            result["data_posicao"] = extract_date(date_match.group(1))

        # Extract tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:] if len(rows) > 1 else rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    try:
                        name = cells[0].get_text(strip=True) if cells else ""
                        if not name or len(name) < 2 or name.upper() in ["NOME", "PRODUTO"]:
                            continue

                        produto = {
                            "nome": name,
                            "valor_aplicado": normalize_decimal(cells[1].get_text(strip=True)) if len(cells) > 1 else 0.0,
                            "data_aplicacao": extract_date(cells[2].get_text(strip=True)) if len(cells) > 2 else None,
                            "taxa": cells[3].get_text(strip=True) if len(cells) > 3 else None,
                            "vencimento": extract_date(cells[4].get_text(strip=True)) if len(cells) > 4 else None,
                            "saldo_bruto": normalize_decimal(cells[5].get_text(strip=True)) if len(cells) > 5 else 0.0,
                            "saldo_liquido": normalize_decimal(cells[6].get_text(strip=True)) if len(cells) > 6 else 0.0,
                            "ir_provisao": normalize_decimal(cells[7].get_text(strip=True)) if len(cells) > 7 else 0.0
                        }
                        result["produtos"].append(produto)
                        result["total_bruto"] += produto["saldo_bruto"]
                        result["total_liquido"] += produto["saldo_liquido"]
                    except:
                        pass
    except Exception as e:
        print(f"Error extracting HTML XLS: {e}")

    return result

# ============================================================================
# IMAGE EXTRACTORS
# ============================================================================

def extract_bank_statement_image(jpg_path: str, banco: str) -> Dict[str, Any]:
    """Extract bank statement from JPG image"""
    return {
        "tipo": "extratoconta",
        "banco": banco,
        "conta": None,
        "periodo": {"inicio": None, "fim": None},
        "moeda": "BRL",
        "saldo_inicial": 0.0,
        "saldo_final": 0.0,
        "transacoes": [],
        "_note": "Image requires OCR/vision processing"
    }

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_all_files():
    """Process all files for Stage E2"""

    files_to_process = [
        ("btgpactual_investimentosposicao_202603-0_original.pdf", extract_btgpactual_investimentosposicao, "btgpactual_investimentosposicao_202603-2_extract.json"),
        ("c6bank_carteirarendafixa_202603-0_original.pdf", extract_c6bank_carteirarendafixa, "c6bank_carteirarendafixa_202603-2_extract.json"),
        ("rico_investimentosposicao_202603-0_original.pdf", extract_rico_investimentosposicao, "rico_investimentosposicao_202603-2_extract.json"),
        ("itau_investimentosposicao_202603-0_original.pdf", extract_itau_investimentosposicao, "itau_investimentosposicao_202603-2_extract.json"),

        ("santander_cdbdetalhesdi1_202603-0_original.pdf", lambda p: extract_santander_cdbdetalhes_pdf(p, "di1"), "santander_cdbdetalhesdi1_202603-2_extract.json"),
        ("santander_cdbdetalhesdi2_202603-0_original.pdf", lambda p: extract_santander_cdbdetalhes_pdf(p, "di2"), "santander_cdbdetalhesdi2_202603-2_extract.json"),
        ("santander_cdbdetalhesprog_202603-0_original.pdf", lambda p: extract_santander_cdbdetalhes_pdf(p, "prog"), "santander_cdbdetalhesprog_202603-2_extract.json"),
        ("santander_cdbresumo_202603-0_original.pdf", extract_santander_cdbresumo_pdf, "santander_cdbresumo_202603-2_extract.json"),

        ("santander_cdbresumo_202604-0_original.xlsx", extract_xlsx_santander_cdbresumo, "santander_cdbresumo_202604-2_extract.json"),
        ("santander_cdbdi_202604-0_original.xls", extract_html_xls_santander, "santander_cdbdi_202604-2_extract.json"),
        ("santander_cdbmetaservas_202604-0_original.xls", extract_html_xls_santander, "santander_cdbmetaservas_202604-2_extract.json"),

        ("binance_extratoconta_202603a-0_original.jpg", lambda p: extract_bank_statement_image(p, "binance"), "binance_extratoconta_202603a-2_extract.json"),
        ("binance_extratoconta_202603b-0_original.jpg", lambda p: extract_bank_statement_image(p, "binance"), "binance_extratoconta_202603b-2_extract.json"),
        ("binance_extratoconta_202603c-0_original.jpg", lambda p: extract_bank_statement_image(p, "binance"), "binance_extratoconta_202603c-2_extract.json"),
        ("itau_extratocontapersonnalite_202603a-0_original.jpg", lambda p: extract_bank_statement_image(p, "itau"), "itau_extratocontapersonnalite_202603a-2_extract.json"),
        ("itau_extratocontapersonnalite_202603b-0_original.jpg", lambda p: extract_bank_statement_image(p, "itau"), "itau_extratocontapersonnalite_202603b-2_extract.json"),
    ]

    processed_count = 0
    failed_files = []

    for input_filename, extractor_func, output_filename in files_to_process:
        input_path = DATA_DIR / input_filename
        output_path = OUTPUT_DIR / output_filename

        if not input_path.exists():
            print(f"SKIP: {input_filename} (file not found)")
            failed_files.append((input_filename, "File not found"))
            continue

        try:
            print(f"Processing: {input_filename}")
            result = extractor_func(str(input_path))

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            processed_count += 1
            print(f"  ✓ Written to: {output_filename}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed_files.append((input_filename, str(e)))

    print("\n" + "="*70)
    print(f"STAGE E2 PROCESSING COMPLETE")
    print(f"Successfully processed: {processed_count}/{len(files_to_process)}")
    if failed_files:
        print(f"\nFailed files ({len(failed_files)}):")
        for filename, error in failed_files:
            print(f"  - {filename}: {error}")
    print("="*70)

if __name__ == "__main__":
    process_all_files()
