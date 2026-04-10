#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2 Fatura Extraction - Deterministic parsers for credit card invoices.

Parsers determinísticos para faturas de cartão de crédito:
  - C6 Bank Carbon CSV (faturacarbon — export CSV do internet banking)
  - C6 Bank Carbon PDF (faturacarbon)
  - Santander Unique PDF (faturaunique)
  - Santander Unique CSV (faturaunique — export CSV do internet banking)
  - Itaú Pão de Açúcar CSV (faturapaoacucar — export CSV do internet banking)
  - Itaú Pão de Açúcar PDF (faturapaoacucar — PDF fallback)
  - QuintoAndar Aluguel (faturaaluguel)

Para bancos desconhecidos, gera um JSON com flag "requires_llm_fallback": true,
para que o operador humano/LLM possa processar manualmente.

Usage:
    python scripts/e2_extract_faturas.py [--dry-run] [--file ARQUIVO.pdf|ARQUIVO.csv]
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
INBOX_DIR = BASE_DIR / "data" / "financial_statements"
OUTPUT_DIR = BASE_DIR / "processed" / "E2_extracts"

# Load family member data for name matching in parsers
def _load_family_config() -> dict:
    _fm_path = BASE_DIR / "config" / "family_members.json"
    if _fm_path.exists():
        with open(_fm_path, "r", encoding="utf-8") as _f:
            return json.load(_f)
    return {}

_FAMILY = _load_family_config()
_TITULAR_KEY = _FAMILY.get("titular", "")
_TITULAR = _FAMILY.get("membros", {}).get(_TITULAR_KEY, {})

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------
def _load_json_config(path: Path, label: str = "") -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  ⚠️  Error loading {label or path.name}: {e}")
    else:
        print(f"  [WARN] {label or path.name} não encontrado — usando defaults hardcoded")
    return {}

_LOCALE_CONFIG = _load_json_config(BASE_DIR / "config" / "localization.json", "localization.json")
_INST_CONFIG = _load_json_config(BASE_DIR / "config" / "institutions.json", "institutions.json")

# Meses PT-BR → número (string zero-padded) — from config
MESES_BR = _LOCALE_CONFIG.get("meses_br_str", {})
if not MESES_BR:
    print("  [WARN] localization.json 'meses_br_str' não encontrado — parsing de datas em português pode falhar")

# Fatura file patterns recognized by deterministic parsers — from config
KNOWN_FATURA_PATTERNS = _INST_CONFIG.get("fatura_patterns", {})
if not KNOWN_FATURA_PATTERNS:
    print("  [WARN] institutions.json 'fatura_patterns' não encontrado — nenhum parser determinístico de fatura será ativado")

# Cartão vencimentos — from config
_CARTOES = _INST_CONFIG.get("cartoes", {})
_VENC_CARBON = _CARTOES.get("faturacarbon", {}).get("dia_vencimento", 5)
_VENC_PDA = _CARTOES.get("faturapaoacucar", {}).get("dia_vencimento", 6)


# =============================================================================
# Logging
# =============================================================================

def log(level: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] E2-FATURA {level}: {msg}", file=sys.stderr)


# =============================================================================
# Utility helpers
# =============================================================================

def parse_brl(text: str) -> Optional[float]:
    """Parse a Brazilian currency string to float. '1.234,56' → 1234.56"""
    if not text:
        return None
    text = text.strip().replace("R$", "").replace("US$", "").replace("EUR", "").strip()
    text = text.replace(" ", "")
    # Handle negative: (-) 98,00 or -98,00 or (1.234,56) contábil
    negative = False
    if text.startswith("(-)") or text.startswith("-"):
        negative = True
        text = text.lstrip("(-)").strip()
    elif text.startswith("(") and text.endswith(")"):
        # Formato contábil: (1.234,56) = negativo
        negative = True
        text = text[1:-1].strip()
    # Remove thousand separator dots, replace decimal comma
    text = text.replace(".", "").replace(",", ".")
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return None


def infer_year_from_filename(filename: str) -> Optional[int]:
    """Extract year from filename like faturacarbon_202603."""
    m = re.search(r'(\d{4})\d{2}', filename)
    if m:
        return int(m.group(1))
    return None


def safe_date(year: int, month: int, day: int) -> str:
    """Retorna data ISO válida, ajustando dia se necessário."""
    import calendar
    if year < 1900 or year > 2100:
        log("WARN", f"  Ano suspeito: {year}-{month:02d}-{day:02d}")
        year = max(1900, min(2100, year))
    if month < 1 or month > 12:
        log("WARN", f"  Mês inválido: {year}-{month:02d}-{day:02d} → ajustado para mês 01")
        month = 1
    max_day = calendar.monthrange(year, month)[1]
    if day > max_day:
        log("WARN", f"  Data ajustada: {year}-{month:02d}-{day:02d} → dia {max_day}")
        day = max_day
    if day < 1:
        log("WARN", f"  Data inválida: {year}-{month:02d}-{day:02d} → dia 1")
        day = 1
    return f"{year}-{month:02d}-{day:02d}"


def resolve_date(day: int, month_str: str, ref_year: int, ref_month: int) -> str:
    """Resolve a date like '28 nov' given reference year/month of the fatura.
    If the month is after the fatura month, it's likely the previous year.
    """
    if ref_year is None or ref_month is None:
        month_num = int(MESES_BR.get(month_str.lower().strip(), '0'))
        if month_num == 0:
            log("WARN", f"  Sem ref_year/ref_month e mês não reconhecido: '{month_str}'")
            return f"{ref_year or datetime.now().year}-01-{day:02d}"
        return safe_date(ref_year or datetime.now().year, month_num, day)

    month_str_lower = month_str.lower().strip()
    month_num = int(MESES_BR.get(month_str_lower, '0'))
    if month_num == 0:
        # Try DD/MM format
        return safe_date(ref_year, ref_month, day)

    year = ref_year
    # Circular distance: handle year boundaries
    # If transaction month is more than 6 months ahead circularly, assume previous year
    forward_distance = (month_num - ref_month) % 12
    if forward_distance > 6:
        # Month is more than 6 months "ahead" circularly = likely previous year
        year -= 1

    return safe_date(year, month_num, day)


def resolve_date_ddmm(dd: int, mm: int, ref_year: int, ref_month: int) -> str:
    """Resolve DD/MM format given fatura reference."""
    if ref_year is None or ref_month is None:
        return safe_date(ref_year or datetime.now().year, mm, dd)
    year = ref_year
    if mm > ref_month + 1:
        year -= 1
    return safe_date(year, mm, dd)


# =============================================================================
# C6 Bank Carbon CSV Parser
# CSV export from C6 Bank internet banking — ZIP-protected
# Separator: semicolon (;)
# Columns: Data de Compra;Nome no Cartão;Final do Cartão;Categoria;Descrição;Parcela;Valor (em US$);Cotação (em R$);Valor (em R$)
# =============================================================================

def parse_c6_carbon_csv(csv_path: Path, filename: str) -> Dict[str, Any]:
    """Parse C6 Bank Carbon credit card invoice from CSV export.

    CSV structure:
      - No header metadata (unlike extrato CSV) — goes straight to column headers
      - Separator: semicolon (;)
      - 9 columns: Data de Compra, Nome no Cartão, Final do Cartão, Categoria,
                    Descrição, Parcela, Valor (em US$), Cotação (em R$), Valor (em R$)
      - International purchases have non-zero USD value and cotação
      - Domestic purchases have US$=0, Cotação=0
      - Payments (Inclusao de Pagamento) have negative Valor (em R$)
      - Multiple cardholders in same invoice (identified via config variantes_nome)
      - Multiple card finals (identified dynamically from PDF)
    """
    import csv as csv_mod

    log("INFO", f"Parsing C6 Carbon CSV: {filename}")

    result = {
        "banco": "C6 Bank",
        "tipo": "faturacarbon",
        "cartao": "Carbon",
        "titular": None,
        "moeda": "BRL",
        "data_vencimento": None,
        "saldo_anterior": None,
        "total_compras_nacionais": None,
        "total_compras_internacionais": None,
        "pagamentos": None,
        "saldo_atual": None,
        "limite_total": None,
        "transacoes": [],
        "cartoes": [],  # sub-cards breakdown
    }

    # Infer vencimento from filename: c6bank_faturacarbon_YYYYMM-0_original.csv
    ref_year = infer_year_from_filename(filename)
    ref_month = None
    m = re.search(r'(\d{4})(\d{2})', filename)
    if m:
        ref_year = int(m.group(1))
        ref_month = int(m.group(2))
        # C6 Carbon vencimento — day from config
        result["data_vencimento"] = safe_date(ref_year, ref_month, _VENC_CARBON)

    # Read CSV
    raw_text = csv_path.read_text(encoding="utf-8-sig")
    reader = csv_mod.reader(raw_text.splitlines(), delimiter=";")

    # Consume header
    header = next(reader, None)
    if not header or "Data de Compra" not in header[0]:
        log("WARN", f"  Header CSV inesperado: {header}")
        return result

    total_nacionais = 0.0
    total_internacionais = 0.0
    total_pagamentos = 0.0
    cards_seen = {}  # "Final XXXX - NOME" → subtotal

    for row in reader:
        if len(row) < 9:
            continue

        data_str = row[0].strip()
        nome_cartao = row[1].strip()
        final_cartao = row[2].strip()
        categoria = row[3].strip()
        descricao_raw = row[4].strip().strip('"').strip()
        parcela_str = row[5].strip()
        usd_str = row[6].strip()
        cotacao_str = row[7].strip()
        valor_brl_str = row[8].strip()

        # Validate date
        if not re.match(r'\d{2}/\d{2}/\d{4}$', data_str):
            continue

        try:
            dt = datetime.strptime(data_str, "%d/%m/%Y")
            data_iso = dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

        # Parse valor BRL
        valor_brl = _parse_fatura_csv_number(valor_brl_str)
        if valor_brl is None:
            continue

        # Build card identifier (matches PDF parser format)
        card_key = f"C6 Carbon Final {final_cartao} - {nome_cartao}"

        # Track card subtotals
        if card_key not in cards_seen:
            cards_seen[card_key] = 0.0
        cards_seen[card_key] += valor_brl

        # Detect titular from first cardholder name entry
        if result["titular"] is None and nome_cartao:
            detected = _detect_member_from_card_name(nome_cartao)
            if detected:
                result["titular"] = detected

        # Build transaction
        tx = {
            "data": data_iso,
            "descricao": descricao_raw,
            "valor": valor_brl,
            "cartao": card_key,
        }

        # Parcela
        if parcela_str and parcela_str != "Única":
            tx["parcela"] = parcela_str

        # Forex info for international purchases
        usd_val = _parse_fatura_csv_number(usd_str)
        cotacao_val = _parse_fatura_csv_number(cotacao_str)
        if usd_val and usd_val > 0:
            tx["forex"] = {
                "moeda_original": "USD",
                "valor_original": usd_val,
                "cotacao": cotacao_val,
            }
            total_internacionais += valor_brl
        elif valor_brl < 0:
            # Negative values = payments/credits
            total_pagamentos += valor_brl
        else:
            total_nacionais += valor_brl

        # Classify special transactions
        desc_lower = descricao_raw.lower()
        if "inclusao de pagamento" in desc_lower:
            tx["tipo_lancamento"] = "pagamento"
        elif "anuidade" in desc_lower:
            tx["tipo_lancamento"] = "anuidade"
        elif "estorno" in desc_lower:
            tx["tipo_lancamento"] = "estorno"
        elif "iof" in desc_lower:
            tx["tipo_lancamento"] = "iof"

        result["transacoes"].append(tx)

    # Populate summary fields
    result["total_compras_nacionais"] = round(total_nacionais, 2) if total_nacionais else None
    result["total_compras_internacionais"] = round(total_internacionais, 2) if total_internacionais else None
    result["pagamentos"] = round(total_pagamentos, 2) if total_pagamentos else None

    # saldo_atual = sum of all transactions
    if result["transacoes"]:
        result["saldo_atual"] = round(sum(t["valor"] for t in result["transacoes"]), 2)

    # Cards summary
    for card_name, subtotal in cards_seen.items():
        result["cartoes"].append({
            "cartao": card_name,
            "subtotal": round(subtotal, 2),
        })

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas do CSV")
    if result["saldo_atual"] is not None:
        log("INFO", f"  → Saldo atual: R$ {result['saldo_atual']:.2f}")
    log("INFO", f"  → Cartões: {len(cards_seen)}")

    return result


def _parse_fatura_csv_number(text: str) -> Optional[float]:
    """Parse number from C6 fatura CSV. Handles '1234.56', '-1234.56', '0'."""
    if not text or not text.strip():
        return None
    text = text.strip()
    try:
        val = float(text)
        return val
    except ValueError:
        # Fallback to BRL format
        return parse_brl(text)


def _detect_member_from_card_name(nome_cartao: str) -> Optional[str]:
    """Match card holder name to family member using config data."""
    nome_upper = nome_cartao.upper()
    for mid, mdata in _FAMILY.get("membros", {}).items():
        for variant in mdata.get("variantes_nome", []):
            # Check if the card name is a prefix/substring of a known variant
            if nome_upper in variant.upper() or variant.upper().startswith(nome_upper):
                return mdata.get("variantes_nome", [variant])[0]
    return None


# =============================================================================
# Santander Unique CSV Parser
# CSV export from Santander internet banking
# Separator: comma (,)
# Columns: data,lançamento,valor
# Date format: YYYY-MM-DD
# Valor: decimal point, negative for payments/credits
# File has UTF-8 BOM
# =============================================================================

def parse_santander_fatura_csv(csv_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Santander Unique credit card invoice from CSV export.

    CSV structure:
      - UTF-8 BOM header
      - Separator: comma (,)
      - 3 columns: data, lançamento, valor
      - Date format: YYYY-MM-DD
      - Valor: float with dot as decimal separator
      - Negative values = payments (PAGAMENTO EFETUADO) or credits (ESTORNO)
      - Positive values = purchases/charges
    """
    import csv as csv_mod

    log("INFO", f"Parsing Santander Unique CSV: {filename}")

    result = {
        "banco": "Santander",
        "tipo": "faturaunique",
        "cartao": "Unique",
        "titular": None,
        "moeda": "BRL",
        "data_vencimento": None,
        "saldo_anterior": None,
        "total_compras": None,
        "pagamentos": None,
        "saldo_atual": None,
        "transacoes": [],
        "cartoes": [],
    }

    # Infer vencimento from filename: santander_faturaunique_YYYYMM-0_original.csv
    ref_year = infer_year_from_filename(filename)
    ref_month = None
    m = re.search(r'(\d{4})(\d{2})', filename)
    if m:
        ref_year = int(m.group(1))
        ref_month = int(m.group(2))
        # Santander Unique vencimento is typically day 06 of the fatura month
        result["data_vencimento"] = safe_date(ref_year, ref_month, 6)

    # Read CSV (handle BOM)
    raw_text = csv_path.read_text(encoding="utf-8-sig")
    reader = csv_mod.reader(raw_text.splitlines(), delimiter=",")

    # Consume header
    header = next(reader, None)
    if not header or "data" not in header[0].lower():
        log("WARN", f"  Header CSV inesperado: {header}")
        return result

    total_compras = 0.0
    total_pagamentos = 0.0

    for row in reader:
        if len(row) < 3:
            continue

        data_str = row[0].strip()
        descricao = row[1].strip()
        valor_str = row[2].strip()

        if not data_str or not valor_str:
            continue

        # Parse date (YYYY-MM-DD format)
        date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', data_str)
        if not date_match:
            # Try DD/MM/YYYY fallback
            date_match2 = re.match(r'(\d{2})/(\d{2})/(\d{4})', data_str)
            if date_match2:
                iso_date = f"{date_match2.group(3)}-{date_match2.group(2)}-{date_match2.group(1)}"
            else:
                log("WARN", f"  Data não reconhecida: {data_str}")
                continue
        else:
            iso_date = data_str

        # Parse valor (dot as decimal separator in CSV)
        try:
            valor = float(valor_str)
        except ValueError:
            # Try Brazilian format (1.234,56)
            val = parse_brl(valor_str)
            if val is not None:
                valor = val
            else:
                log("WARN", f"  Valor não reconhecido: {valor_str}")
                continue

        # Classify: negative = payment/credit, positive = purchase/debit
        if valor < 0:
            total_pagamentos += valor
            tipo_txn = "pagamento" if "PAGAMENTO" in descricao.upper() else "estorno"
        else:
            total_compras += valor
            tipo_txn = "compra"

        # Detect IOF
        if "IOF" in descricao.upper():
            tipo_txn = "iof"

        txn = {
            "data": iso_date,
            "descricao": descricao,
            "valor": round(abs(valor), 2),
            "tipo": tipo_txn,
        }
        # Keep sign convention: purchases positive, payments negative
        if valor < 0:
            txn["valor"] = -round(abs(valor), 2)

        result["transacoes"].append(txn)

    # Summary
    result["total_compras"] = round(total_compras, 2) if total_compras else None
    result["pagamentos"] = round(total_pagamentos, 2) if total_pagamentos else None
    saldo = total_compras + total_pagamentos
    result["saldo_atual"] = round(saldo, 2)

    n_txns = len(result["transacoes"])
    log("INFO", f"  → {n_txns} transações, saldo R$ {saldo:,.2f}")

    # Parse quality
    if n_txns > 0:
        result["parse_quality"] = "ok"
    else:
        result["parse_quality"] = "empty_csv"
        log("WARN", f"  CSV vazio (0 transações): {filename}")

    return result


# =============================================================================
# C6 Bank Carbon Parser (PDF)
# =============================================================================

def parse_c6_carbon(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse C6 Bank Carbon credit card invoice."""
    log("INFO", f"Parsing C6 Carbon: {filename}")

    result = {
        "banco": "C6 Bank",
        "tipo": "faturacarbon",
        "cartao": "Carbon",
        "titular": None,
        "moeda": "BRL",
        "data_vencimento": None,
        "saldo_anterior": None,
        "total_compras_nacionais": None,
        "total_compras_internacionais": None,
        "pagamentos": None,
        "saldo_atual": None,
        "limite_total": None,
        "transacoes": [],
        "cartoes": [],  # sub-cards breakdown
    }

    ref_year = infer_year_from_filename(filename)
    ref_month = None
    m = re.search(r'(\d{4})(\d{2})', filename)
    if m:
        ref_year = int(m.group(1))
        ref_month = int(m.group(2))

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

            full_text = "\n".join(all_text)

            # --- Extract header info ---
            # Titular
            _c6_regex = _TITULAR.get("regex_nome_fatura", {}).get("c6_carbon", "")
            m = re.search(_c6_regex, full_text) if _c6_regex else None
            if m:
                result["titular"] = _TITULAR.get("variantes_nome", [_TITULAR.get("nome_completo", "")])[0]

            # Vencimento: "05 de Março" or "Vencimento: 05 de Março"
            m = re.search(r'[Vv]encimento[:\s]+(\d{1,2})\s+de\s+(\w+)', full_text)
            if m and ref_year:
                day = int(m.group(1))
                month_name = m.group(2).lower()
                month_num = MESES_BR.get(month_name)
                if month_num:
                    result["data_vencimento"] = f"{ref_year}-{month_num}-{day:02d}"

            # Valor total: "R$ 41.406,31" near "Valor da fatura"
            m = re.search(r'Valor da fatura:\s*R\$\s*([\d.,]+)', full_text)
            if m:
                result["saldo_atual"] = parse_brl(m.group(1))

            # Limite total
            m = re.search(r'Limite total:\s*R\$\s*([\d.,]+)', full_text)
            if m:
                result["limite_total"] = parse_brl(m.group(1))

            # Resumo da fatura - compras nacionais/internacionais
            m = re.search(r'Compras nacionais\s+([\d.,]+)', full_text)
            if m:
                result["total_compras_nacionais"] = parse_brl(m.group(1))
            m = re.search(r'Compras internacionais\s+([\d.,]+)', full_text)
            if m:
                result["total_compras_internacionais"] = parse_brl(m.group(1))

            # Estornos/créditos
            m = re.search(r'Estornos\s*/\s*Crédito na Fatura\s+\(?\-?\)?\s*([\d.,]+)', full_text)
            if m:
                result["pagamentos"] = -parse_brl(m.group(1))

            # --- Extract transactions ---
            # Pattern: "DD mmm  DESCRIPTION  [USD info | Cotação...]  VALUE"
            # Transaction lines have format: "28 nov AIR EUROPA LINEAS AE - Parcela 3/3 2.747,60"
            # or with forex: "01 fev HOTEL MUNDIAL USD 156,74 | Cotação USD: R$5,47 857,01"

            current_card_name = None
            current_card_subtotal = None

            tx_pattern = re.compile(
                r'^(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s+'
                r'(.+?)\s+'
                r'([\d.,]+)\s*$',
                re.MULTILINE
            )

            # Card header: "C6 Carbon Virtual Final XXXX - CARDHOLDER NAME"
            card_pattern = re.compile(
                r'C6 Carbon\s+(?:Virtual\s+)?Final\s+(\d{4})\s*-\s*(.+?)(?:\s+Cartão|\s+Subtotal)',
                re.IGNORECASE
            )

            subtotal_pattern = re.compile(
                r'Subtotal deste cartão\s+R\$\s*([\d.,]+)',
                re.IGNORECASE
            )

            cards_seen = {}

            for page in all_text:
                lines = page.split('\n')

                for line in lines:
                    # Check for card header
                    card_m = card_pattern.search(line)
                    if card_m:
                        current_card_name = f"C6 Carbon Final {card_m.group(1)} - {card_m.group(2).strip()}"

                    sub_m = subtotal_pattern.search(line)
                    if sub_m and current_card_name:
                        current_card_subtotal = parse_brl(sub_m.group(1))
                        if current_card_name not in cards_seen:
                            cards_seen[current_card_name] = current_card_subtotal

                    # Match transaction line
                    tx_m = tx_pattern.match(line.strip())
                    if tx_m:
                        day = int(tx_m.group(1))
                        month_str = tx_m.group(2)
                        raw_desc = tx_m.group(3).strip()
                        valor = parse_brl(tx_m.group(4))

                        if valor is None:
                            continue

                        # Resolve date
                        date_str = resolve_date(day, month_str, ref_year, ref_month)

                        # Parse forex info from description
                        forex_info = None
                        parcela = None
                        descricao = raw_desc

                        # Extract forex: "USD 156,74 | Cotação USD: R$5,47"
                        forex_m = re.search(
                            r'(USD|EUR)\s+([\d.,]+)\s*\|\s*Cotação\s+\w+:\s*R\$\s*([\d.,]+)',
                            raw_desc
                        )
                        if forex_m:
                            forex_info = {
                                "moeda_original": forex_m.group(1),
                                "valor_original": parse_brl(forex_m.group(2)),
                                "cotacao": parse_brl(forex_m.group(3)),
                            }
                            descricao = raw_desc[:forex_m.start()].strip()

                        # IOF marker
                        iof_m = re.search(r'IOF Transações Exterior', raw_desc)
                        if iof_m:
                            descricao = raw_desc[:iof_m.start()].strip()
                            if not descricao:
                                # IOF line without merchant name - use previous tx's merchant
                                descricao = "IOF Transações Exterior"

                        # Extract parcela: "- Parcela 3/3"
                        parcela_m = re.search(r'-\s*Parcela\s+(\d+/\d+)', raw_desc)
                        if parcela_m:
                            parcela = parcela_m.group(1)
                            descricao = raw_desc[:parcela_m.start()].strip()

                        tx = {
                            "data": date_str,
                            "descricao": descricao,
                            "valor": valor,
                            "cartao": current_card_name,
                        }
                        if parcela:
                            tx["parcela"] = parcela
                        if forex_info:
                            tx["forex"] = forex_info
                        if iof_m and not forex_m:
                            tx["tipo_lancamento"] = "iof"

                        result["transacoes"].append(tx)

            # Build cards summary
            for card_name, subtotal in cards_seen.items():
                result["cartoes"].append({
                    "cartao": card_name,
                    "subtotal": subtotal,
                })

        log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    except Exception as e:
        log("ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    return result


# =============================================================================
# Santander Unique Parser
# =============================================================================

def parse_santander_unique(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Santander Unique credit card invoice."""
    log("INFO", f"Parsing Santander Unique: {filename}")

    ref_year = infer_year_from_filename(filename)
    ref_month = None
    m = re.search(r'(\d{4})(\d{2})', filename)
    if m:
        ref_year = int(m.group(1))
        ref_month = int(m.group(2))

    result = {
        "banco": "Santander",
        "tipo": "faturaunique",
        "cartao": "Unique",
        "titular": None,
        "moeda": "BRL",
        "data_vencimento": None,
        "saldo_anterior": None,
        "total_compras": None,
        "pagamentos": None,
        "saldo_atual": None,
        "transacoes": [],
        "cartoes": [],
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

            full_text = "\n".join(all_text)

            # --- Header ---
            _unique_regex = _TITULAR.get("regex_nome_fatura", {}).get("santander_unique", "")
            m = re.search(_unique_regex, full_text) if _unique_regex else None
            if m:
                result["titular"] = m.group(0).strip()

            # Total a Pagar + Vencimento: Santander layout has headers on one line,
            # values on another: "Total a Pagar  Vencimento  Melhor Data..."
            #                    "R$ 372,85      15/01/2026  10/02/2026"
            m = re.search(r'R\$\s*([\d.,]+)\s+(\d{2}/\d{2}/\d{4})\s+\d{2}/\d{2}/\d{4}', full_text)
        if m:
            result["saldo_atual"] = parse_brl(m.group(1))
            venc_parts = m.group(2).split("/")
            if len(venc_parts) == 3:
                result["data_vencimento"] = f"{venc_parts[2]}-{venc_parts[1]}-{venc_parts[0]}"

        # Fallback: try simpler patterns
        if result["saldo_atual"] is None:
            m = re.search(r'R\$\s*([\d.,]+)\s+\d{2}/\d{2}/\d{4}', full_text)
            if m:
                result["saldo_atual"] = parse_brl(m.group(1))
        if result["saldo_atual"] is None:
            m = re.search(r'Total a Pagar\s*\n?\s*R\$\s*([\d.,]+)', full_text)
            if m:
                result["saldo_atual"] = parse_brl(m.group(1))
        if result["data_vencimento"] is None and ref_year and ref_month:
            # Fallback: buscar data DD/MM/YYYY que seja coerente com ref_year/ref_month
            candidates = re.findall(r'(\d{2})/(\d{2})/(\d{4})', full_text)
            for dd, mm, yyyy in candidates:
                if int(yyyy) == ref_year and int(mm) == ref_month:
                    result["data_vencimento"] = f"{yyyy}-{mm}-{dd}"
                    break
            # Se nenhuma data do mês correto, usar ref_year-ref_month-15 como estimativa
            if result["data_vencimento"] is None:
                result["data_vencimento"] = f"{ref_year}-{ref_month:02d}-15"
                log("WARN", f"  Vencimento estimado (sem match exato): {result['data_vencimento']}")

        # Saldo Anterior
        m = re.search(r'Saldo Anterior\s+([\d.,]+)', full_text)
        if m:
            result["saldo_anterior"] = parse_brl(m.group(1))

        # Total Despesas
        m = re.search(r'Total Despesas/Débitos no Brasil\s+([\d.,]+)', full_text)
        if m:
            result["total_compras"] = parse_brl(m.group(1))

        # Total pagamentos (sempre negativo por convenção — reduzem saldo da fatura)
        m = re.search(r'Total de pagamentos\s+([\d.,]+)', full_text)
        if m:
            val = parse_brl(m.group(1))
            result["pagamentos"] = -abs(val) if val else None

        # --- Transactions by card holder ---
        # pdfplumber merges left+right columns into single lines, so we need
        # to handle "polluted" lines where right-column text is appended.
        #
        # Card sections: "CARDHOLDER NAME - XXXX XXXX XXXX XXXX"
        # Transactions: "[prefix] DD/MM DESCRIPTION VALUE [USD_VALUE]"
        # Prefix can be "1 " or "□ " from checkbox icons

        card_section_pattern = re.compile(
            r'(?:@ )?([A-ZÇÃÕÉ][A-ZÇÃÕÉ\s]+?)\s*-\s*(\d{4}\s+XXXX\s+XXXX\s+\d{4})',
        )

        # Transaction pattern — allows optional leading "1 " or similar prefix,
        # optional negative sign, and trailing junk from right column
        tx_pattern = re.compile(
            r'^\s*(?:\d\s+)?(\d{2}/\d{2})\s+(.+?)\s+(-?[\d.,]+)(?:\s+([\d.,]+))?\s*(?:\s+\(\+\).*|\s+\(\-\).*|\s+\(=\).*)?$'
        )

        detail_start = full_text.find("Detalhamento da Fatura")
        if detail_start < 0:
            detail_start = 0
        detail_text = full_text[detail_start:]

        current_card = None
        current_section_type = None

        for line in detail_text.split('\n'):
            # Check for card header
            card_m = card_section_pattern.search(line)
            if card_m:
                current_card = f"{card_m.group(1).strip()} - {card_m.group(2).strip()}"

            # Check section type
            if 'Pagamento' in line and ('Créditos' in line or 'pagamentos' in line.lower()):
                current_section_type = "pagamento"
            elif re.match(r'^\s*Despesas\s*$', line):
                current_section_type = "despesas"

            if not current_card:
                continue

            # IOF DESPESA NO EXTERIOR (standalone line, no date)
            if 'IOF DESPESA NO EXTERIOR' in line and not re.match(r'\s*\d{2}/\d{2}', line):
                iof_m = re.search(r'IOF DESPESA NO EXTERIOR\s+([\d.,]+)', line)
                if iof_m:
                    # IOF has no date in the PDF; prefer date of preceding transaction
                    iof_date = result.get("data_vencimento")
                    if result.get("transacoes") and len(result["transacoes"]) > 0:
                        last_tx = result["transacoes"][-1]
                        if last_tx.get("data"):
                            iof_date = last_tx["data"]
                    result["transacoes"].append({
                        "data": iof_date,
                        "descricao": "IOF DESPESA NO EXTERIOR",
                        "valor": parse_brl(iof_m.group(1)),
                        "cartao": current_card,
                        "tipo_lancamento": "iof",
                    })
                continue

            # TRY TRANSACTION MATCH FIRST (before skips), because pdfplumber
            # merges right-column text onto transaction lines
            tx_m = tx_pattern.match(line)
            if tx_m:
                date_parts = tx_m.group(1).split("/")
                dd = int(date_parts[0])
                mm = int(date_parts[1])

                raw_desc = tx_m.group(2).strip()
                valor_str = tx_m.group(3).strip()
                valor_brl = parse_brl(valor_str)
                valor_usd = parse_brl(tx_m.group(4)) if tx_m.group(4) and tx_m.group(4).strip() else None

                if valor_brl is None:
                    continue

                # Clean right-column junk from description
                # e.g. "SCP COMPLETO- DEZ/25 26,34 (+) Total Despesas..." → chop at "(+)"
                for junk in [' (+)', ' (-)', ' (=)', ' Saldo', ' Total']:
                    idx = raw_desc.find(junk)
                    if idx > 0:
                        raw_desc = raw_desc[:idx].strip()

                date_str = resolve_date_ddmm(dd, mm, ref_year, ref_month)

                is_payment = current_section_type == "pagamento" or valor_brl < 0

                tx = {
                    "data": date_str,
                    "descricao": raw_desc,
                    "valor": valor_brl,
                    "cartao": current_card,
                }
                if valor_usd:
                    tx["forex"] = {"moeda_original": "USD", "valor_original": valor_usd}

                result["transacoes"].append(tx)

        log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    except Exception as e:
        log("ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    return result


# =============================================================================
# Itaú Pão de Açúcar Parser
# =============================================================================

def parse_itau_paoacucar(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú Pão de Açúcar credit card invoice.

    Key challenge: pdfplumber merges left and right columns into single lines.
    The "Lançamentos" table (left) and "Encargos" table (right) get concatenated.
    We handle this by matching transaction patterns at the START of lines and
    truncating any right-column junk.
    """
    log("INFO", f"Parsing Itaú Pão de Açúcar: {filename}")

    ref_year = infer_year_from_filename(filename)
    ref_month = None
    m = re.search(r'(\d{4})(\d{2})', filename)
    if m:
        ref_year = int(m.group(1))
        ref_month = int(m.group(2))

    result = {
        "banco": "Itaú",
        "tipo": "faturapaoacucar",
        "cartao": "Pão de Açúcar",
        "titular": None,
        "moeda": "BRL",
        "data_vencimento": None,
        "saldo_anterior": None,
        "total_compras": None,
        "pagamentos": None,
        "saldo_atual": None,
        "transacoes": [],
        "compras_parceladas_futuras": [],
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        full_text = "\n".join(all_text)

        # --- Header ---
        _itau_regex = _TITULAR.get("regex_nome_fatura", {}).get("itau_paoacucar", "")
        m = re.search(_itau_regex, full_text) if _itau_regex else None
        if m:
            result["titular"] = m.group(1)

        m = re.search(r'Vencimento:\s*(\d{2}/\d{2}/\d{4})', full_text)
        if m:
            parts = m.group(1).split("/")
            result["data_vencimento"] = f"{parts[2]}-{parts[1]}-{parts[0]}"

        m = re.search(r'Total desta fatura\s+([\d.,]+)', full_text)
        if m:
            result["saldo_atual"] = parse_brl(m.group(1))

        m = re.search(r'Total da fatura anterior\s+([\d.,]+)', full_text)
        if m:
            result["saldo_anterior"] = parse_brl(m.group(1))

        # Pagamentos (sempre negativo por convenção)
        m = re.search(r'Pagamento efetuado em \d+/\d+/\d+\s+(-?\s*[\d.,]+)', full_text)
        if m:
            val = parse_brl(m.group(1))
            result["pagamentos"] = -abs(val) if val else None

        m = re.search(r'Lançamentos atuais\s+([\d.,]+)', full_text)
        if m:
            result["total_compras"] = parse_brl(m.group(1))

        m = re.search(r'Cartão\s+([\d.X]+)', full_text)
        if m:
            result["numero_cartao"] = m.group(1)

        # --- Transactions ---
        # Pattern: "DD/MM  ESTABLISHMENT [parcela_info]  VALUE  [right-column junk]"
        # The right-column junk starts with text like "Juros", "Multa", numbers, etc.
        # Key: match DD/MM at start, then grab description+value greedily,
        # then handle the fact that the VALUE is followed by junk.

        # Transaction regex: captures DD/MM, then everything up to a number pattern
        # that represents the value. We need to find the FIRST standalone number
        # after the description.
        tx_pattern = re.compile(
            r'(?:@\s*)?(\d{2}/\d{2})\s+'                  # date
            r'(.+?)\s+'                                     # description (lazy)
            r'(\d{1,2}/\d{1,2})\s+'                        # parcela (NN/NN)
            r'([\d.,]+)'                                    # value
        )
        # Simpler pattern without parcela
        tx_simple = re.compile(
            r'(?:@\s*)?(\d{2}/\d{2})\s+'                  # date
            r'(.+?)\s+'                                     # description (lazy)
            r'([\d.,]+)'                                    # value
        )

        current_card = None
        in_lancamentos = False
        in_parceladas = False

        for line in full_text.split('\n'):
            # Detect sections
            if 'Lançamentos: compras e saques' in line or 'Lançamentos:compras e saques' in line:
                in_lancamentos = True
                in_parceladas = False
                continue
            if 'Lançamentos internacionais' in line:
                # Seção internacional é parte dos lançamentos atuais
                in_lancamentos = True
                in_parceladas = False
                continue
            if 'Compras parceladas' in line and 'próximas faturas' in line:
                in_lancamentos = False
                in_parceladas = True
                continue
            # Stop markers — mas apenas se a linha NÃO contém também um card header
            # ou transação (pdfplumber merge de colunas pode colocar stop markers
            # na mesma linha que dados válidos)
            has_card_header = bool(re.search(r'\(final\s+\d+\)', line))
            has_tx_date = bool(re.match(r'\s*(?:@\s*)?\d{2}/\d{2}\s', line.strip()))
            if not has_card_header and not has_tx_date:
                if any(s in line for s in ['Fique atento', 'Continua...',
                                            'Pagamentos em', 'lojas são aceitos', 'apenas em dinheiro',
                                            'cartão de débito', 'Não são aceitos']):
                    in_lancamentos = False
                    in_parceladas = False
                    continue
                # "Limites de crédito" sozinho (não embutido em right-column junk)
                if re.match(r'^\s*Limites de crédito\s*$', line):
                    in_lancamentos = False
                    in_parceladas = False
                    continue

            if not (in_lancamentos or in_parceladas):
                continue

            # Card sub-header: "CARDHOLDER NAME (final XXXX)"
            card_m = re.search(r'([A-Z][\w\s]+)\(final\s+(\d+)\)', line)
            if card_m:
                current_card = f"{card_m.group(1).strip()} (final {card_m.group(2)})"
                # Don't continue — line might also contain tx data from right-column merge

            # TRY TRANSACTION MATCH FIRST (before skips), because pdfplumber
            # merges right-column text (Encargos) onto transaction lines.
            # e.g. "08/06 BRASIL PARAL*Bras 07/12 59,00 Juros de mora 1,00 % am 0,00"

            # Try to match transaction with parcela first
            matched = False
            tx_m = tx_pattern.match(line.strip())
            if tx_m:
                dd, mm_str = tx_m.group(1).split("/")
                raw_desc = tx_m.group(2).strip()
                parcela = tx_m.group(3)
                valor = parse_brl(tx_m.group(4))

                if valor is not None:
                    date_str = resolve_date_ddmm(int(dd), int(mm_str), ref_year, ref_month)
                    tx = {
                        "data": date_str,
                        "descricao": raw_desc,
                        "valor": valor,
                        "cartao": current_card,
                        "parcela": parcela,
                    }
                    if in_parceladas:
                        result["compras_parceladas_futuras"].append(tx)
                    else:
                        result["transacoes"].append(tx)
                    matched = True

            if not matched:
                # Simple pattern without parcela
                tx_m = tx_simple.match(line.strip())
                if tx_m:
                    dd, mm_str = tx_m.group(1).split("/")
                    raw_desc = tx_m.group(2).strip()
                    valor = parse_brl(tx_m.group(3))

                    if valor is not None and valor != 0:
                        date_str = resolve_date_ddmm(int(dd), int(mm_str), ref_year, ref_month)
                        tx = {
                            "data": date_str,
                            "descricao": raw_desc,
                            "valor": valor,
                            "cartao": current_card,
                        }
                        if in_parceladas:
                            result["compras_parceladas_futuras"].append(tx)
                        else:
                            result["transacoes"].append(tx)

        log("INFO", f"  → {len(result['transacoes'])} transações, {len(result['compras_parceladas_futuras'])} parceladas futuras")
    except Exception as e:
        log("ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    return result


# =============================================================================
# Parser: Itaú Pão de Açúcar CSV (faturapaoacucar)
# CSV export from Itaú internet banking — BOM-prefixed, 3 columns
#
# Structure:
#   Header: data,lançamento,valor (with UTF-8 BOM)
#   Rows: YYYY-MM-DD,DESCRIPTION,DECIMAL_VALUE
#   Values: plain decimals (not Brazilian formatted), negative = payment
#   Filename: fatura-YYYYMMDD.csv (date = due date; 99999999 = open invoice)
# =============================================================================

def parse_itau_paoacucar_csv(csv_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú Pão de Açúcar credit card invoice from CSV export.

    CSV structure:
      - UTF-8 BOM header
      - 3 columns: data, lançamento, valor
      - Dates already in ISO format (YYYY-MM-DD)
      - Values as plain decimals (negative = payments/credits)
      - Filename encodes due date: fatura-YYYYMMDD.csv
    """
    log("INFO", f"Parsing Itaú Pão de Açúcar CSV: {filename}")

    # Infer vencimento from filename: fatura-YYYYMMDD.csv or itau_faturapaoacucar_YYYYMM...csv
    data_vencimento = None
    is_fatura_aberta = False

    # Pattern: fatura-YYYYMMDD.csv (original upload name)
    m = re.search(r'fatura-(\d{8})', filename)
    if m:
        date_str = m.group(1)
        if date_str == "99999999":
            is_fatura_aberta = True
        else:
            y, mo, d = date_str[:4], date_str[4:6], date_str[6:8]
            data_vencimento = f"{y}-{mo}-{d}"

    # Pattern: itau_faturapaoacucar_YYYYMM-0_original.csv (pipeline naming)
    if not data_vencimento and not is_fatura_aberta:
        m = re.search(r'(\d{4})(\d{2})', filename)
        if m:
            ref_year, ref_month = int(m.group(1)), int(m.group(2))
            # Fatura Itaú PdA — day from config
            data_vencimento = f"{ref_year}-{ref_month:02d}-{_VENC_PDA:02d}"

    result = {
        "banco": "Itaú",
        "tipo": "faturapaoacucar",
        "cartao": "Pão de Açúcar",
        "titular": None,
        "moeda": "BRL",
        "data_vencimento": data_vencimento,
        "saldo_anterior": None,
        "total_compras": None,
        "pagamentos": None,
        "saldo_atual": None,
        "transacoes": [],
        "compras_parceladas_futuras": [],
    }

    if is_fatura_aberta:
        result["notas"] = ["Fatura aberta (em aberto, ainda não fechada)"]

    try:
        # Read CSV with BOM handling
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

        if not lines:
            log("WARN", f"  CSV vazio: {filename}")
            return result

        # Parse header
        header = lines[0].strip().lower()
        if 'data' not in header or 'valor' not in header:
            log("WARN", f"  Header CSV inesperado: {header}")
            result["notas"] = result.get("notas", []) + [f"Header inesperado: {header}"]
            return result

        # Parse data rows
        total_pagamentos = 0.0
        total_compras = 0.0

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            # CSV simple split (no commas in values, descriptions may have commas
            # but in practice Itaú doesn't use them in descriptions)
            # Use a more robust approach: split from right for the value
            parts = line.split(',')
            if len(parts) < 3:
                continue

            # Date is first field, value is last field, description is everything in between
            data = parts[0].strip()
            valor_str = parts[-1].strip()
            descricao = ','.join(parts[1:-1]).strip()

            # Validate date format YYYY-MM-DD
            if not re.match(r'\d{4}-\d{2}-\d{2}$', data):
                continue

            # Parse value
            try:
                valor = float(valor_str)
            except ValueError:
                valor = parse_brl(valor_str)
                if valor is None:
                    continue

            # Detect parcela from description: "STORE NAME NN/NN"
            parcela = None
            parcela_m = re.search(r'(\d{1,2}/\d{1,2})$', descricao)
            if parcela_m:
                parcela = parcela_m.group(1)

            # Classify transaction
            desc_upper = descricao.upper()
            is_pagamento = "PAGAMENTO EFETUADO" in desc_upper
            is_estorno = "ESTORNO" in desc_upper

            tx = {
                "data": data,
                "descricao": descricao,
                "valor": valor,
            }
            if parcela:
                tx["parcela"] = parcela

            result["transacoes"].append(tx)

            # Accumulate totals
            if is_pagamento:
                total_pagamentos += valor
            elif valor < 0 and not is_estorno:
                # Negative values that aren't estornos are also payments/credits
                total_pagamentos += valor
            else:
                # Positive values and estornos (negative refunds) count as compras
                total_compras += valor

        # Set derived totals
        if total_pagamentos != 0:
            result["pagamentos"] = total_pagamentos
        if total_compras != 0:
            result["total_compras"] = total_compras

        # Saldo atual = total compras + pagamentos
        result["saldo_atual"] = round(total_compras + total_pagamentos, 2) if result["transacoes"] else None

        # Itaú CSV doesn't include cardholder info — default to primary titular
        if not result["titular"]:
            result["titular"] = _TITULAR.get("variantes_nome", [_TITULAR.get("nome_completo")])[0]

    except Exception as e:
        log("ERROR", f"  Falha ao processar CSV {filename}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas do CSV")
    return result


# =============================================================================
# QuintoAndar Aluguel Parser
# =============================================================================

def parse_quintoandar(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse QuintoAndar rental invoice."""
    log("INFO", f"Parsing QuintoAndar: {filename}")

    ref_year = infer_year_from_filename(filename)
    ref_month = None
    m = re.search(r'(\d{4})(\d{2})', filename)
    if m:
        ref_year = int(m.group(1))
        ref_month = int(m.group(2))

    # Extract property name from filename
    prop_m = re.search(r'faturaaluguel(\w+?)_\d{6}', filename)
    propriedade = prop_m.group(1) if prop_m else "desconhecida"

    result = {
        "banco": "QuintoAndar",
        "tipo": "faturaaluguel",
        "propriedade": propriedade,
        "moeda": "BRL",
        "periodo_referencia": f"{ref_year}-{ref_month:02d}" if ref_year and ref_month else None,
        "total_recebido": None,
        "itens": [],
        "data_recebimento": None,
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        full_text = "\n".join(all_text)

        # Property address
        m = re.search(r'Faturas de aluguel\s*\n(.+)', full_text)
        if m:
            result["endereco"] = m.group(1).strip()

        # Total recebido
        m = re.search(r'Total de\s*\n?\s*R\$\s*([\d.,]+)', full_text)
        if m:
            result["total_recebido"] = parse_brl(m.group(1))

        # Data de recebimento: "Receber até DD/MM/YYYY"
        m = re.search(r'[Rr]eceber até\s+(\d{2}/\d{2}/\d{4})', full_text)
        if m:
            parts = m.group(1).split("/")
            result["data_recebimento"] = f"{parts[2]}-{parts[1]}-{parts[0]}"

        # Line items: "Aluguel - Fev/2026 R$ 2.000,00"
        # or negative: "Taxa de administração - Quinto Andar -R$ 186,00"
        item_pattern = re.compile(
            r'(.+?)\s+(-?R\$\s*[\d.,]+)',
        )

        # Headers/footers a rejeitar SOMENTE se não houver match de item válido
        SKIP_EXACT = {'total de', 'subtotal', 'você recebe', 'recebido'}

        for line in full_text.split('\n'):
            stripped = line.strip()
            # Tentar match primeiro — antes de aplicar skip-list
            item_m = item_pattern.match(stripped)
            if item_m:
                desc = item_m.group(1).strip()
                valor_str = item_m.group(2).strip()
                valor = parse_brl(valor_str)

                if valor is not None and desc and len(desc) > 3:
                    # Rejeitar apenas descrições que são claramente headers
                    if desc.lower().strip() in SKIP_EXACT:
                        continue
                    result["itens"].append({
                        "descricao": desc,
                        "valor": valor,
                    })

        log("INFO", f"  → {len(result['itens'])} itens extraídos")
    except Exception as e:
        log("ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    return result


# =============================================================================
# LLM Fallback Stub
# =============================================================================

def generate_llm_fallback(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Generate a stub JSON for unknown fatura types, flagged for LLM processing."""
    log("WARN", f"Unknown fatura format: {filename} — flagging for LLM fallback")

    text_preview = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:3]:
                t = page.extract_text()
                if t:
                    text_preview += t + "\n"
    except Exception:
        pass

    return {
        "tipo": "fatura_desconhecida",
        "arquivo_origem": filename,
        "requires_llm_fallback": True,
        "texto_extraido_preview": text_preview[:5000],
        "transacoes": [],
        "nota": "Banco/formato não reconhecido pelo parser determinístico. Requer processamento LLM.",
    }


# =============================================================================
# Post-parse validation
# =============================================================================

def validate_parse_result(result: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Adiciona metadata de qualidade ao resultado do parse."""
    saldo = result.get("saldo_atual") or 0
    txns = len(result.get("transacoes", []))
    itens = len(result.get("itens", []))
    venc = result.get("data_vencimento", "")

    if saldo == 0 and txns == 0 and itens == 0 and not venc:
        result["parse_quality"] = "empty_result"
        log("WARN", f"  Resultado completamente vazio para {filename} — verificar PDF")
    elif saldo > 0 and txns == 0 and itens == 0:
        result["parse_quality"] = "missing_transactions"
        log("WARN", f"  Saldo R$ {saldo:.2f} mas 0 transações para {filename}")
    else:
        result["parse_quality"] = "ok"

    return result


# =============================================================================
# Router: identifies fatura type and dispatches to parser
# =============================================================================

def identify_and_parse(file_path: Path) -> Optional[Dict[str, Any]]:
    """Identify fatura type from filename and dispatch to appropriate parser."""
    filename = file_path.name

    # C6 Carbon CSV (priority over PDF)
    if re.search(r'c6bank_faturacarbon.*\.csv$', filename, re.IGNORECASE):
        return parse_c6_carbon_csv(file_path, filename)

    # C6 Carbon PDF
    if re.search(r'c6bank_faturacarbon', filename, re.IGNORECASE):
        return parse_c6_carbon(file_path, filename)

    # Santander Unique CSV (priority over PDF)
    if re.search(r'santander_faturaunique.*\.csv$', filename, re.IGNORECASE):
        return parse_santander_fatura_csv(file_path, filename)

    # Santander Unique PDF
    if re.search(r'santander_faturaunique', filename, re.IGNORECASE):
        return parse_santander_unique(file_path, filename)

    # Itaú Pão de Açúcar CSV (priority over PDF)
    if re.search(r'itau_faturapaoacucar.*\.csv$', filename, re.IGNORECASE):
        return parse_itau_paoacucar_csv(file_path, filename)

    # Itaú Pão de Açúcar PDF
    if re.search(r'itau_faturapaoacucar', filename, re.IGNORECASE):
        return parse_itau_paoacucar(file_path, filename)

    # QuintoAndar Aluguel
    if re.search(r'quintoandar_faturaaluguel', filename, re.IGNORECASE):
        return parse_quintoandar(file_path, filename)

    # Unknown → LLM fallback (only for PDFs)
    if filename.endswith(".csv"):
        log("WARN", f"CSV não reconhecido: {filename}")
        return {
            "tipo": "fatura_desconhecida",
            "arquivo_origem": filename,
            "requires_llm_fallback": True,
            "transacoes": [],
            "nota": "Formato CSV não reconhecido. Requer análise manual.",
        }
    return generate_llm_fallback(file_path, filename)


# =============================================================================
# Main
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="E2 Fatura Extraction - Deterministic Parsers")
    parser.add_argument("--dry-run", action="store_true", help="Preview sem salvar")
    parser.add_argument("--file", type=str, help="Processar apenas um arquivo específico (PDF ou CSV)")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR), help="Diretório de saída")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect fatura PDFs and CSVs
    if args.file:
        files = [Path(args.file)]
    else:
        # Find all fatura files in inbox (PDF and CSV)
        files = []
        for ext in ("pdf", "csv"):
            for p in sorted(INBOX_DIR.glob(f"*fatura*-0_original.{ext}")):
                files.append(p)
        # Warn about non-renamed files (missing -0_original suffix)
        non_standard = []
        for p in sorted(INBOX_DIR.glob("*fatura*.*")):
            if "-0_original" not in p.name and p.suffix.lower() in (".pdf", ".csv"):
                non_standard.append(p.name)
        if non_standard:
            log("WARN", f"{len(non_standard)} arquivo(s) fatura sem sufixo -0_original (ignorados):")
            for name in non_standard:
                log("WARN", f"  → {name}")

    if not files:
        log("WARN", "Nenhuma fatura encontrada para processar.")
        return

    log("INFO", f"Encontradas {len(files)} faturas para processar")

    stats = {"total": 0, "sucesso": 0, "fallback": 0, "erro": 0, "txn_total": 0}

    for pdf_path in files:
        stats["total"] += 1
        filename = pdf_path.name

        try:
            result = identify_and_parse(pdf_path)

            if result is None:
                log("WARN", f"  Skipped: {filename}")
                continue

            # Validate parse quality
            if not result.get("requires_llm_fallback"):
                result = validate_parse_result(result, filename)

            # Count transactions
            txn_count = len(result.get("transacoes", []))
            txn_count += len(result.get("itens", []))  # QuintoAndar
            stats["txn_total"] += txn_count

            if result.get("requires_llm_fallback"):
                stats["fallback"] += 1
            else:
                stats["sucesso"] += 1

            # Generate output filename
            # e.g., c6bank_faturacarbon_202603-0_original.{pdf,csv} → c6bank_faturacarbon_202603-2_extract.json
            # Robusto: remove qualquer variação de -0_original antes de .pdf ou .csv
            out_name = re.sub(r'(-0_original)?\.(pdf|csv)$', '-2_extract.json', filename, flags=re.IGNORECASE)

            out_path = output_dir / out_name

            if args.dry_run:
                log("DRY-RUN", f"  Would write: {out_path.name} ({txn_count} txns)")
                # Print sample
                sample = json.dumps(result, ensure_ascii=False, indent=2)
                if len(sample) > 1000:
                    print(sample[:1000] + "\n... [truncated]")
                else:
                    print(sample)
                print()
            else:
                # Overwrite protection: don't replace a JSON with transactions
                # with a new result that has 0 transactions
                if txn_count == 0 and out_path.exists():
                    try:
                        existing = json.loads(out_path.read_text(encoding='utf-8'))
                        existing_txns = len(existing.get("transacoes", []))
                        if existing_txns > 0:
                            log("WARN", f"  SKIP: {out_path.name} já tem {existing_txns} txns; "
                                f"não sobrescrever com resultado de 0 txns")
                            stats["sucesso"] += 0  # don't count as success
                            continue
                    except (json.JSONDecodeError, IOError):
                        pass  # existing file is corrupt/empty, OK to overwrite

                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                log("OK", f"  Saved: {out_path.name} ({txn_count} txns)")

        except Exception as e:
            stats["erro"] += 1
            log("ERROR", f"  Failed: {filename} — {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)

    # Summary
    print("\n" + "=" * 60, file=sys.stderr)
    log("SUMMARY", f"Total: {stats['total']} | OK: {stats['sucesso']} | Fallback LLM: {stats['fallback']} | Erro: {stats['erro']}")
    log("SUMMARY", f"Transações extraídas: {stats['txn_total']}")
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    main()
