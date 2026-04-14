#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2 Common Utilities — shared by all bank parser modules.

Consolidates config loading, value parsing, date handling, and logging
that was previously duplicated across e2_extract_extratos.py and e2_extract_faturas.py.
"""

import calendar
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Paths
# =============================================================================

_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent.parent

BASE_DIR = _DEFAULT_BASE_DIR
DATA_DIR = BASE_DIR / "data" / "financial_statements"
OUTPUT_DIR = BASE_DIR / "processed" / "E2_extracts"
CONFIG_DIR = BASE_DIR / "config"


# =============================================================================
# Config loading
# =============================================================================

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


def _init_config(base_dir: Path) -> None:
    """(Re)carrega paths e configs a partir de um root_dir."""
    global BASE_DIR, DATA_DIR, OUTPUT_DIR, CONFIG_DIR
    global FAMILY, MEMBROS, TITULAR_KEY, TITULAR, MEMBER_NAMES, MEMBER_CPFS
    global LOCALE_CONFIG, INST_CONFIG, PIPE_CONFIG
    global MESES_BR_INT, MESES_BR_STR, BANCO_CANONICAL
    global KNOWN_FATURA_PATTERNS, CARTOES
    global VENC_CARBON, VENC_UNIQUE, VENC_PDA
    global CARTAO_CARBON, CARTAO_UNIQUE, CARTAO_PDA
    global LAYOUTS, ITAU_XLS_LAYOUT, SANTANDER_XLS_LAYOUT, C6_CSV_LAYOUT
    global MIN_XLS_BYTES, MIN_CSV_BYTES

    BASE_DIR = base_dir
    DATA_DIR = base_dir / "data" / "financial_statements"
    OUTPUT_DIR = base_dir / "processed" / "E2_extracts"
    CONFIG_DIR = base_dir / "config"

    fm_path = CONFIG_DIR / "family_members.json"
    FAMILY = _load_json_config(fm_path, "family_members.json") if fm_path.exists() else {}
    MEMBROS = FAMILY.get("membros", {})
    TITULAR_KEY = FAMILY.get("titular", "")
    TITULAR = MEMBROS.get(TITULAR_KEY, {})

    MEMBER_NAMES = []
    MEMBER_CPFS = {}
    for _mid, _mdata in MEMBROS.items():
        for variant in _mdata.get("variantes_nome", []):
            MEMBER_NAMES.append(variant)
        cpf = _mdata.get("cpf", "")
        if cpf:
            MEMBER_CPFS[cpf] = _mid

    LOCALE_CONFIG = _load_json_config(CONFIG_DIR / "localization.json", "localization.json")
    INST_CONFIG = _load_json_config(CONFIG_DIR / "institutions.json", "institutions.json")
    PIPE_CONFIG = _load_json_config(CONFIG_DIR / "pipeline.json", "pipeline.json")

    MESES_BR_INT = LOCALE_CONFIG.get("meses_br_int", {})
    MESES_BR_STR = LOCALE_CONFIG.get("meses_br_str", {})

    BANCO_CANONICAL = INST_CONFIG.get("banco_canonical", {})
    KNOWN_FATURA_PATTERNS = INST_CONFIG.get("fatura_patterns", {})
    CARTOES = INST_CONFIG.get("cartoes", {})
    VENC_CARBON = CARTOES.get("faturacarbon", {}).get("dia_vencimento", 5)
    VENC_UNIQUE = CARTOES.get("faturaunique", {}).get("dia_vencimento", 6)
    VENC_PDA = CARTOES.get("faturapaoacucar", {}).get("dia_vencimento", 6)
    CARTAO_CARBON = CARTOES.get("faturacarbon", {}).get("nome_cartao", "Carbon")
    CARTAO_UNIQUE = CARTOES.get("faturaunique", {}).get("nome_cartao", "Unique")
    CARTAO_PDA = CARTOES.get("faturapaoacucar", {}).get("nome_cartao", "Pão de Açúcar")

    LAYOUTS = INST_CONFIG.get("layouts", {})
    ITAU_XLS_LAYOUT = LAYOUTS.get("itau_xls", {})
    SANTANDER_XLS_LAYOUT = LAYOUTS.get("santander_xls", {})
    C6_CSV_LAYOUT = LAYOUTS.get("c6_csv", {})

    _file_limits = PIPE_CONFIG.get("file_limits", {})
    MIN_XLS_BYTES = _file_limits.get("min_xls_bytes", 40000)
    MIN_CSV_BYTES = _file_limits.get("min_csv_bytes", 500)


# Module level: carrega defaults (retrocompat)
_init_config(_DEFAULT_BASE_DIR)


# =============================================================================
# Display name helper
# =============================================================================

def banco_display(key: str) -> str:
    """Get display name for a bank from config, with title-case fallback."""
    name = BANCO_CANONICAL.get(key, key)
    return name.title() if name == name.lower() else name


# Pre-computed display names used by parsers
BANCO_C6 = banco_display("c6bank")
BANCO_ITAU = banco_display("itau")
BANCO_PICPAY = banco_display("picpay")
BANCO_BRADESCO = banco_display("bradesco")
BANCO_SANTANDER = banco_display("santander")
BANCO_RICO = banco_display("rico")
BANCO_WISE = banco_display("wise")
BANCO_QUINTOANDAR = banco_display("quintoandar")
BANCO_BTG = banco_display("btgpactual")
BANCO_BOA = banco_display("bankofamerica")


# =============================================================================
# Logging
# =============================================================================

_VERBOSE = True


def set_verbose(v: bool) -> None:
    global _VERBOSE
    _VERBOSE = v


def log(prefix: str, level: str, msg: str) -> None:
    if not _VERBOSE and level == "DEBUG":
        return
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {prefix} {level}: {msg}", file=sys.stderr)


# =============================================================================
# Value parsing
# =============================================================================

def parse_brl(text: str) -> Optional[float]:
    """Parse Brazilian currency string to float.
    Superset merge of both original implementations.
    '1.234,56' → 1234.56, '-R$ 98,00' → -98.0, '(1.234,56)' → -1234.56
    """
    if not text:
        return None
    text = str(text).strip()
    for sym in ("R$", "US$", "EUR", "USD", "BRL", "$"):
        text = text.replace(sym, "")
    text = text.replace(" ", "").strip()
    if not text or text == "-":
        return None

    negative = False
    if text.startswith("(-)"):
        negative = True
        text = text[3:].strip()
    elif text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    elif text.startswith("-") or text.startswith("(-"):
        negative = True
        text = text.lstrip("(-").rstrip(")").strip()

    text = text.replace(".", "").replace(",", ".")
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return None


def parse_usd(text: str) -> Optional[float]:
    """Parse US currency string to float. '2,605.00' → 2605.0"""
    if not text:
        return None
    text = str(text).strip()
    for sym in ("US$", "USD", "$"):
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

    text = text.replace(",", "")
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return None


# =============================================================================
# Date helpers
# =============================================================================

def safe_date(year: int, month: int, day: int) -> str:
    """Return valid ISO date string, adjusting day if necessary."""
    year = max(1900, min(2100, year))
    if month < 1 or month > 12:
        month = 1
    max_day = calendar.monthrange(year, month)[1]
    if day > max_day:
        day = max_day
    if day < 1:
        day = 1
    return f"{year}-{month:02d}-{day:02d}"


def infer_periodo_from_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract periodo start/end from filename patterns like _202501_202512 or _202603."""
    m = re.search(r'_(\d{4})(\d{2})_(\d{4})(\d{2})', filename)
    if m:
        y1, m1, y2, m2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        inicio = safe_date(y1, m1, 1)
        fim_day = calendar.monthrange(y2, m2)[1]
        fim = safe_date(y2, m2, fim_day)
        return inicio, fim

    m = re.search(r'_(\d{4})(\d{2})(?:[a-z])?-', filename)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        inicio = safe_date(y, mo, 1)
        fim_day = calendar.monthrange(y, mo)[1]
        fim = safe_date(y, mo, fim_day)
        return inicio, fim

    return None, None


def infer_year_from_filename(filename: str) -> Optional[int]:
    """Extract year from filename like faturacarbon_202603."""
    m = re.search(r'(\d{4})\d{2}', filename)
    if m:
        return int(m.group(1))
    return None


def resolve_year_from_period(dd: int, mm: int, periodo_inicio: str, periodo_fim: str) -> int:
    """Given a transaction DD/MM, resolve which year it belongs to based on periodo."""
    if not periodo_inicio:
        return datetime.now().year
    start_year = int(periodo_inicio[:4])
    end_year = int(periodo_fim[:4]) if periodo_fim else start_year
    if start_year == end_year:
        return start_year
    start_month = int(periodo_inicio[5:7])
    if mm >= start_month:
        return start_year
    return end_year


def resolve_date(day: int, month_str: str, ref_year: int, ref_month: int) -> str:
    """Resolve a date like '28 nov' given reference year/month of the fatura."""
    if ref_year is None or ref_month is None:
        month_num = int(MESES_BR_STR.get(month_str.lower().strip(), '0'))
        if month_num == 0:
            return f"{ref_year or datetime.now().year}-01-{day:02d}"
        return safe_date(ref_year or datetime.now().year, month_num, day)

    month_str_lower = month_str.lower().strip()
    month_num = int(MESES_BR_STR.get(month_str_lower, '0'))
    if month_num == 0:
        return safe_date(ref_year, ref_month, day)

    year = ref_year
    forward_distance = (month_num - ref_month) % 12
    if forward_distance > 6:
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
# Member / account detection
# =============================================================================

def detect_member_from_text(text: str) -> Optional[str]:
    """Try to identify which family member owns this statement."""
    text_upper = text.upper()
    for cpf, mid in MEMBER_CPFS.items():
        if cpf in text:
            return mid
    for mid, mdata in MEMBROS.items():
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


def detect_member_from_card_name(nome_cartao: str) -> Optional[str]:
    """Match card holder name to family member using config data."""
    nome_upper = nome_cartao.upper()
    for mid, mdata in FAMILY.get("membros", {}).items():
        for variant in mdata.get("variantes_nome", []):
            if nome_upper in variant.upper() or variant.upper().startswith(nome_upper):
                return mdata.get("variantes_nome", [variant])[0]
    return None


# =============================================================================
# Result templates
# =============================================================================

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
