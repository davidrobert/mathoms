#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2 Extrato Extraction - Deterministic parsers for bank statements.

Parsers determinísticos para extratos bancários. Segue a mesma arquitetura
do e2_extract_faturas.py — um parser por banco, roteamento por filename,
fallback LLM para bancos desconhecidos.

Bancos suportados (TABLE_READY — pdfplumber tables):
  - C6 Bank: extratoconta, extratocontapj, extratocontaglobalusd, extratocontaglobaleur
  - Itaú: extratoconta, extratocontapersonnalite
  - PicPay: extratoconta

Bancos suportados (TEXT_REGEX — regex sobre texto extraído):
  - Bradesco: extratoconta, extratopoupanca
  - Santander: extratoconta
  - BTG Pactual: extratoconta
  - Rico: extratoconta
  - Wise: extratocontausd, extratocontabrl
  - Bank of America: extratoconta

Usage:
    python scripts/e2_extract_extratos.py [--dry-run] [--file ARQUIVO.pdf]

Author: Claude Opus 4.6
"""

import calendar
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# Configuration — loaded from project config files, never hardcoded
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "financial_statements"
OUTPUT_DIR = BASE_DIR / "processed" / "E2_extracts"
CONFIG_DIR = BASE_DIR / "config"


def _load_family_config() -> dict:
    """Load family_members.json for name matching (used in header parsing)."""
    fm_path = CONFIG_DIR / "family_members.json"
    if fm_path.exists():
        with open(fm_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


_FAMILY = _load_family_config()
_MEMBROS = _FAMILY.get("membros", {})

# Build a lookup of all known member names and CPFs from config
_MEMBER_NAMES: List[str] = []
_MEMBER_CPFS: Dict[str, str] = {}  # cpf → member_id
for _mid, _mdata in _MEMBROS.items():
    for variant in _mdata.get("variantes_nome", []):
        _MEMBER_NAMES.append(variant)
    cpf = _mdata.get("cpf", "")
    if cpf:
        _MEMBER_CPFS[cpf] = _mid

# Meses PT-BR → número
MESES_BR = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4,
    'mai': 5, 'jun': 6, 'jul': 7, 'ago': 8,
    'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
}

# Extrato file patterns recognized by deterministic parsers
# Maps (banco_prefix, tipo_contains) → parser function name
# Populated at module level after parser definitions

# =============================================================================
# Logging
# =============================================================================

_VERBOSE = True


def log(level: str, msg: str) -> None:
    if not _VERBOSE and level == "DEBUG":
        return
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] E2-EXTRATO {level}: {msg}", file=sys.stderr)


# =============================================================================
# Utility helpers (shared with e2_extract_faturas.py patterns)
# =============================================================================

def parse_brl(text: str) -> Optional[float]:
    """Parse Brazilian currency string to float. '1.234,56' → 1234.56, '-R$ 98,00' → -98.0"""
    if not text:
        return None
    text = str(text).strip()
    # Remove currency symbols
    for sym in ("R$", "US$", "EUR", "USD", "BRL", "$"):
        text = text.replace(sym, "")
    text = text.strip()
    if not text or text == "-":
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    elif text.startswith("-") or text.startswith("(-"):
        negative = True
        text = text.lstrip("(-").rstrip(")").strip()

    # Brazilian format: 1.234,56 → remove dots, comma→dot
    text = text.replace(".", "").replace(",", ".")
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return None


def safe_date(year: int, month: int, day: int) -> str:
    """Return valid ISO date string, adjusting day if necessary."""
    year = max(1900, min(2100, year))
    if month < 1 or month > 12:
        log("WARN", f"  Mês inválido: {year}-{month:02d}-{day:02d} → mês 01")
        month = 1
    max_day = calendar.monthrange(year, month)[1]
    if day > max_day:
        day = max_day
    if day < 1:
        day = 1
    return f"{year}-{month:02d}-{day:02d}"


def infer_periodo_from_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract periodo start/end from filename patterns like _202501_202512 or _202603."""
    # Pattern: banco_tipo_YYYYMM_YYYYMM-0_original.pdf
    m = re.search(r'_(\d{4})(\d{2})_(\d{4})(\d{2})', filename)
    if m:
        y1, m1, y2, m2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        inicio = safe_date(y1, m1, 1)
        fim_day = calendar.monthrange(y2, m2)[1]
        fim = safe_date(y2, m2, fim_day)
        return inicio, fim

    # Pattern: banco_tipo_YYYYMM-0_original.pdf (single month)
    m = re.search(r'_(\d{4})(\d{2})(?:[a-z])?-', filename)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        inicio = safe_date(y, mo, 1)
        fim_day = calendar.monthrange(y, mo)[1]
        fim = safe_date(y, mo, fim_day)
        return inicio, fim

    return None, None


def detect_member_from_text(text: str) -> Optional[str]:
    """Try to identify which family member owns this statement, using config names/CPFs."""
    text_upper = text.upper()
    for cpf, mid in _MEMBER_CPFS.items():
        if cpf in text:
            return mid
    for mid, mdata in _MEMBROS.items():
        for variant in mdata.get("variantes_nome", []):
            if variant.upper() in text_upper:
                return mid
    return None


def extract_account_number(text: str, banco: str) -> Optional[str]:
    """Extract account number from statement text using common patterns."""
    patterns = [
        r'[Cc]onta[:\s]+(\d[\d.\-/]+\d)',
        r'[Aa]gência[:\s]+\d+\s*[\|/•]\s*[Cc]onta[:\s]+(\d[\d.\-]+\d)',
        r'Account\s*(?:number|#)?[:\s]+(\d[\d\s]+\d)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return None


def make_result_template(banco: str, tipo: str, moeda: str = "BRL") -> Dict[str, Any]:
    """Create a standard E2 result dictionary."""
    return {
        "banco": banco,
        "tipo": tipo,
        "moeda": moeda,
        "numero_conta": None,
        "titular": None,
        "periodo": {"inicio": None, "fim": None},
        "saldo_inicial": None,
        "saldo_final": None,
        "transacoes": [],
        "notas": [],
    }


def resolve_year_from_period(dd: int, mm: int, periodo_inicio: str, periodo_fim: str) -> int:
    """Given a transaction DD/MM, resolve which year it belongs to based on periodo."""
    if not periodo_inicio:
        return datetime.now().year
    start_year = int(periodo_inicio[:4])
    end_year = int(periodo_fim[:4]) if periodo_fim else start_year
    if start_year == end_year:
        return start_year
    # If the month is >= start month of start_year, use start_year
    start_month = int(periodo_inicio[5:7])
    if mm >= start_month:
        return start_year
    return end_year


# =============================================================================
# Parser: C6 Bank (extratoconta, extratocontapj, extratocontaglobal*)
# TABLE_READY — pdfplumber extract_tables() works well
# =============================================================================

def parse_c6bank(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse C6 Bank statement (conta, contapj, contaglobal)."""
    # Detect subtype from filename
    is_global_usd = "extratocontaglobalusd" in filename
    is_global_eur = "extratocontaglobaleur" in filename
    is_pj = "extratocontapj" in filename

    if is_global_usd:
        moeda = "USD"
        tipo = "extratocontaglobalusd"
    elif is_global_eur:
        moeda = "EUR"
        tipo = "extratocontaglobaleur"
    elif is_pj:
        moeda = "BRL"
        tipo = "extratocontapj"
    else:
        moeda = "BRL"
        tipo = "extratoconta"

    log("INFO", f"Parsing C6 Bank ({tipo}): {filename}")
    result = make_result_template("C6 Bank", tipo, moeda)

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extract header info from first page text
            first_text = pdf.pages[0].extract_text() or ""
            result["titular"] = detect_member_from_text(first_text)
            result["numero_conta"] = extract_account_number(first_text, "c6bank")

            # Parse periodo from header text (more precise than filename)
            # Pattern: "Período • DD de MÊS de YYYY até DD de MÊS de YYYY"
            periodo_pat = re.compile(
                r'Período\s*•?\s*(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+'
                r'até\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
                re.IGNORECASE
            )
            pm = periodo_pat.search(first_text)
            if pm:
                d1 = int(pm.group(1))
                m1 = MESES_BR.get(pm.group(2).lower(), 0)
                y1 = int(pm.group(3))
                d2 = int(pm.group(4))
                m2 = MESES_BR.get(pm.group(5).lower(), 0)
                y2 = int(pm.group(6))
                if m1 and m2:
                    result["periodo"]["inicio"] = safe_date(y1, m1, d1)
                    result["periodo"]["fim"] = safe_date(y2, m2, d2)

            # Extract saldo from header
            # Pattern: "Saldo do dia • DD de MÊS de YYYY • R$ 6.930,11"
            saldo_header = re.search(
                r'Saldo do dia.*?[•\s]+(R\$|US\$|EUR)\s*([\d.,]+)',
                first_text
            )

            # Check for "Sem lançamentos no mês" (empty period)
            full_text = "\n".join(
                (p.extract_text() or "") for p in pdf.pages
            )
            if "Sem lançamentos no mês" in full_text or "sem lançamentos" in full_text.lower():
                empty_months = full_text.lower().count("sem lançamentos")
                result["notas"].append(
                    f"Sem lançamentos no período ({empty_months} mês(es) sem movimentação)"
                )

            # Parse all tables across all pages
            all_rows: List[Tuple[str, str, str, str, str]] = []
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and len(row) >= 4:
                            all_rows.append(tuple(str(c) if c else "" for c in row))

            # C6 Bank has two table formats:
            # Conta/PJ: [data_lancamento, data_contabil, tipo, descricao, valor_BRL]
            # Global:    [data, tipo, descricao, valor_FX, autorizacao]
            # The Global format has currency prefixes in valor (e.g. "-US$ 25,38")
            # and an authorization column instead of data_contabil
            is_global = is_global_usd or is_global_eur

            pending_tx: Optional[Dict] = None
            saldo_values: List[Tuple[str, float]] = []

            for row in all_rows:
                # Normalize: ensure 5 columns
                cols = list(row) + [""] * (5 - len(row))
                col0, col1, col2, col3, col4 = cols[:5]

                # For Global format, valor is in col3 (with currency prefix)
                # For Conta/PJ format, valor is in col4
                if is_global:
                    valor_col = col3
                    desc_col = col2
                    tipo_col = col1
                else:
                    valor_col = col4
                    desc_col = col3
                    tipo_col = col2

                # Skip empty/header rows
                if not any(c.strip() for c in cols):
                    continue

                # Detect "Saldo do dia" rows
                saldo_match = re.match(r'Saldo do dia\s+(\d{2}/\d{2}/\d{2,4})', col0)
                if saldo_match:
                    saldo_val = parse_brl(col4) or parse_brl(col3)
                    if saldo_val is not None:
                        date_str = saldo_match.group(1)
                        saldo_values.append((date_str, saldo_val))
                    # Flush pending tx
                    if pending_tx:
                        result["transacoes"].append(pending_tx)
                        pending_tx = None
                    continue

                # Transaction row: has date in col0 (DD/MM) and value in valor_col
                date_match = re.match(r'(\d{2}/\d{2})', col0.strip())
                has_value = valor_col.strip() and parse_brl(valor_col) is not None

                if date_match and has_value:
                    # Flush previous pending
                    if pending_tx:
                        result["transacoes"].append(pending_tx)

                    dd, mm_str = date_match.group(1).split("/")
                    dd_i, mm_i = int(dd), int(mm_str)
                    year = resolve_year_from_period(
                        dd_i, mm_i,
                        result["periodo"]["inicio"] or "",
                        result["periodo"]["fim"] or ""
                    )
                    valor = parse_brl(valor_col)

                    pending_tx = {
                        "data": safe_date(year, mm_i, dd_i),
                        "descricao": desc_col.strip(),
                        "valor": valor,
                        "tipo_lancamento": tipo_col.strip() if tipo_col.strip() else None,
                    }
                    continue

                if date_match and not has_value:
                    # Row with date but no value — next row likely has value
                    if pending_tx:
                        result["transacoes"].append(pending_tx)

                    dd, mm_str = date_match.group(1).split("/")
                    dd_i, mm_i = int(dd), int(mm_str)
                    year = resolve_year_from_period(
                        dd_i, mm_i,
                        result["periodo"]["inicio"] or "",
                        result["periodo"]["fim"] or ""
                    )
                    pending_tx = {
                        "data": safe_date(year, mm_i, dd_i),
                        "descricao": desc_col.strip(),
                        "valor": None,
                        "tipo_lancamento": tipo_col.strip() if tipo_col.strip() else None,
                    }
                    continue

                # Continuation row (no date in col0)
                if not date_match and (tipo_col.strip() or desc_col.strip()):
                    val = parse_brl(valor_col)
                    if pending_tx and pending_tx["valor"] is None and val is not None:
                        # This row carries the value for the pending tx
                        pending_tx["valor"] = val
                        if desc_col.strip() and not pending_tx["descricao"]:
                            pending_tx["descricao"] = desc_col.strip()
                        result["transacoes"].append(pending_tx)
                        pending_tx = None
                    elif val is not None:
                        # Standalone continuation with value — new transaction inheriting date
                        if pending_tx:
                            result["transacoes"].append(pending_tx)
                        prev_date = result["transacoes"][-1]["data"] if result["transacoes"] else None
                        pending_tx = None
                        result["transacoes"].append({
                            "data": prev_date,
                            "descricao": desc_col.strip(),
                            "valor": val,
                            "tipo_lancamento": tipo_col.strip() if tipo_col.strip() else None,
                        })
                    elif pending_tx and desc_col.strip():
                        # Description continuation
                        pending_tx["descricao"] += " " + desc_col.strip()

            # Flush last pending
            if pending_tx:
                result["transacoes"].append(pending_tx)

            # Remove transactions with None valor
            result["transacoes"] = [t for t in result["transacoes"] if t.get("valor") is not None]

            # Derive saldo_inicial and saldo_final from saldo rows
            if saldo_values:
                result["saldo_inicial"] = saldo_values[0][1]
                result["saldo_final"] = saldo_values[-1][1]

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: Itaú (extratoconta, extratocontapersonnalite)
# TABLE_READY — many small 1-row tables per page
# =============================================================================

def parse_itau(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú bank statement."""
    is_personnalite = "personnalite" in filename.lower()
    tipo = "extratocontapersonnalite" if is_personnalite else "extratoconta"

    log("INFO", f"Parsing Itaú ({tipo}): {filename}")
    result = make_result_template("Itaú", tipo, "BRL")

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_text = pdf.pages[0].extract_text() or ""
            result["titular"] = detect_member_from_text(first_text)
            result["numero_conta"] = extract_account_number(first_text, "itau")

            # Parse periodo from header: "Período: DD/MM/YYYY a DD/MM/YYYY"
            pm = re.search(r'Per[ií]odo[:\s]+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', first_text)
            if pm:
                parts1 = pm.group(1).split("/")
                parts2 = pm.group(2).split("/")
                result["periodo"]["inicio"] = f"{parts1[2]}-{parts1[1]}-{parts1[0]}"
                result["periodo"]["fim"] = f"{parts2[2]}-{parts2[1]}-{parts2[0]}"

            # Itaú produces many small tables, each typically 1 row
            # Format: [data, lancamentos, valor, saldo]
            # "SALDO DO DIA" entries have empty valor and saldo in col 3
            all_tables: List[list] = []
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    all_tables.extend(table)

            saldo_values: List[Tuple[str, float]] = []

            for row in all_tables:
                if not row or len(row) < 3:
                    continue
                cols = [str(c).strip() if c else "" for c in row]

                # Pad to 4 columns
                while len(cols) < 4:
                    cols.append("")

                date_str, descricao, valor_str, saldo_str = cols[0], cols[1], cols[2], cols[3]

                # Skip header row
                if date_str.lower() in ("data", ""):
                    if descricao.lower() in ("lançamentos", "lancamentos", ""):
                        continue

                # Skip empty rows
                if not date_str and not descricao:
                    continue

                # Parse date
                date_match = re.match(r'(\d{2}/\d{2}/\d{4})', date_str)
                if not date_match:
                    continue

                parts = date_match.group(1).split("/")
                iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"

                # "SALDO DO DIA" rows
                if "SALDO DO DIA" in descricao.upper():
                    saldo_val = parse_brl(saldo_str) or parse_brl(valor_str)
                    if saldo_val is not None:
                        saldo_values.append((iso_date, saldo_val))
                    continue

                # Regular transaction
                valor = parse_brl(valor_str)
                if valor is None:
                    continue

                result["transacoes"].append({
                    "data": iso_date,
                    "descricao": descricao,
                    "valor": valor,
                })

            # Derive saldos
            if saldo_values:
                # Sort by date
                saldo_values.sort(key=lambda x: x[0])
                result["saldo_inicial"] = saldo_values[0][1]
                result["saldo_final"] = saldo_values[-1][1]

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: PicPay (extratoconta)
# TABLE_READY — perfect 5-column tables
# =============================================================================

def parse_picpay(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse PicPay bank statement."""
    log("INFO", f"Parsing PicPay: {filename}")
    result = make_result_template("PicPay", "extratoconta", "BRL")

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_text = pdf.pages[0].extract_text() or ""
            result["titular"] = detect_member_from_text(first_text)

            # Account number
            m = re.search(r'Conta[:\s]+(\d+)', first_text)
            if m:
                result["numero_conta"] = m.group(1)

            # Periodo from header: "MOVIMENTAÇÕES DD DE MÊS DE YYYY A DD DE MÊS DE YYYY"
            pm = re.search(
                r'MOVIMENTA[ÇC][ÕO]ES\s+(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})\s+A\s+'
                r'(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})',
                first_text, re.IGNORECASE
            )
            if pm:
                d1, m1_name, y1 = int(pm.group(1)), pm.group(2).lower(), int(pm.group(3))
                d2, m2_name, y2 = int(pm.group(4)), pm.group(5).lower(), int(pm.group(6))
                m1 = MESES_BR.get(m1_name, 0)
                m2 = MESES_BR.get(m2_name, 0)
                if m1 and m2:
                    result["periodo"]["inicio"] = safe_date(y1, m1, d1)
                    result["periodo"]["fim"] = safe_date(y2, m2, d2)

            # PicPay tables: [Data/Hora, Descrição, Valor, Saldo, Saldo Sacável]
            saldo_first = None
            saldo_last = None

            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 4:
                            continue
                        cols = [str(c).strip() if c else "" for c in row]

                        # Skip header
                        if "Data/Hora" in cols[0] or "Descrição" in cols[1]:
                            continue

                        # Parse date from "DD/MM/YYYY\nHH:MM:SS"
                        date_match = re.match(r'(\d{2}/\d{2}/\d{4})', cols[0])
                        if not date_match:
                            continue

                        parts = date_match.group(1).split("/")
                        iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        descricao = cols[1]
                        valor = parse_brl(cols[2])
                        saldo = parse_brl(cols[3])

                        if valor is None:
                            continue

                        result["transacoes"].append({
                            "data": iso_date,
                            "descricao": descricao,
                            "valor": valor,
                        })

                        if saldo is not None:
                            if saldo_first is None:
                                saldo_first = saldo
                            saldo_last = saldo

            # PicPay lists newest first; transactions should be oldest first
            result["transacoes"].reverse()

            # Derive saldos (last in list = oldest = initial, first = newest = final)
            if saldo_first is not None:
                result["saldo_final"] = saldo_first
            if saldo_last is not None:
                result["saldo_inicial"] = saldo_last

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: Bradesco (extratoconta, extratopoupanca)
# TEXT_REGEX — multi-line text format
# =============================================================================

def parse_bradesco(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Bradesco bank statement (conta corrente or poupança)."""
    is_poupanca = "poupanca" in filename.lower()
    tipo = "extratopoupanca" if is_poupanca else "extratoconta"

    log("INFO", f"Parsing Bradesco ({tipo}): {filename}")
    result = make_result_template("Bradesco", tipo, "BRL")

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Combine all pages text
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"

            result["titular"] = detect_member_from_text(all_text)

            # Account: "Ag: 3221 | Conta: 77113-9"
            m = re.search(r'Ag[:\s]+(\d+)\s*\|\s*Conta[:\s]+([\d-]+)', all_text)
            if m:
                result["numero_conta"] = f"Ag {m.group(1)} Conta {m.group(2)}"

            # Periodo: "Entre DD/MM/YYYY e DD/MM/YYYY"
            pm = re.search(r'Entre\s+(\d{2}/\d{2}/\d{4})\s+e\s+(\d{2}/\d{2}/\d{4})', all_text)
            if pm:
                p1 = pm.group(1).split("/")
                p2 = pm.group(2).split("/")
                result["periodo"]["inicio"] = f"{p1[2]}-{p1[1]}-{p1[0]}"
                result["periodo"]["fim"] = f"{p2[2]}-{p2[1]}-{p2[0]}"

            # Bradesco format: transaction lines are multi-line blocks
            # Date line: DD/MM/YY at start
            # Then historico, docto, credito, debito, saldo on various lines
            #
            # Pattern: "DD/MM/YY historico docto [credito] [- debito] [saldo]"
            # Continuation lines have no date prefix
            # Values appear at end of line: "1.808,49" for credit, "- 1.500,00" for debit
            # Saldo appears after credit/debit: "1.809,49" or "1,00"

            lines = all_text.split("\n")
            transactions: List[Dict] = []
            saldo_anterior = None
            current_date = None

            # Find SALDO ANTERIOR
            for line in lines:
                m = re.match(r'(\d{2}/\d{2}/\d{2})\s+SALDO ANTERIOR\s+([\d.,]+)', line)
                if m:
                    saldo_anterior = parse_brl(m.group(2))
                    dd, mm, yy = m.group(1).split("/")
                    yy_full = 2000 + int(yy) if int(yy) < 50 else 1900 + int(yy)
                    result["saldo_inicial"] = saldo_anterior
                    break

            # Main transaction pattern for Bradesco:
            # Line starts with DD/MM/YY followed by historico and numbers
            # Numbers at the end: [credit] [- debit] [saldo]
            # The tricky part is distinguishing credit vs debit vs saldo
            #
            # Key insight: Bradesco always shows saldo at the end
            # If "- VALUE" appears, it's a debit
            # A standalone value before saldo could be credit

            tx_date_pattern = re.compile(
                r'^(\d{2}/\d{2}/\d{2})\s+(.*)'
            )

            # Parse transaction blocks
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                dm = tx_date_pattern.match(line)

                if dm:
                    date_str = dm.group(1)
                    rest = dm.group(2).strip()
                    dd, mm, yy = date_str.split("/")
                    yy_full = 2000 + int(yy) if int(yy) < 50 else 1900 + int(yy)
                    current_date = safe_date(yy_full, int(mm), int(dd))

                    # Skip SALDO ANTERIOR line
                    if "SALDO ANTERIOR" in rest:
                        i += 1
                        continue

                    # Extract all values from the line
                    # Pattern: text followed by number sequences
                    # Look for credit (positive), debit (with -), and saldo
                    values_in_line = re.findall(r'(-?\s*[\d.,]+)', rest)

                    # The historico is everything before the first number
                    hist_match = re.match(r'(.+?)\s+(-?\s*\d[\d.,]*)', rest)
                    if hist_match:
                        historico = hist_match.group(1).strip()
                    else:
                        historico = rest.strip()

                    # Determine if this line has a complete transaction
                    # Bradesco: debit marked with "- VALUE", credit is just "VALUE"
                    # Saldo is always last number on line with amount
                    debit_match = re.search(r'-\s+([\d.,]+)\s+([\d.,]+)\s*$', rest)
                    credit_match = re.search(r'(\d[\d.,]*)\s+([\d.,]+)\s*$', rest)

                    if debit_match:
                        # "- DEBIT SALDO" at end
                        valor = -parse_brl(debit_match.group(1))
                        if valor is not None:
                            transactions.append({
                                "data": current_date,
                                "descricao": historico,
                                "valor": valor,
                            })
                    elif credit_match:
                        # Need to distinguish credit from docto number
                        # If there are >= 2 number-like values, first might be docto
                        nums = re.findall(r'[\d.,]+', rest)
                        if len(nums) >= 2:
                            # Last is saldo, second-to-last might be value
                            possible_val = parse_brl(nums[-2])
                            possible_saldo = parse_brl(nums[-1])
                            # Check if the number appears after "- " (debit)
                            if re.search(r'-\s+' + re.escape(nums[-2]), rest):
                                if possible_val is not None:
                                    transactions.append({
                                        "data": current_date,
                                        "descricao": historico,
                                        "valor": -possible_val,
                                    })
                            elif possible_val is not None and possible_val != possible_saldo:
                                # Credit: value appears before saldo without "-"
                                # But need to avoid docto numbers (7-digit)
                                raw = nums[-2].replace(".", "").replace(",", "")
                                if len(raw) <= 6:  # likely a monetary value, not docto
                                    transactions.append({
                                        "data": current_date,
                                        "descricao": historico,
                                        "valor": possible_val,
                                    })

                elif current_date:
                    # Continuation line (no date) — may contain a sub-transaction
                    # Pattern: "Historico DOCTO - VALUE SALDO"
                    if line and not line.startswith("Data ") and not line.startswith("Bradesco"):
                        debit_m = re.search(r'-\s+([\d.,]+)\s+([\d.,]+)\s*$', line)
                        credit_m = re.search(r'(\d[\d.,]+)\s+([\d.,]+)\s*$', line)

                        if debit_m:
                            hist = re.match(r'(.+?)\s+-\s+[\d.,]+', line)
                            desc = hist.group(1).strip() if hist else line.strip()
                            # Clean docto from description
                            desc = re.sub(r'\s+\d{7}\s*$', '', desc).strip()
                            valor = -parse_brl(debit_m.group(1))
                            if valor is not None and abs(valor) > 0.001:
                                transactions.append({
                                    "data": current_date,
                                    "descricao": desc,
                                    "valor": valor,
                                })
                        elif credit_m:
                            nums = re.findall(r'[\d.,]+', line)
                            if len(nums) >= 2:
                                possible_val = parse_brl(nums[-2])
                                possible_saldo = parse_brl(nums[-1])
                                if (possible_val is not None and possible_saldo is not None
                                        and possible_val != possible_saldo):
                                    raw = nums[-2].replace(".", "").replace(",", "")
                                    if len(raw) <= 6:
                                        hist = line[:line.rfind(nums[-2])].strip()
                                        hist = re.sub(r'\s+\d{7}\s*$', '', hist).strip()
                                        if hist:
                                            transactions.append({
                                                "data": current_date,
                                                "descricao": hist,
                                                "valor": possible_val,
                                            })

                i += 1

            result["transacoes"] = transactions

            # Try to find saldo final from "Total" line or last saldo
            total_match = re.search(r'Total\s+([\d.,]+)\s+-\s+([\d.,]+)\s+([\d.,]+)', all_text)
            if total_match:
                result["saldo_final"] = parse_brl(total_match.group(3))

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: Santander (extratoconta)
# TEXT_REGEX — clean single-line format
# =============================================================================

def parse_santander_conta(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Santander bank account statement."""
    log("INFO", f"Parsing Santander Conta: {filename}")
    result = make_result_template("Santander", "extratoconta", "BRL")

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"

            result["titular"] = detect_member_from_text(all_text)

            # Account: "Agência e Conta: 1652 / 01001341-6"
            m = re.search(r'Ag[êe]ncia\s+e\s+Conta[:\s]+([\d\s/\-]+)', all_text)
            if m:
                result["numero_conta"] = m.group(1).strip()

            # Periodo: "Período: DD/MM/YYYY a DD/MM/YYYY"
            pm = re.search(r'Per[ií]odo[:\s]+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', all_text)
            if pm:
                p1 = pm.group(1).split("/")
                p2 = pm.group(2).split("/")
                result["periodo"]["inicio"] = f"{p1[2]}-{p1[1]}-{p1[0]}"
                result["periodo"]["fim"] = f"{p2[2]}-{p2[1]}-{p2[0]}"

            # Check for "SALDO ANTERIOR" only with no transactions
            # If only "SALDO ANTERIOR" line exists on page 1 and no other transaction
            # lines, this is a period without activity
            saldo_ant_match = re.search(
                r'(\d{2}/\d{2}/\d{4})\s+SALDO ANTERIOR\s+(-?[\d.,]+)',
                all_text
            )
            if saldo_ant_match:
                result["saldo_inicial"] = parse_brl(saldo_ant_match.group(2))

            # Santander format: each line is a complete transaction
            # "DD/MM/YYYY DESCRIÇÃO DOCTO SITUAÇÃO CRÉDITO DÉBITO SALDO"
            # Credit appears as positive number, Debit as negative with "-"
            # Example: "06/02/2026 PIX RECEBIDO DAVID... 000000 5.000,00 118,34"
            # Example: "06/02/2026 DEBITO AUT. TELEFONE... 000000 -338,00 -4.881,66"

            tx_pattern = re.compile(
                r'^(\d{2}/\d{2}/\d{4})\s+'  # Date
                r'(.+?)\s+'                   # Description
                r'(\d{6})\s*'                 # Docto (6 digits)
                r'(-?[\d.,]+)\s+'             # Value (credit positive, debit negative)
                r'(-?[\d.,]+)\s*$',           # Saldo
                re.MULTILINE
            )

            saldo_values: List[Tuple[str, float]] = []

            for m in tx_pattern.finditer(all_text):
                date_parts = m.group(1).split("/")
                iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                descricao = m.group(2).strip()
                valor = parse_brl(m.group(4))
                saldo = parse_brl(m.group(5))

                if valor is None:
                    continue

                result["transacoes"].append({
                    "data": iso_date,
                    "descricao": descricao,
                    "valor": valor,
                })

                if saldo is not None:
                    saldo_values.append((iso_date, saldo))

            # Santander lists newest first; reverse to chronological
            result["transacoes"].reverse()
            saldo_values.reverse()

            # Note if no transactions found (legitimate zero-activity period)
            if not result["transacoes"] and result["saldo_inicial"] is not None:
                result["notas"].append(
                    "Conta sem movimentação no período (apenas saldo anterior registrado)"
                )

            # Saldo anterior from previous search
            sa_pattern = re.search(
                r'Saldo anterior.*?Saldo \(R\$\)\s*\n\s*(\d{2}/\d{2}/\d{4})\s+(-?[\d.,]+)',
                all_text, re.DOTALL
            )
            if sa_pattern:
                result["saldo_inicial"] = parse_brl(sa_pattern.group(2))
            elif saldo_values:
                # Earliest saldo minus earliest transaction = initial
                result["saldo_inicial"] = saldo_values[0][1] - (result["transacoes"][0]["valor"] if result["transacoes"] else 0)

            if saldo_values:
                result["saldo_final"] = saldo_values[-1][1]

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: BTG Pactual (extratoconta)
# TEXT_REGEX — clean tabular text
# =============================================================================

def parse_btg(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse BTG Pactual bank statement."""
    log("INFO", f"Parsing BTG Pactual: {filename}")
    result = make_result_template("BTG Pactual", "extratoconta", "BRL")

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"

            result["titular"] = detect_member_from_text(all_text)

            # Account
            m = re.search(r'Conta Corrente[:\s]+([\d]+)', all_text)
            if m:
                result["numero_conta"] = m.group(1)

            # CPF
            m = re.search(r'CPF[:\s]+([\d.\-]+)', all_text)

            # Periodo: "Período de DD/MM/YYYY a DD/MM/YYYY"
            pm = re.search(r'Per[ií]odo\s+de\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', all_text)
            if pm:
                p1 = pm.group(1).split("/")
                p2 = pm.group(2).split("/")
                result["periodo"]["inicio"] = f"{p1[2]}-{p1[1]}-{p1[0]}"
                result["periodo"]["fim"] = f"{p2[2]}-{p2[1]}-{p2[0]}"

            # BTG format: "DD/MM/YYYY DESCRIÇÃO DEBITO CREDITO SALDO"
            # "Saldo Inicial" and "Saldo Final" are special rows
            # Debit column: value without sign (represents money out)
            # Credit column: value without sign (represents money in)
            # One of debit/credit is present per line

            # Parse line by line
            lines = all_text.split("\n")
            in_movimentacao = False

            for line in lines:
                line = line.strip()

                if "Movimentação" in line and "Conta Corrente" in line:
                    in_movimentacao = True
                    continue

                if not in_movimentacao:
                    continue

                # Skip headers
                if line.startswith("Data") and "Descrição" in line:
                    continue

                # Saldo Inicial
                si_match = re.match(r'(\d{2}/\d{2}/\d{4})\s+Saldo Inicial\s+([\d.,]+)', line)
                if si_match:
                    result["saldo_inicial"] = parse_brl(si_match.group(2))
                    continue

                # Saldo Final
                sf_match = re.match(r'(\d{2}/\d{2}/\d{4})\s+Saldo Final\s+([\d.,]+)', line)
                if sf_match:
                    result["saldo_final"] = parse_brl(sf_match.group(2))
                    continue

                # Total lines
                if line.startswith("Total de"):
                    continue

                # Regular transaction: DD/MM/YYYY DESCRIPTION VALUE1 VALUE2
                # Where VALUE1 = debit OR credit, VALUE2 = saldo after
                tx_match = re.match(
                    r'(\d{2}/\d{2}/\d{4})\s+'  # Date
                    r'(.+?)\s+'                  # Description
                    r'([\d.,]+)\s+'              # Value (debit or credit)
                    r'([\d.,]+)\s*$',            # Saldo
                    line
                )
                if tx_match:
                    date_parts = tx_match.group(1).split("/")
                    iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                    descricao = tx_match.group(2).strip()
                    valor_raw = parse_brl(tx_match.group(3))
                    saldo_after = parse_brl(tx_match.group(4))

                    if valor_raw is None:
                        continue

                    # Determine sign: compare saldo progression
                    # If saldo decreased → debit (negative)
                    # If saldo increased → credit (positive)
                    # Use "RESGATE", "REMUNERAÇÃO", "CREDITO", "RECEBIMENTO", "CUPOM",
                    # "DIVIDENDO", "Rendimento" as credit indicators
                    credit_keywords = [
                        "RESGATE", "REMUNERAÇÃO", "CREDITO", "CRÉDITO",
                        "RECEBIMENTO", "CUPOM", "DIVIDENDO", "Rendimento",
                        "RENDIMENT", "FRAÇÕES",
                    ]
                    desc_upper = descricao.upper()
                    is_credit = any(kw.upper() in desc_upper for kw in credit_keywords)

                    # Also check: if there's a previous transaction, compare saldos
                    if is_credit:
                        valor = valor_raw  # positive
                    else:
                        valor = -valor_raw  # debit = negative

                    result["transacoes"].append({
                        "data": iso_date,
                        "descricao": descricao,
                        "valor": valor,
                    })

                # Handle "- VALUE" notation for credit (CONTA REMUNERADA lines)
                tx_match2 = re.match(
                    r'(\d{2}/\d{2}/\d{4})\s+'
                    r'(.+?)\s+-\s+'
                    r'([\d.,]+)\s+'
                    r'([\d.,]+)\s*$',
                    line
                )
                if tx_match2 and not tx_match:
                    date_parts = tx_match2.group(1).split("/")
                    iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                    descricao = tx_match2.group(2).strip()
                    valor_raw = parse_brl(tx_match2.group(3))
                    if valor_raw is not None:
                        result["transacoes"].append({
                            "data": iso_date,
                            "descricao": descricao,
                            "valor": valor_raw,  # "- VALUE" in BTG = credit (REMUNERAÇÃO)
                        })

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: Rico (extratoconta)
# TEXT_REGEX — single page, clean format
# =============================================================================

def parse_rico(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Rico corretora bank statement."""
    log("INFO", f"Parsing Rico: {filename}")
    result = make_result_template("Rico", "extratoconta", "BRL")

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"

            result["titular"] = detect_member_from_text(all_text)

            # Account
            m = re.search(r'Conta[:\s]+(\d+)', all_text)
            if m:
                result["numero_conta"] = m.group(1)

            # Periodo: "De: DD/MM/YYYY Até: DD/MM/YYYY"
            pm = re.search(r'De[:\s]+(\d{2}/\d{2}/\d{4})\s+Até[:\s]+(\d{2}/\d{2}/\d{4})', all_text)
            if pm:
                p1 = pm.group(1).split("/")
                p2 = pm.group(2).split("/")
                result["periodo"]["inicio"] = f"{p1[2]}-{p1[1]}-{p1[0]}"
                result["periodo"]["fim"] = f"{p2[2]}-{p2[1]}-{p2[0]}"

            # Saldo disponível
            m = re.search(r'Saldo dispon[ií]vel[:\s]+R\$\s*([\d.,]+)', all_text)
            if m:
                result["saldo_final"] = parse_brl(m.group(1))

            # Rico format: "DD/MM/YYYY DD/MM/YYYY HISTORICO R$ valor R$ saldo"
            # Liq date, Mov date, then description, then R$ value, then R$ saldo
            tx_pattern = re.compile(
                r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+'  # Liq date, Mov date
                r'(.+?)\s+'                                        # Description
                r'R\$\s*([\d.,]+)\s+'                              # Value
                r'R\$\s*([\d.,]+)',                                 # Saldo
            )

            for m in tx_pattern.finditer(all_text):
                date_parts = m.group(1).split("/")  # Use Liq date
                iso_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                descricao = m.group(3).strip()
                valor = parse_brl(m.group(4))

                if valor is None:
                    continue

                # Rico only shows credits (dividendos, JCP, rendimentos)
                result["transacoes"].append({
                    "data": iso_date,
                    "descricao": descricao,
                    "valor": valor,
                })

            # Derive saldo_inicial from saldo_final minus total credits
            if result["saldo_final"] is not None and result["transacoes"]:
                total = sum(t["valor"] for t in result["transacoes"] if t["valor"])
                result["saldo_inicial"] = round(result["saldo_final"] - total, 2)

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: Wise (extratocontausd, extratocontabrl)
# TEXT_REGEX — description + amount + balance on one line, date on next
# =============================================================================

def parse_wise(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Wise bank statement."""
    is_usd = "usd" in filename.lower()
    moeda = "USD" if is_usd else "BRL"
    tipo = f"extratoconta{moeda.lower()}"

    log("INFO", f"Parsing Wise ({moeda}): {filename}")
    result = make_result_template("Wise", tipo, moeda)

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"

            result["titular"] = detect_member_from_text(all_text)

            # Account
            m = re.search(r'N[úu]mero da conta\s+.*?(\d{10,})', all_text)
            if m:
                result["numero_conta"] = m.group(1)

            # Periodo from header
            # "1 de janeiro de 2025 [GMT-03:00] - 29 de março de 2026 [GMT-03:00]"
            pm = re.search(
                r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+\[.*?\]\s*-\s*'
                r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
                all_text
            )
            if pm:
                d1, m1, y1 = int(pm.group(1)), MESES_BR.get(pm.group(2).lower(), 0), int(pm.group(3))
                d2, m2, y2 = int(pm.group(4)), MESES_BR.get(pm.group(5).lower(), 0), int(pm.group(6))
                if m1 and m2:
                    result["periodo"]["inicio"] = safe_date(y1, m1, d1)
                    result["periodo"]["fim"] = safe_date(y2, m2, d2)

            # Current balance from header: "USD em DD de MÊS de YYYY [TZ] VALUE USD"
            bal_match = re.search(
                r'(?:USD|BRL)\s+em\s+.*?\s+([\d.,]+)\s+(?:USD|BRL)',
                all_text
            )
            if bal_match:
                result["saldo_final"] = parse_brl(bal_match.group(1))

            # Wise format: transactions are blocks of 2 lines:
            # Line 1: "Description [entrada|saída] [-]VALUE BALANCE"
            # Line 2: "DD de MÊS de YYYY Transação: ID [Referência: ref]"
            #
            # Entries/exits marked by column position or sign

            # Parse using combined pattern
            # Transaction pattern: description + optional amount columns + balance
            lines = all_text.split("\n")
            transactions: List[Dict] = []
            i = 0

            while i < len(lines):
                line = lines[i].strip()

                # Look for date line: "DD de MÊS de YYYY Transação: ..."
                date_match = re.match(
                    r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+Transação',
                    line
                )

                if date_match and transactions:
                    # This is the date for the previous transaction
                    d = int(date_match.group(1))
                    m_name = date_match.group(2).lower()
                    y = int(date_match.group(3))
                    mo = MESES_BR.get(m_name, 0)
                    if mo:
                        transactions[-1]["data"] = safe_date(y, mo, d)
                    i += 1
                    continue

                # Transaction line: ends with amount and balance
                # Examples:
                # "Recebeu dinheiro de Douglas... 20,00 4.721,94"
                # "Pago para IU65 Premium & B -16,12 8.854,16"
                # "Dinheiro adicionado à conta 8.400,00 10.836,38"
                tx_match = re.match(
                    r'(.+?)\s+(-?[\d.,]+)\s+([\d.,]+)\s*$',
                    line
                )

                if tx_match:
                    descricao = tx_match.group(1).strip()
                    valor = parse_brl(tx_match.group(2))
                    # Skip header rows
                    if descricao in ("Descrição", "Descrição Entrada Saída Valor"):
                        i += 1
                        continue
                    if "Entrada" in descricao and "Saída" in descricao:
                        i += 1
                        continue

                    if valor is not None:
                        transactions.append({
                            "data": None,  # will be filled by next date line
                            "descricao": descricao,
                            "valor": valor,
                        })

                i += 1

            # Remove transactions without dates
            result["transacoes"] = [t for t in transactions if t.get("data")]

            # Wise lists newest first; reverse
            result["transacoes"].reverse()

            # Note if no transactions (legitimate zero-activity)
            if not result["transacoes"] and result["saldo_final"] is not None:
                result["notas"].append(
                    "Conta sem movimentação no período (saldo estável)"
                )

            # Derive saldo_inicial
            if result["saldo_final"] is not None and result["transacoes"]:
                total = sum(t["valor"] for t in result["transacoes"] if t["valor"])
                result["saldo_inicial"] = round(result["saldo_final"] - total, 2)

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: Bank of America (extratoconta)
# TEXT_REGEX — standard US bank statement
# =============================================================================

def parse_bankofamerica(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Bank of America statement."""
    log("INFO", f"Parsing Bank of America: {filename}")
    result = make_result_template("Bank of America", "extratoconta", "USD")

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"

            result["titular"] = detect_member_from_text(all_text)

            # Account: "Account number: XXXX XXXX XXXX"
            m = re.search(r'Account\s+number[:\s]+([\d\s]+)', all_text)
            if m:
                result["numero_conta"] = m.group(1).strip()

            # Periodo: "for February 25, 2026 to March 26, 2026"
            pm = re.search(
                r'for\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+to\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})',
                all_text
            )
            if pm:
                months_en = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12,
                }
                m1 = months_en.get(pm.group(1).lower(), 0)
                m2 = months_en.get(pm.group(4).lower(), 0)
                if m1 and m2:
                    result["periodo"]["inicio"] = safe_date(int(pm.group(3)), m1, int(pm.group(2)))
                    result["periodo"]["fim"] = safe_date(int(pm.group(6)), m2, int(pm.group(5)))

            # Beginning/Ending balance
            bb = re.search(r'Beginning balance.*?\$([\d.,]+)', all_text)
            eb = re.search(r'Ending balance.*?\$([\d.,]+)', all_text)
            if bb:
                result["saldo_inicial"] = parse_brl(bb.group(1))
            if eb:
                result["saldo_final"] = parse_brl(eb.group(1))

            # Transaction lines: "MM/DD/YY DESCRIPTION AMOUNT"
            # BoA uses US date format
            tx_pattern = re.compile(
                r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(-?[\d.,]+)\s*$',
                re.MULTILINE
            )
            for m in tx_pattern.finditer(all_text):
                mm, dd, yy = m.group(1).split("/")
                yy_full = 2000 + int(yy)
                iso_date = safe_date(yy_full, int(mm), int(dd))
                result["transacoes"].append({
                    "data": iso_date,
                    "descricao": m.group(2).strip(),
                    "valor": parse_brl(m.group(3)),
                })

            # Note: BoA may legitimately have 0 transactions (dormant account)
            if not result["transacoes"] and result["saldo_inicial"] == result["saldo_final"]:
                result["notas"].append("Conta sem movimentação no período (saldo inicial = saldo final)")

    except Exception as e:
        log("ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log("INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Router — maps filename patterns to parser functions
# =============================================================================

# Order matters: more specific patterns first
PARSER_REGISTRY: List[Tuple[re.Pattern, callable]] = [
    # C6 Bank variants
    (re.compile(r'^c6bank_extratocontaglobalusd_'), parse_c6bank),
    (re.compile(r'^c6bank_extratocontaglobaleur_'), parse_c6bank),
    (re.compile(r'^c6bank_extratocontapj_'), parse_c6bank),
    (re.compile(r'^c6bank_extratoconta_'), parse_c6bank),
    # Itaú
    (re.compile(r'^itau_extratocontapersonnalite_'), parse_itau),
    (re.compile(r'^itau_extratoconta_'), parse_itau),
    # PicPay
    (re.compile(r'^picpay_extratoconta_'), parse_picpay),
    # Bradesco
    (re.compile(r'^bradesco_extratopoupanca_'), parse_bradesco),
    (re.compile(r'^bradesco_extratoconta_'), parse_bradesco),
    # Santander
    (re.compile(r'^santander_extratoconta_'), parse_santander_conta),
    # BTG Pactual
    (re.compile(r'^btgpactual_extratoconta_'), parse_btg),
    # Rico
    (re.compile(r'^rico_extratoconta_'), parse_rico),
    # Wise
    (re.compile(r'^wise_extratoconta'), parse_wise),
    # Bank of America
    (re.compile(r'^bankofamerica_extratoconta_'), parse_bankofamerica),
]

# Types that are NOT bank statements (should not be processed by this script)
NON_STATEMENT_TYPES = re.compile(
    r'(fatura|investimentosposicao|carteirarendafixa|cdbdetalhes|cdbresumo|'
    r'informerendimentos|irpf|curriculo|holerite|baseline|dados_)'
)


def route_to_parser(filename: str) -> Optional[callable]:
    """Find the appropriate parser for a given filename."""
    # Skip non-statement types
    if NON_STATEMENT_TYPES.search(filename):
        return None

    for pattern, parser_fn in PARSER_REGISTRY:
        if pattern.search(filename):
            return parser_fn

    return None


# =============================================================================
# Validation gate
# =============================================================================

def validate_result(result: Dict[str, Any], pdf_path: Path) -> List[str]:
    """Validate extraction result. Returns list of warnings/errors."""
    issues = []

    n_tx = len(result.get("transacoes", []))
    periodo = result.get("periodo", {})

    # Check periodo
    if not periodo.get("inicio"):
        issues.append("WARN: periodo.inicio ausente")
    if not periodo.get("fim"):
        issues.append("WARN: periodo.fim ausente")

    # Check transactions vs PDF size
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)
            n_pages = len(pdf.pages)
    except Exception:
        total_chars = 0
        n_pages = 0

    # Heuristic: if PDF has significant text content but 0 transactions,
    # it's likely a parsing failure unless explicitly noted
    if n_tx == 0 and total_chars > 500 and n_pages > 0:
        is_dormant = any("sem movimentação" in n.lower() for n in result.get("notas", []))
        is_empty_period = any("sem lançamentos" in n.lower() for n in result.get("notas", []))
        if not is_dormant and not is_empty_period:
            issues.append(
                f"ERROR: 0 transações extraídas de PDF com {total_chars} chars / "
                f"{n_pages} páginas — provável falha de parsing"
            )

    # Check for transactions with None values
    none_vals = sum(1 for t in result.get("transacoes", []) if t.get("valor") is None)
    if none_vals > 0:
        issues.append(f"WARN: {none_vals} transações com valor None")

    # Check for duplicate transactions (same date+valor+descricao)
    seen = set()
    dupes = 0
    for t in result.get("transacoes", []):
        key = (t.get("data"), t.get("valor"), t.get("descricao", "")[:30])
        if key in seen:
            dupes += 1
        seen.add(key)
    if dupes > 0:
        issues.append(f"INFO: {dupes} possíveis duplicatas intra-arquivo")

    return issues


# =============================================================================
# Main — CLI interface
# =============================================================================

def find_extrato_files() -> List[Path]:
    """Find all bank statement PDFs in data/financial_statements/."""
    if not DATA_DIR.is_dir():
        log("WARN", f"Diretório não encontrado: {DATA_DIR}")
        return []

    files = []
    for f in sorted(DATA_DIR.iterdir()):
        if not f.is_file():
            continue
        if not f.name.endswith("-0_original.pdf"):
            continue
        # Check if this is a statement type (not fatura, investment, etc.)
        if NON_STATEMENT_TYPES.search(f.name):
            continue
        # Must contain "extrato" in filename
        if "extrato" not in f.name.lower():
            continue
        files.append(f)

    return files


def process_file(pdf_path: Path, dry_run: bool = False) -> Optional[Dict[str, Any]]:
    """Process a single PDF file through the appropriate parser."""
    filename = pdf_path.name

    parser_fn = route_to_parser(filename)
    if parser_fn is None:
        log("WARN", f"Sem parser determinístico para: {filename}")
        return {
            "requires_llm_fallback": True,
            "arquivo": filename,
            "motivo": "Banco/tipo não reconhecido pelo parser determinístico",
        }

    if dry_run:
        log("INFO", f"[DRY-RUN] Processaria: {filename} → {parser_fn.__name__}")
        return None

    result = parser_fn(pdf_path, filename)

    # Run validation
    issues = validate_result(result, pdf_path)
    for issue in issues:
        level = issue.split(":")[0]
        log(level, f"  {filename}: {issue}")
        result.setdefault("notas", []).append(issue)

    return result


def save_result(result: Dict[str, Any], filename: str) -> Path:
    """Save extraction result to E2_extracts directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Output filename: replace -0_original.pdf with -2_extract.json
    out_name = filename.replace("-0_original.pdf", "-2_extract.json")
    out_path = OUTPUT_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return out_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="E2 Extrato Extraction — Deterministic parsers for bank statements"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without writing files")
    parser.add_argument("--file", type=str, default=None,
                        help="Process a specific PDF file")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: processed/E2_extracts/)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress debug output")

    args = parser.parse_args()

    global _VERBOSE, OUTPUT_DIR
    if args.quiet:
        _VERBOSE = False
    if args.output_dir:
        OUTPUT_DIR = Path(args.output_dir)

    log("INFO", "=" * 60)
    log("INFO", "E2 EXTRATO EXTRACTION — Deterministic Parsers")
    log("INFO", "=" * 60)

    if args.file:
        pdf_path = Path(args.file)
        if not pdf_path.exists():
            # Try relative to DATA_DIR
            pdf_path = DATA_DIR / args.file
        if not pdf_path.exists():
            log("ERROR", f"Arquivo não encontrado: {args.file}")
            sys.exit(1)
        files = [pdf_path]
    else:
        files = find_extrato_files()

    if not files:
        log("INFO", "Nenhum extrato encontrado para processar.")
        return

    log("INFO", f"Encontrados {len(files)} extratos para processar")

    # Statistics
    stats = {
        "processados": 0,
        "transacoes_total": 0,
        "llm_fallback": 0,
        "erros_validacao": 0,
        "warnings": 0,
    }

    for pdf_path in files:
        result = process_file(pdf_path, dry_run=args.dry_run)
        if result is None:
            continue

        if result.get("requires_llm_fallback"):
            stats["llm_fallback"] += 1
            log("WARN", f"  → Requer LLM fallback: {pdf_path.name}")
            continue

        n_tx = len(result.get("transacoes", []))
        stats["processados"] += 1
        stats["transacoes_total"] += n_tx

        # Count issues
        for note in result.get("notas", []):
            if note.startswith("ERROR"):
                stats["erros_validacao"] += 1
            elif note.startswith("WARN"):
                stats["warnings"] += 1

        if not args.dry_run:
            out_path = save_result(result, pdf_path.name)
            log("INFO", f"  → Salvo: {out_path.name} ({n_tx} transações)")

    # Summary
    log("INFO", "=" * 60)
    log("INFO", "RESUMO:")
    log("INFO", f"  Processados: {stats['processados']}")
    log("INFO", f"  Total transações: {stats['transacoes_total']}")
    log("INFO", f"  LLM fallback: {stats['llm_fallback']}")
    log("INFO", f"  Erros de validação: {stats['erros_validacao']}")
    log("INFO", f"  Warnings: {stats['warnings']}")
    log("INFO", "=" * 60)

    if stats["erros_validacao"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
