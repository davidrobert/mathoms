#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C6 Bank — extratos (conta, contapj, global USD/EUR) e faturas (Carbon)."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_C6,
    C6_CSV_LAYOUT,
    CARTAO_CARBON,
    FAMILY,
    MESES_BR_INT,
    MESES_BR_STR,
    TITULAR,
    VENC_CARBON,
    detect_member_from_card_name,
    detect_member_from_text,
    extract_account_number,
    infer_periodo_from_filename,
    infer_year_from_filename,
    log,
    make_result_template,
    parse_brl,
    resolve_date,
    resolve_year_from_period,
    safe_date,
)

LOG_PREFIX_EXTRATO = "E2-EXTRATO"
LOG_PREFIX_FATURA = "E2-FATURA"

PARSERS = [
    (r'^c6bank_extratocontapj_.*\.csv$', "parse_c6bank_csv"),
    (r'^c6bank_extratoconta_.*\.csv$', "parse_c6bank_csv"),
    (r'^c6bank_extratocontaglobalusd_', "parse_c6bank"),
    (r'^c6bank_extratocontaglobaleur_', "parse_c6bank"),
    (r'^c6bank_extratocontapj_', "parse_c6bank"),
    (r'^c6bank_extratoconta_', "parse_c6bank"),
    (r'c6bank_faturacarbon.*\.csv$', "parse_c6_carbon_csv"),
    (r'c6bank_faturacarbon', "parse_c6_carbon"),
]


# =============================================================================
# Helpers — extrato CSV
# =============================================================================

def _parse_csv_number(text: str) -> Optional[float]:
    """Parse a number from C6 CSV format. Handles '1234.56', '-1234.56', empty strings."""
    if not text or not text.strip():
        return None
    text = text.strip().replace(",", "")  # in case of thousands separators
    try:
        return float(text)
    except ValueError:
        return parse_brl(text)


def _classify_c6_csv_lancamento(titulo: str, descricao: str) -> str:
    """Classify a C6 CSV transaction into tipo_lancamento based on titulo/descricao."""
    combined = f"{titulo} {descricao}".lower()

    if "pix enviado" in combined:
        return "Saída PIX"
    elif "pix recebido" in combined:
        return "Entrada PIX"
    elif "devol recebida pix" in combined or "devol enviada pix" in combined:
        return "Devolução PIX"
    elif "ted enviada" in combined or "transf enviada" in combined:
        return "Saída TED/Transferência"
    elif "ted recebida" in combined or "transf recebida" in combined:
        return "Entrada TED/Transferência"
    elif "c6tag" in combined:
        return "C6 Tag (Pedágio/Estacionamento)"
    elif "boleto" in combined or "guia" in combined:
        return "Pagamento Boleto"
    elif "juros" in combined or "iof" in combined:
        return "Encargos Bancários"
    elif "rendimento" in combined or "aplicação" in combined or "aplicacao" in combined:
        return "Investimento/Rendimento"
    elif "resgate" in combined:
        return "Resgate Investimento"
    elif "salário" in combined or "salario" in combined:
        return "Salário"
    elif "13" in titulo and "salário" in combined.replace("á", "a"):
        return "13º Salário"
    elif "compra" in combined or "débito" in combined or "debito" in combined:
        return "Compra/Débito"
    else:
        return "Outros"


# =============================================================================
# Helpers — fatura CSV
# =============================================================================

def _parse_fatura_csv_number(text: str) -> Optional[float]:
    """Parse number from C6 fatura CSV. Handles '1234.56', '-1234.56', '0'."""
    if not text or not text.strip():
        return None
    text = text.strip()
    try:
        val = float(text)
        return val
    except ValueError:
        return parse_brl(text)


# =============================================================================
# Parser: C6 Bank extrato conta CSV
# =============================================================================

def parse_c6bank_csv(csv_path: Path, filename: str) -> Dict[str, Any]:
    """Parse C6 Bank CSV statement (conta or contapj).

    CSV structure:
      - BOM (UTF-8) header
      - Lines 1-2: "EXTRATO DE CONTA CORRENTE C6 BANK" + blank
      - Line 3: "Agência: X / Conta: NNNNNNNNN"
      - Line 4: "Extrato gerado em DD/MM/YYYY - as HH:MM:SS"
      - Line 5: blank
      - Line 6: "Extrato de DD/MM/YYYY a DD/MM/YYYY"
      - Line 7: blank
      - Line 8: header row (comma-separated)
      - Lines 9+: transaction data
    """
    import csv as csv_mod

    is_pj = "extratocontapj" in filename
    tipo = "extratocontapj" if is_pj else "extratoconta"
    moeda = "BRL"

    log(LOG_PREFIX_EXTRATO, "INFO", f"Parsing C6 Bank CSV ({tipo}): {filename}")
    result = make_result_template(BANCO_C6, tipo, moeda)

    raw_text = csv_path.read_text(encoding="utf-8-sig")
    lines = raw_text.splitlines()

    # --- Parse header metadata ---
    for line in lines[:6]:
        conta_m = re.search(r'Conta:\s*(\d+)', line)
        if conta_m:
            result["numero_conta"] = conta_m.group(1)
            break

    for line in lines[:10]:
        periodo_m = re.search(
            r'Extrato de\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', line
        )
        if periodo_m:
            d1 = datetime.strptime(periodo_m.group(1), "%d/%m/%Y")
            d2 = datetime.strptime(periodo_m.group(2), "%d/%m/%Y")
            result["periodo"]["inicio"] = d1.strftime("%Y-%m-%d")
            result["periodo"]["fim"] = d2.strftime("%Y-%m-%d")
            break

    if not result["periodo"]["inicio"]:
        p_ini, p_fim = infer_periodo_from_filename(filename)
        result["periodo"]["inicio"] = p_ini
        result["periodo"]["fim"] = p_fim

    header_text = "\n".join(lines[:6])
    result["titular"] = detect_member_from_text(header_text)

    # --- Find the CSV header row and parse transactions ---
    csv_header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Data Lançamento,") or line.strip().startswith("Data Lancamento,"):
            csv_header_idx = i
            break

    if csv_header_idx is None:
        result["notas"].append("WARN: Header CSV 'Data Lançamento,...' não encontrado")
        return result

    csv_text = "\n".join(lines[csv_header_idx:])
    reader = csv_mod.reader(csv_text.splitlines())
    header = next(reader, None)

    if not header:
        result["notas"].append("WARN: Header CSV vazio")
        return result

    header_clean = [h.strip().lower() for h in header]

    saldo_first = None
    saldo_last = None

    for row in reader:
        if len(row) < 6:
            continue

        while len(row) < 7:
            row.append("")

        data_lanc_str = row[0].strip()
        data_contabil_str = row[1].strip()
        titulo = row[2].strip()
        descricao = row[3].strip()
        entrada_str = row[4].strip()
        saida_str = row[5].strip()
        saldo_str = row[6].strip()

        if not re.match(r'\d{2}/\d{2}/\d{4}$', data_lanc_str):
            continue

        try:
            dt = datetime.strptime(data_lanc_str, "%d/%m/%Y")
            data_iso = dt.strftime("%Y-%m-%d")
        except ValueError:
            log(LOG_PREFIX_EXTRATO, "WARN", f"  Data inválida: {data_lanc_str}")
            continue

        entrada = _parse_csv_number(entrada_str)
        saida = _parse_csv_number(saida_str)

        if entrada and entrada > 0:
            valor = entrada
        elif saida and saida > 0:
            valor = -saida
        else:
            valor = 0.0

        if descricao and descricao != titulo:
            desc_full = f"{titulo} — {descricao}" if titulo else descricao
        else:
            desc_full = titulo or descricao or ""

        tipo_lanc = _classify_c6_csv_lancamento(titulo, descricao)

        tx = {
            "data": data_iso,
            "descricao": desc_full,
            "valor": valor,
            "tipo_lancamento": tipo_lanc,
        }

        result["transacoes"].append(tx)

        saldo_val = _parse_csv_number(saldo_str)
        if saldo_val is not None:
            if saldo_first is None:
                saldo_first = saldo_val
            saldo_last = saldo_val

    result["saldo_final"] = saldo_last

    if saldo_first is not None and result["transacoes"]:
        first_valor = result["transacoes"][0].get("valor", 0) or 0
        result["saldo_inicial"] = round(saldo_first - first_valor, 2)
    else:
        result["saldo_inicial"] = saldo_first

    n_tx = len(result["transacoes"])
    log(LOG_PREFIX_EXTRATO, "INFO", f"  Extraídas {n_tx} transações do CSV")
    if result["saldo_inicial"] is not None:
        log(LOG_PREFIX_EXTRATO, "INFO", f"  Saldo inicial: {result['saldo_inicial']:.2f}")
    if result["saldo_final"] is not None:
        log(LOG_PREFIX_EXTRATO, "INFO", f"  Saldo final: {result['saldo_final']:.2f}")

    return result


# =============================================================================
# Parser: C6 Bank extrato conta/PJ/global PDF
# =============================================================================

def parse_c6bank(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse C6 Bank statement (conta, contapj, contaglobal)."""
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

    log(LOG_PREFIX_EXTRATO, "INFO", f"Parsing C6 Bank ({tipo}): {filename}")
    result = make_result_template(BANCO_C6, tipo, moeda)

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_text = pdf.pages[0].extract_text() or ""
            result["titular"] = detect_member_from_text(first_text)
            result["numero_conta"] = extract_account_number(first_text, "c6bank")

            periodo_pat = re.compile(
                r'Período\s*•?\s*(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+'
                r'até\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
                re.IGNORECASE
            )
            pm = periodo_pat.search(first_text)
            if pm:
                d1 = int(pm.group(1))
                m1 = MESES_BR_INT.get(pm.group(2).lower(), 0)
                y1 = int(pm.group(3))
                d2 = int(pm.group(4))
                m2 = MESES_BR_INT.get(pm.group(5).lower(), 0)
                y2 = int(pm.group(6))
                if m1 and m2:
                    result["periodo"]["inicio"] = safe_date(y1, m1, d1)
                    result["periodo"]["fim"] = safe_date(y2, m2, d2)

            saldo_header = re.search(
                r'Saldo do dia.*?[•\s]+(R\$|US\$|EUR)\s*([\d.,]+)',
                first_text
            )

            full_text = "\n".join(
                (p.extract_text() or "") for p in pdf.pages
            )
            if "Sem lançamentos no mês" in full_text or "sem lançamentos" in full_text.lower():
                empty_months = full_text.lower().count("sem lançamentos")
                result["notas"].append(
                    f"Sem lançamentos no período ({empty_months} mês(es) sem movimentação)"
                )

            if is_global_usd or is_global_eur:
                saldo_text_match = re.search(
                    r'Saldo do dia.*?(?:US\$|€|EUR\s*)\s*([\d.,]+)',
                    full_text,
                )
                if saldo_text_match:
                    raw = saldo_text_match.group(1).replace(".", "").replace(",", ".")
                    try:
                        result["saldo_final"] = float(raw)
                    except ValueError:
                        pass

            all_rows: List[Tuple[str, str, str, str, str]] = []
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and len(row) >= 4:
                            all_rows.append(tuple(str(c) if c else "" for c in row))

            is_global = is_global_usd or is_global_eur

            pending_tx: Optional[Dict] = None
            saldo_values: List[Tuple[str, float]] = []

            _c6g = C6_CSV_LAYOUT.get("global_format", {})
            _c6cp = C6_CSV_LAYOUT.get("conta_pj_format", {})
            _c6_min_cols = C6_CSV_LAYOUT.get("min_columns", 5)
            _c6_saldo_re = C6_CSV_LAYOUT.get("saldo_regex", r'Saldo do dia\s+(\d{2}/\d{2}/\d{2,4})')

            for row in all_rows:
                cols = list(row) + [""] * (_c6_min_cols - len(row))
                col0, col1, col2, col3, col4 = cols[:5]

                if is_global:
                    valor_col = cols[_c6g.get("valor", 3)]
                    desc_col = cols[_c6g.get("descricao", 2)]
                    tipo_col = cols[_c6g.get("tipo", 1)]
                else:
                    valor_col = cols[_c6cp.get("valor", 4)]
                    desc_col = cols[_c6cp.get("descricao", 3)]
                    tipo_col = cols[_c6cp.get("tipo", 2)]

                if not any(c.strip() for c in cols):
                    continue

                saldo_match = re.match(_c6_saldo_re, col0)
                if saldo_match:
                    saldo_val = parse_brl(col4) or parse_brl(col3)
                    if saldo_val is not None:
                        date_str = saldo_match.group(1)
                        saldo_values.append((date_str, saldo_val))
                    if pending_tx:
                        result["transacoes"].append(pending_tx)
                        pending_tx = None
                    continue

                date_match = re.match(r'(\d{2}/\d{2})', col0.strip())
                has_value = valor_col.strip() and parse_brl(valor_col) is not None

                if date_match and has_value:
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

                if not date_match and (tipo_col.strip() or desc_col.strip()):
                    val = parse_brl(valor_col)
                    if pending_tx and pending_tx["valor"] is None and val is not None:
                        pending_tx["valor"] = val
                        if desc_col.strip() and not pending_tx["descricao"]:
                            pending_tx["descricao"] = desc_col.strip()
                        result["transacoes"].append(pending_tx)
                        pending_tx = None
                    elif val is not None:
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
                        pending_tx["descricao"] += " " + desc_col.strip()

            if pending_tx:
                result["transacoes"].append(pending_tx)

            result["transacoes"] = [t for t in result["transacoes"] if t.get("valor") is not None]

            if saldo_values:
                result["saldo_inicial"] = saldo_values[0][1]
                result["saldo_final"] = saldo_values[-1][1]

    except Exception as e:
        log(LOG_PREFIX_EXTRATO, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX_EXTRATO, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# =============================================================================
# Parser: C6 Carbon fatura CSV
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

    log(LOG_PREFIX_FATURA, "INFO", f"Parsing C6 Carbon CSV: {filename}")

    result = {
        "banco": BANCO_C6,
        "tipo": "faturacarbon",
        "cartao": CARTAO_CARBON,
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
        "cartoes": [],
    }

    ref_year = infer_year_from_filename(filename)
    ref_month = None
    m = re.search(r'(\d{4})(\d{2})', filename)
    if m:
        ref_year = int(m.group(1))
        ref_month = int(m.group(2))
        result["data_vencimento"] = safe_date(ref_year, ref_month, VENC_CARBON)

    raw_text = csv_path.read_text(encoding="utf-8-sig")
    reader = csv_mod.reader(raw_text.splitlines(), delimiter=";")

    header = next(reader, None)
    if not header or "Data de Compra" not in header[0]:
        log(LOG_PREFIX_FATURA, "WARN", f"  Header CSV inesperado: {header}")
        return result

    total_nacionais = 0.0
    total_internacionais = 0.0
    total_pagamentos = 0.0
    cards_seen = {}

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

        if not re.match(r'\d{2}/\d{2}/\d{4}$', data_str):
            continue

        try:
            dt = datetime.strptime(data_str, "%d/%m/%Y")
            data_iso = dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

        valor_brl = _parse_fatura_csv_number(valor_brl_str)
        if valor_brl is None:
            continue

        card_key = f"C6 Carbon Final {final_cartao} - {nome_cartao}"

        if card_key not in cards_seen:
            cards_seen[card_key] = 0.0
        cards_seen[card_key] += valor_brl

        if result["titular"] is None and nome_cartao:
            detected = detect_member_from_card_name(nome_cartao)
            if detected:
                result["titular"] = detected

        tx = {
            "data": data_iso,
            "descricao": descricao_raw,
            "valor": valor_brl,
            "cartao": card_key,
        }

        if parcela_str and parcela_str != "Única":
            tx["parcela"] = parcela_str

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
            total_pagamentos += valor_brl
        else:
            total_nacionais += valor_brl

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

    result["total_compras_nacionais"] = round(total_nacionais, 2) if total_nacionais else None
    result["total_compras_internacionais"] = round(total_internacionais, 2) if total_internacionais else None
    result["pagamentos"] = round(total_pagamentos, 2) if total_pagamentos else None

    if result["transacoes"]:
        result["saldo_atual"] = round(sum(t["valor"] for t in result["transacoes"]), 2)

    for card_name, subtotal in cards_seen.items():
        result["cartoes"].append({
            "cartao": card_name,
            "subtotal": round(subtotal, 2),
        })

    log(LOG_PREFIX_FATURA, "INFO", f"  → {len(result['transacoes'])} transações extraídas do CSV")
    if result["saldo_atual"] is not None:
        log(LOG_PREFIX_FATURA, "INFO", f"  → Saldo atual: R$ {result['saldo_atual']:.2f}")
    log(LOG_PREFIX_FATURA, "INFO", f"  → Cartões: {len(cards_seen)}")

    return result


# =============================================================================
# Parser: C6 Carbon fatura PDF
# =============================================================================

def parse_c6_carbon(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse C6 Bank Carbon credit card invoice."""
    log(LOG_PREFIX_FATURA, "INFO", f"Parsing C6 Carbon: {filename}")

    result = {
        "banco": BANCO_C6,
        "tipo": "faturacarbon",
        "cartao": CARTAO_CARBON,
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
        "cartoes": [],
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
            _c6_regex = TITULAR.get("regex_nome_fatura", {}).get("c6_carbon", "")
            m = re.search(_c6_regex, full_text) if _c6_regex else None
            if m:
                result["titular"] = TITULAR.get("variantes_nome", [TITULAR.get("nome_completo", "")])[0]

            m = re.search(r'[Vv]encimento[:\s]+(\d{1,2})\s+de\s+(\w+)', full_text)
            if m and ref_year:
                day = int(m.group(1))
                month_name = m.group(2).lower()
                month_num = MESES_BR_STR.get(month_name)
                if month_num:
                    result["data_vencimento"] = f"{ref_year}-{month_num}-{day:02d}"

            m = re.search(r'Valor da fatura:\s*R\$\s*([\d.,]+)', full_text)
            if m:
                result["saldo_atual"] = parse_brl(m.group(1))

            m = re.search(r'Limite total:\s*R\$\s*([\d.,]+)', full_text)
            if m:
                result["limite_total"] = parse_brl(m.group(1))

            m = re.search(r'Compras nacionais\s+([\d.,]+)', full_text)
            if m:
                result["total_compras_nacionais"] = parse_brl(m.group(1))
            m = re.search(r'Compras internacionais\s+([\d.,]+)', full_text)
            if m:
                result["total_compras_internacionais"] = parse_brl(m.group(1))

            m = re.search(r'Estornos\s*/\s*Crédito na Fatura\s+\(?\-?\)?\s*([\d.,]+)', full_text)
            if m:
                result["pagamentos"] = -parse_brl(m.group(1))

            # --- Extract transactions ---
            current_card_name = None
            current_card_subtotal = None

            tx_pattern = re.compile(
                r'^(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s+'
                r'(.+?)\s+'
                r'([\d.,]+)\s*$',
                re.MULTILINE
            )

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
                    card_m = card_pattern.search(line)
                    if card_m:
                        current_card_name = f"C6 Carbon Final {card_m.group(1)} - {card_m.group(2).strip()}"

                    sub_m = subtotal_pattern.search(line)
                    if sub_m and current_card_name:
                        current_card_subtotal = parse_brl(sub_m.group(1))
                        if current_card_name not in cards_seen:
                            cards_seen[current_card_name] = current_card_subtotal

                    tx_m = tx_pattern.match(line.strip())
                    if tx_m:
                        day = int(tx_m.group(1))
                        month_str = tx_m.group(2)
                        raw_desc = tx_m.group(3).strip()
                        valor = parse_brl(tx_m.group(4))

                        if valor is None:
                            continue

                        date_str = resolve_date(day, month_str, ref_year, ref_month)

                        forex_info = None
                        parcela = None
                        descricao = raw_desc

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

                        iof_m = re.search(r'IOF Transações Exterior', raw_desc)
                        if iof_m:
                            descricao = raw_desc[:iof_m.start()].strip()
                            if not descricao:
                                descricao = "IOF Transações Exterior"

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

            for card_name, subtotal in cards_seen.items():
                result["cartoes"].append({
                    "cartao": card_name,
                    "subtotal": subtotal,
                })

        log(LOG_PREFIX_FATURA, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    except Exception as e:
        log(LOG_PREFIX_FATURA, "ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    return result
