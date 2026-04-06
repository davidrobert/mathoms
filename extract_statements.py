#!/usr/bin/env python3
"""
Extract bank statement data from PDFs and JPGs into JSON format.
"""

import pdfplumber
import json
from pathlib import Path
import re
from PIL import Image
import pytesseract
from typing import Dict, List, Any, Optional, Tuple

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "financial_statements"
OUTPUT_DIR = BASE_DIR / "processed" / "E2_extracts"

def parse_value(val_str: str) -> Optional[float]:
    """Parse Brazilian currency format to float"""
    if not val_str:
        return None
    val_str = str(val_str).strip()
    # Remove R$ and spaces
    val_str = val_str.replace('R$', '').replace('$', '').strip()
    # Remove thousand separators and convert decimal
    val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except (ValueError, AttributeError):
        return None

def extract_c6_corrente_202603(pdf_path: str) -> Dict[str, Any]:
    """Extract C6 Bank corrente account statement March 2025 - March 2026"""

    transacoes = []
    conta_numero = "130952222"
    agencia = "1"

    with pdfplumber.open(pdf_path) as pdf:
        # First page - get header info
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        # Extract account number and agency from text
        match = re.search(r'Conta:\s*(\d+)', text)
        if match:
            conta_numero = match.group(1)

        match = re.search(r'Agência:\s*(\d+)', text)
        if match:
            agencia = match.group(1)

        # Extract all transactions from all pages
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue

                        # Skip header rows
                        if any('Data' in str(cell) for cell in row):
                            continue

                        data_lanc = row[0] if row[0] else None
                        data_contabil = row[1] if len(row) > 1 else None
                        tipo_trans = row[2] if len(row) > 2 else None
                        descricao = row[3] if len(row) > 3 else None
                        valor_str = row[4] if len(row) > 4 else None

                        # Filter out summary rows
                        if 'Saldo do dia' in str(descricao):
                            continue

                        if not data_lanc or not descricao:
                            continue

                        # Normalize date strings
                        data_lanc = str(data_lanc).strip()
                        if not data_lanc or len(data_lanc) < 5:
                            continue

                        valor = parse_value(valor_str)
                        if valor is None:
                            continue

                        tipo = "crédito" if valor > 0 else "débito"

                        transacoes.append({
                            "data": data_lanc,
                            "descricao": str(descricao).strip() if descricao else "",
                            "tipo": tipo,
                            "valor": abs(valor),
                            "saldo_apos": 0.00
                        })

    # Remove duplicates while preserving order
    seen = set()
    unique_transacoes = []
    for t in transacoes:
        key = (t['data'], t['descricao'], t['valor'], t['tipo'])
        if key not in seen:
            seen.add(key)
            unique_transacoes.append(t)

    # Build response
    data = {
        "tipo": "extratoconta",
        "instituicao": "C6 Bank",
        "conta": {
            "numero": conta_numero,
            "tipo": "corrente",
            "moeda": "BRL",
            "agencia": agencia
        },
        "periodo": {
            "data_inicio": "2025-03-29",
            "data_fim": "2026-03-29"
        },
        "saldos": {
            "saldo_inicial": {
                "valor": 0.00,
                "data": "2025-03-29"
            },
            "saldo_final": {
                "valor": 6930.11,
                "data": "2026-03-29"
            }
        },
        "transacoes": unique_transacoes,
        "total_periodo": {
            "total_debitos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'débito'), 2),
            "total_creditos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'crédito'), 2),
            "saldo_liquido": 0.00
        }
    }

    return data

def extract_c6_global_eur(pdf_path: str, periodo: str) -> Dict[str, Any]:
    """Extract C6 Bank Global EUR account statement"""

    transacoes = []
    conta_numero = ""
    agencia = "1"

    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        # Extract account info
        match = re.search(r'Conta:\s*(\d+)', text)
        if match:
            conta_numero = match.group(1)

        # Extract transactions
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue

                        if any('Data' in str(cell) for cell in row):
                            continue

                        data_lanc = row[0] if row[0] else None
                        tipo_trans = row[2] if len(row) > 2 else None
                        descricao = row[3] if len(row) > 3 else None
                        valor_str = row[4] if len(row) > 4 else None

                        if 'Saldo' in str(descricao):
                            continue

                        if not data_lanc or not descricao:
                            continue

                        data_lanc = str(data_lanc).strip()
                        if not data_lanc or len(data_lanc) < 5:
                            continue

                        valor = parse_value(valor_str)
                        if valor is None:
                            continue

                        tipo = "crédito" if valor > 0 else "débito"

                        transacoes.append({
                            "data": data_lanc,
                            "descricao": str(descricao).strip() if descricao else "",
                            "tipo": tipo,
                            "valor": abs(valor),
                            "saldo_apos": 0.00
                        })

    # Remove duplicates
    seen = set()
    unique_transacoes = []
    for t in transacoes:
        key = (t['data'], t['descricao'], t['valor'], t['tipo'])
        if key not in seen:
            seen.add(key)
            unique_transacoes.append(t)

    # Parse periodo
    if "_" in periodo:
        parts = periodo.split("_")
        data_inicio = f"20{parts[0][:2]}-{parts[0][2:4]}-01"
        data_fim = f"20{parts[1][:2]}-{parts[1][2:4]}-30"
    else:
        data_inicio = f"2025-{periodo[2:4]}-01"
        data_fim = f"2025-{periodo[2:4]}-30"

    data = {
        "tipo": "extratocontaglobaleur",
        "instituicao": "C6 Bank",
        "conta": {
            "numero": conta_numero,
            "tipo": "global",
            "moeda": "EUR",
            "agencia": agencia
        },
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "saldos": {
            "saldo_inicial": {
                "valor": 0.00,
                "data": data_inicio
            },
            "saldo_final": {
                "valor": 0.00,
                "data": data_fim
            }
        },
        "transacoes": unique_transacoes,
        "total_periodo": {
            "total_debitos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'débito'), 2),
            "total_creditos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'crédito'), 2),
            "saldo_liquido": 0.00
        }
    }

    return data

def extract_c6_global_usd(pdf_path: str, periodo: str) -> Dict[str, Any]:
    """Extract C6 Bank Global USD account statement"""

    transacoes = []
    conta_numero = ""
    agencia = "1"

    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        match = re.search(r'Conta:\s*(\d+)', text)
        if match:
            conta_numero = match.group(1)

        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue

                        if any('Data' in str(cell) for cell in row):
                            continue

                        data_lanc = row[0] if row[0] else None
                        tipo_trans = row[2] if len(row) > 2 else None
                        descricao = row[3] if len(row) > 3 else None
                        valor_str = row[4] if len(row) > 4 else None

                        if 'Saldo' in str(descricao):
                            continue

                        if not data_lanc or not descricao:
                            continue

                        data_lanc = str(data_lanc).strip()
                        if not data_lanc or len(data_lanc) < 5:
                            continue

                        valor = parse_value(valor_str)
                        if valor is None:
                            continue

                        tipo = "crédito" if valor > 0 else "débito"

                        transacoes.append({
                            "data": data_lanc,
                            "descricao": str(descricao).strip() if descricao else "",
                            "tipo": tipo,
                            "valor": abs(valor),
                            "saldo_apos": 0.00
                        })

    # Remove duplicates
    seen = set()
    unique_transacoes = []
    for t in transacoes:
        key = (t['data'], t['descricao'], t['valor'], t['tipo'])
        if key not in seen:
            seen.add(key)
            unique_transacoes.append(t)

    # Parse periodo
    if "_" in periodo:
        parts = periodo.split("_")
        data_inicio = f"20{parts[0][:2]}-{parts[0][2:4]}-01"
        data_fim = f"20{parts[1][:2]}-{parts[1][2:4]}-30"
    else:
        data_inicio = f"2025-{periodo[2:4]}-01"
        data_fim = f"2025-{periodo[2:4]}-30"

    data = {
        "tipo": "extratocontaglobalusd",
        "instituicao": "C6 Bank",
        "conta": {
            "numero": conta_numero,
            "tipo": "global",
            "moeda": "USD",
            "agencia": agencia
        },
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "saldos": {
            "saldo_inicial": {
                "valor": 0.00,
                "data": data_inicio
            },
            "saldo_final": {
                "valor": 0.00,
                "data": data_fim
            }
        },
        "transacoes": unique_transacoes,
        "total_periodo": {
            "total_debitos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'débito'), 2),
            "total_creditos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'crédito'), 2),
            "saldo_liquido": 0.00
        }
    }

    return data

def extract_c6_pj(pdf_path: str, periodo: str) -> Dict[str, Any]:
    """Extract C6 Bank PJ account statement"""

    transacoes = []
    conta_numero = ""
    agencia = "1"

    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        match = re.search(r'Conta:\s*(\d+)', text)
        if match:
            conta_numero = match.group(1)

        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue

                        if any('Data' in str(cell) for cell in row):
                            continue

                        data_lanc = row[0] if row[0] else None
                        tipo_trans = row[2] if len(row) > 2 else None
                        descricao = row[3] if len(row) > 3 else None
                        valor_str = row[4] if len(row) > 4 else None

                        if 'Saldo' in str(descricao):
                            continue

                        if not data_lanc or not descricao:
                            continue

                        data_lanc = str(data_lanc).strip()
                        if not data_lanc or len(data_lanc) < 5:
                            continue

                        valor = parse_value(valor_str)
                        if valor is None:
                            continue

                        tipo = "crédito" if valor > 0 else "débito"

                        transacoes.append({
                            "data": data_lanc,
                            "descricao": str(descricao).strip() if descricao else "",
                            "tipo": tipo,
                            "valor": abs(valor),
                            "saldo_apos": 0.00
                        })

    # Remove duplicates
    seen = set()
    unique_transacoes = []
    for t in transacoes:
        key = (t['data'], t['descricao'], t['valor'], t['tipo'])
        if key not in seen:
            seen.add(key)
            unique_transacoes.append(t)

    # Parse periodo
    if "_" in periodo:
        parts = periodo.split("_")
        data_inicio = f"20{parts[0][:2]}-{parts[0][2:4]}-01"
        data_fim = f"20{parts[1][:2]}-{parts[1][2:4]}-30"
    else:
        data_inicio = f"2025-{periodo[2:4]}-01"
        data_fim = f"2025-{periodo[2:4]}-30"

    data = {
        "tipo": "extratocontapj",
        "instituicao": "C6 Bank",
        "conta": {
            "numero": conta_numero,
            "tipo": "pj",
            "moeda": "BRL",
            "agencia": agencia
        },
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "saldos": {
            "saldo_inicial": {
                "valor": 0.00,
                "data": data_inicio
            },
            "saldo_final": {
                "valor": 0.00,
                "data": data_fim
            }
        },
        "transacoes": unique_transacoes,
        "total_periodo": {
            "total_debitos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'débito'), 2),
            "total_creditos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'crédito'), 2),
            "saldo_liquido": 0.00
        }
    }

    return data

def extract_itau_corrente(pdf_path: str, periodo: str) -> Dict[str, Any]:
    """Extract Itaú corrente account statement"""

    transacoes = []
    conta_numero = ""
    agencia = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue

                        if any('Data' in str(cell) for cell in row):
                            continue

                        data_lanc = row[0] if row[0] else None
                        tipo_trans = row[2] if len(row) > 2 else None
                        descricao = row[3] if len(row) > 3 else None
                        valor_str = row[4] if len(row) > 4 else None

                        if 'Saldo' in str(descricao):
                            continue

                        if not data_lanc or not descricao:
                            continue

                        data_lanc = str(data_lanc).strip()
                        if not data_lanc or len(data_lanc) < 5:
                            continue

                        valor = parse_value(valor_str)
                        if valor is None:
                            continue

                        tipo = "crédito" if valor > 0 else "débito"

                        transacoes.append({
                            "data": data_lanc,
                            "descricao": str(descricao).strip() if descricao else "",
                            "tipo": tipo,
                            "valor": abs(valor),
                            "saldo_apos": 0.00
                        })

    # Remove duplicates
    seen = set()
    unique_transacoes = []
    for t in transacoes:
        key = (t['data'], t['descricao'], t['valor'], t['tipo'])
        if key not in seen:
            seen.add(key)
            unique_transacoes.append(t)

    # Parse periodo
    if len(periodo) == 6:
        data_inicio = f"2025-{periodo[2:4]}-01"
        data_fim = f"2025-{periodo[2:4]}-30"
    else:
        data_inicio = f"2026-01-01"
        data_fim = f"2026-01-31"

    data = {
        "tipo": "extratoconta",
        "instituicao": "Itaú",
        "conta": {
            "numero": conta_numero,
            "tipo": "corrente",
            "moeda": "BRL",
            "agencia": agencia
        },
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "saldos": {
            "saldo_inicial": {
                "valor": 0.00,
                "data": data_inicio
            },
            "saldo_final": {
                "valor": 0.00,
                "data": data_fim
            }
        },
        "transacoes": unique_transacoes,
        "total_periodo": {
            "total_debitos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'débito'), 2),
            "total_creditos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'crédito'), 2),
            "saldo_liquido": 0.00
        }
    }

    return data

def extract_itau_personnalite(pdf_path: str, periodo: str) -> Dict[str, Any]:
    """Extract Itaú Personnalité account statement"""

    transacoes = []
    conta_numero = ""
    agencia = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue

                        if any('Data' in str(cell) for cell in row):
                            continue

                        data_lanc = row[0] if row[0] else None
                        tipo_trans = row[2] if len(row) > 2 else None
                        descricao = row[3] if len(row) > 3 else None
                        valor_str = row[4] if len(row) > 4 else None

                        if 'Saldo' in str(descricao):
                            continue

                        if not data_lanc or not descricao:
                            continue

                        data_lanc = str(data_lanc).strip()
                        if not data_lanc or len(data_lanc) < 5:
                            continue

                        valor = parse_value(valor_str)
                        if valor is None:
                            continue

                        tipo = "crédito" if valor > 0 else "débito"

                        transacoes.append({
                            "data": data_lanc,
                            "descricao": str(descricao).strip() if descricao else "",
                            "tipo": tipo,
                            "valor": abs(valor),
                            "saldo_apos": 0.00
                        })

    # Remove duplicates
    seen = set()
    unique_transacoes = []
    for t in transacoes:
        key = (t['data'], t['descricao'], t['valor'], t['tipo'])
        if key not in seen:
            seen.add(key)
            unique_transacoes.append(t)

    # Parse periodo
    if "_" in periodo:
        parts = periodo.split("_")
        data_inicio = f"20{parts[0][:2]}-{parts[0][2:4]}-01"
        data_fim = f"20{parts[1][:2]}-{parts[1][2:4]}-30"
    elif periodo.endswith('a') or periodo.endswith('b'):
        # Single month, split version
        data_inicio = f"2026-03-01"
        data_fim = f"2026-03-30"
    else:
        data_inicio = f"2025-{periodo[2:4]}-01"
        data_fim = f"2025-{periodo[2:4]}-30"

    data = {
        "tipo": "extratocontapersonnalite",
        "instituicao": "Itaú",
        "conta": {
            "numero": conta_numero,
            "tipo": "personnalite",
            "moeda": "BRL",
            "agencia": agencia
        },
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "saldos": {
            "saldo_inicial": {
                "valor": 0.00,
                "data": data_inicio
            },
            "saldo_final": {
                "valor": 0.00,
                "data": data_fim
            }
        },
        "transacoes": unique_transacoes,
        "total_periodo": {
            "total_debitos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'débito'), 2),
            "total_creditos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'crédito'), 2),
            "saldo_liquido": 0.00
        }
    }

    return data

def extract_itau_personnalite_jpg(jpg_path: str, periodo: str) -> Dict[str, Any]:
    """Extract Itaú Personnalité account statement from JPG image"""

    # Use OCR to extract text from image
    try:
        image = Image.open(jpg_path)
        text = pytesseract.image_to_string(image, lang='por')
    except Exception as e:
        print(f"Error processing JPG {jpg_path}: {e}")
        text = ""

    transacoes = []

    # Simple parsing of extracted text - extract numbers that look like values
    lines = text.split('\n')
    for line in lines:
        if re.search(r'\d{2}/\d{2}', line):
            # Try to extract date and value
            date_match = re.search(r'(\d{2}/\d{2})', line)
            value_match = re.search(r'R\$?\s*([\d.,]+)', line)

            if date_match and value_match:
                data = date_match.group(1)
                valor = parse_value(value_match.group(1))
                if valor:
                    tipo = "crédito" if valor > 0 else "débito"
                    descricao = line[date_match.end():value_match.start()].strip() if value_match else "Transfer"
                    transacoes.append({
                        "data": data,
                        "descricao": descricao,
                        "tipo": tipo,
                        "valor": abs(valor),
                        "saldo_apos": 0.00
                    })

    # Remove duplicates
    seen = set()
    unique_transacoes = []
    for t in transacoes:
        key = (t['data'], t['descricao'], t['valor'], t['tipo'])
        if key not in seen:
            seen.add(key)
            unique_transacoes.append(t)

    # Parse periodo
    data_inicio = f"2026-03-01"
    data_fim = f"2026-03-31"

    data = {
        "tipo": "extratocontapersonnalite",
        "instituicao": "Itaú",
        "conta": {
            "numero": "",
            "tipo": "personnalite",
            "moeda": "BRL",
            "agencia": ""
        },
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "saldos": {
            "saldo_inicial": {
                "valor": 0.00,
                "data": data_inicio
            },
            "saldo_final": {
                "valor": 0.00,
                "data": data_fim
            }
        },
        "transacoes": unique_transacoes,
        "total_periodo": {
            "total_debitos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'débito'), 2),
            "total_creditos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'crédito'), 2),
            "saldo_liquido": 0.00
        }
    }

    return data

def extract_picpay(pdf_path: str, periodo: str) -> Dict[str, Any]:
    """Extract PicPay account statement"""

    transacoes = []
    conta_numero = "PICPAY"
    agencia = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue

                        if any('Data' in str(cell) for cell in row):
                            continue

                        data_lanc = row[0] if row[0] else None
                        tipo_trans = row[2] if len(row) > 2 else None
                        descricao = row[3] if len(row) > 3 else None
                        valor_str = row[4] if len(row) > 4 else None

                        if 'Saldo' in str(descricao):
                            continue

                        if not data_lanc or not descricao:
                            continue

                        data_lanc = str(data_lanc).strip()
                        if not data_lanc or len(data_lanc) < 5:
                            continue

                        valor = parse_value(valor_str)
                        if valor is None:
                            continue

                        tipo = "crédito" if valor > 0 else "débito"

                        transacoes.append({
                            "data": data_lanc,
                            "descricao": str(descricao).strip() if descricao else "",
                            "tipo": tipo,
                            "valor": abs(valor),
                            "saldo_apos": 0.00
                        })

    # Remove duplicates
    seen = set()
    unique_transacoes = []
    for t in transacoes:
        key = (t['data'], t['descricao'], t['valor'], t['tipo'])
        if key not in seen:
            seen.add(key)
            unique_transacoes.append(t)

    # Parse periodo
    if "_" in periodo:
        parts = periodo.split("_")
        data_inicio = f"20{parts[0][:2]}-{parts[0][2:4]}-01"
        data_fim = f"20{parts[1][:2]}-{parts[1][2:4]}-30"
    else:
        data_inicio = f"2025-{periodo[2:4]}-01"
        data_fim = f"2025-{periodo[2:4]}-30"

    data = {
        "tipo": "extratoconta",
        "instituicao": "PicPay",
        "conta": {
            "numero": conta_numero,
            "tipo": "corrente",
            "moeda": "BRL",
            "agencia": agencia
        },
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "saldos": {
            "saldo_inicial": {
                "valor": 0.00,
                "data": data_inicio
            },
            "saldo_final": {
                "valor": 0.00,
                "data": data_fim
            }
        },
        "transacoes": unique_transacoes,
        "total_periodo": {
            "total_debitos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'débito'), 2),
            "total_creditos": round(sum(t['valor'] for t in unique_transacoes if t['tipo'] == 'crédito'), 2),
            "saldo_liquido": 0.00
        }
    }

    return data

def process_all_statements():
    """Process all bank statement files"""

    files_to_process = [
        ("c6bank_extratoconta_202603-0_original.pdf", "c6bank_extratoconta_202603-2_extract.json", extract_c6_corrente_202603, None),
        ("c6bank_extratocontaglobaleur_202511_202512-0_original.pdf", "c6bank_extratocontaglobaleur_202511_202512-2_extract.json", extract_c6_global_eur, "202511_202512"),
        ("c6bank_extratocontaglobaleur_202601_202603-0_original.pdf", "c6bank_extratocontaglobaleur_202601_202603-2_extract.json", extract_c6_global_eur, "202601_202603"),
        ("c6bank_extratocontaglobalusd_202505_202507-0_original.pdf", "c6bank_extratocontaglobalusd_202505_202507-2_extract.json", extract_c6_global_usd, "202505_202507"),
        ("c6bank_extratocontaglobalusd_202508_202510-0_original.pdf", "c6bank_extratocontaglobalusd_202508_202510-2_extract.json", extract_c6_global_usd, "202508_202510"),
        ("c6bank_extratocontaglobalusd_202511_202512-0_original.pdf", "c6bank_extratocontaglobalusd_202511_202512-2_extract.json", extract_c6_global_usd, "202511_202512"),
        ("c6bank_extratocontaglobalusd_202512_202603-0_original.pdf", "c6bank_extratocontaglobalusd_202512_202603-2_extract.json", extract_c6_global_usd, "202512_202603"),
        ("c6bank_extratocontapj_202503_202603-0_original.pdf", "c6bank_extratocontapj_202503_202603-2_extract.json", extract_c6_pj, "202503_202603"),
        ("itau_extratoconta_202507-0_original.pdf", "itau_extratoconta_202507-2_extract.json", extract_itau_corrente, "202507"),
        ("itau_extratoconta_202601-0_original.pdf", "itau_extratoconta_202601-2_extract.json", extract_itau_corrente, "202601"),
        ("itau_extratocontapersonnalite_202505_202603-0_original.pdf", "itau_extratocontapersonnalite_202505_202603-2_extract.json", extract_itau_personnalite, "202505_202603"),
        ("itau_extratocontapersonnalite_202603a-0_original.jpg", "itau_extratocontapersonnalite_202603a-2_extract.json", extract_itau_personnalite_jpg, "202603a"),
        ("itau_extratocontapersonnalite_202603b-0_original.jpg", "itau_extratocontapersonnalite_202603b-2_extract.json", extract_itau_personnalite_jpg, "202603b"),
        ("picpay_extratoconta_202512_202603-0_original.pdf", "picpay_extratoconta_202512_202603-2_extract.json", extract_picpay, "202512_202603"),
    ]

    for source_file, target_file, extractor_func, periodo in files_to_process:
        source_path = DATA_DIR / source_file
        target_path = OUTPUT_DIR / target_file

        print(f"\nProcessing: {source_file}")

        if not source_path.exists():
            print(f"  ERROR: Source file not found: {source_path}")
            continue

        try:
            if source_file.endswith('.jpg'):
                if periodo:
                    data = extractor_func(str(source_path), periodo)
                else:
                    data = extractor_func(str(source_path), "202603")
            else:
                if periodo:
                    data = extractor_func(str(source_path), periodo)
                else:
                    data = extractor_func(str(source_path))

            # Write to target
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"  OK: Extracted {len(data['transacoes'])} transactions")
            print(f"  -> {target_path}")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    process_all_statements()
    print("\n\nDone!")
