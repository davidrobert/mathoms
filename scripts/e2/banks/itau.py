#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Itaú — parsers de extratos (conta, CDB) e faturas (Pão de Açúcar PDF/CSV)."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.banks.itau_extrato_2026 import (
    fill_result_layout_2026,
    is_itau_layout_2026,
)
from scripts.e2.common import (
    BANCO_ITAU,
    CARTAO_PDA,
    FAMILY,
    ITAU_XLS_LAYOUT,
    MEMBROS,
    TITULAR,
    VENC_PDA,
    detect_member_from_card_name,
    detect_member_from_text,
    extract_account_number,
    infer_fatura_ref_from_filename,
    infer_periodo_from_filename,
    log,
    make_result_template,
    new_cdb_position_result,
    new_investment_position_result,
    parse_brl,
    read_pdf_text,
    resolve_date_ddmm,
    safe_date,
)
from scripts.e2.validation import apply_cdb_checksum, apply_rv_count_checksum

LOG_PREFIX_EXTRATO = "E2-EXTRATO"
LOG_PREFIX_FATURA = "E2-FATURA"

PARSERS = [
    # Anchors subtipo-agnósticos (sem underscore terminador) — casam subtipos de
    # moeda do E0 (extratocontausd/brl/eur/...). Ordem preserva o roteamento
    # format-specific: `.xls$` → parse_itau_xls antes do fallback any-ext.
    # Ver bankofamerica.py para o rationale completo.
    (r"^itau_extratocontapersonnalite_.*\.xls$", "parse_itau_xls"),
    (r"^itau_extratoconta.*\.xls$", "parse_itau_xls"),
    (r"^itau_extratocontapersonnalite_", "parse_itau"),
    (r"^itau_extratoconta", "parse_itau"),
    (r"^itau_cdbresumo_.*\.xls$", "parse_itau_cdb_html_xls"),
    (r"^itau_cdbdetalhes_.*\.xls$", "parse_itau_cdb_html_xls"),
    (r"^itau_cdbresumo_.*\.pdf$", "parse_itau_cdb_pdf"),
    (r"^itau_cdbdetalhes_.*\.pdf$", "parse_itau_cdb_pdf"),
    (r"itau_faturapaoacucar.*\.csv$", "parse_itau_paoacucar_csv"),
    (r"itau_faturapaoacucar", "parse_itau_paoacucar"),
    # Fatura de cartão não-cobranded. `_` terminador exclui `faturapaoacucar`
    # (roteia acima); disjunto, ordem relativa é indiferente.
    (r"^itau_fatura_", "parse_itau_fatura"),
    # Posição acionária (custódia escritural investfone) — PDF, só-quantidade.
    (r"^itau_investimentosposicao_.*\.pdf$", "parse_itau_investimentosposicao"),
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _fix_itau_xls_encoding(text: str) -> str:
    """Fix mojibake in Itaú XLS files (UTF-8 decoded as latin-1)."""
    if not text or not isinstance(text, str):
        return text or ""
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


# ---------------------------------------------------------------------------
# Extrato conta — XLS
# ---------------------------------------------------------------------------


def parse_itau_xls(xls_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú XLS bank statement exported from internet banking.

    Supports the standard Itaú XLS format with sheets:
    - Lançamentos (transactions)
    - Posição Consolidada (balance summary)
    - Limites (overdraft limits)
    """
    try:
        import xlrd
    except ImportError:
        log(LOG_PREFIX_EXTRATO, "ERROR", "xlrd not installed. Run: pip install xlrd")
        result = make_result_template(BANCO_ITAU, "extratoconta", "BRL")
        result["notas"].append("xlrd not installed — cannot parse XLS")
        result["requires_llm_fallback"] = True
        return result

    is_personnalite = "personnalite" in filename.lower()
    tipo = "extratocontapersonnalite" if is_personnalite else "extratoconta"

    log(LOG_PREFIX_EXTRATO, "INFO", f"Parsing Itaú XLS ({tipo}): {filename}")
    result = make_result_template(BANCO_ITAU, tipo, "BRL")
    result["tipo_conta"] = "corrente"

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        wb = xlrd.open_workbook(xls_path)

        # --- Sheet: Lançamentos ---
        if "Lançamentos" not in wb.sheet_names():
            sheet_names_lower = {s.lower(): s for s in wb.sheet_names()}
            lancamentos_name = sheet_names_lower.get("lançamentos") or sheet_names_lower.get(
                "lancamentos"
            )
            if not lancamentos_name:
                log(
                    LOG_PREFIX_EXTRATO,
                    "WARN",
                    f"  Sheet 'Lançamentos' não encontrada em {filename}",
                )
                result["notas"].append("Sheet Lançamentos não encontrada")
                result["requires_llm_fallback"] = True
                return result
        else:
            lancamentos_name = "Lançamentos"

        sh = wb.sheet_by_name(lancamentos_name)

        # --- Extract header info — layout from config ---
        _ih = ITAU_XLS_LAYOUT.get("header", {})
        _titular_r = _ih.get("titular_row", 2)
        _titular_c = _ih.get("titular_col", 1)
        _ag_r = _ih.get("agencia_row", 3)
        _ag_c = _ih.get("agencia_col", 1)
        _conta_r = _ih.get("conta_row", 4)
        _conta_c = _ih.get("conta_col", 1)

        if sh.nrows >= max(_titular_r, _ag_r, _conta_r) + 1:
            nome_raw = str(sh.cell(_titular_r, _titular_c).value).strip()
            nome = _fix_itau_xls_encoding(nome_raw)
            result["titular"] = detect_member_from_text(nome)

            ag_val = sh.cell(_ag_r, _ag_c).value
            agencia = str(int(ag_val)) if isinstance(ag_val, float) else str(ag_val).strip()
            result["agencia"] = agencia

            conta_val = str(sh.cell(_conta_r, _conta_c).value).strip()
            result["numero_conta"] = conta_val

        # --- Parse transactions ---
        saldo_anterior = None
        saldo_final = None
        in_future_section = False
        first_tx_date = None
        last_tx_date = None

        _data_start = ITAU_XLS_LAYOUT.get("data_start_row", 10)
        _icols = ITAU_XLS_LAYOUT.get("columns", {})
        _cd = _icols.get("data", 0)
        _cde = _icols.get("descricao", 1)
        _cv = _icols.get("valor", 3)
        _cs = _icols.get("saldo", 4)

        for r in range(_data_start, sh.nrows):
            cell_date = str(sh.cell(r, _cd).value).strip() if sh.ncols > _cd else ""
            cell_desc = str(sh.cell(r, _cde).value).strip() if sh.ncols > _cde else ""
            cell_valor = sh.cell(r, _cv).value if sh.ncols > _cv else ""
            cell_saldo = sh.cell(r, _cs).value if sh.ncols > _cs else ""

            cell_desc = _fix_itau_xls_encoding(cell_desc)

            desc_lower = cell_desc.lower()
            date_lower = cell_date.lower()
            if (
                "lançamentos futuros" in date_lower
                or "lançamentos futuros" in desc_lower
                or "lancamentos futuros" in date_lower
                or "lancamentos futuros" in desc_lower
                or "saídas futuras" in date_lower
                or "saidas futuras" in date_lower
            ):
                in_future_section = True
                continue

            if in_future_section:
                continue

            if not cell_date or cell_date.lower() in ("lançamentos", "lancamentos", ""):
                continue

            date_match = re.match(r"(\d{2})/(\d{2})/(\d{4})", cell_date)
            if not date_match:
                continue

            dd, mm, yyyy = date_match.group(1), date_match.group(2), date_match.group(3)
            iso_date = f"{yyyy}-{mm}-{dd}"

            # --- SALDO ANTERIOR ---
            if "SALDO ANTERIOR" in cell_desc.upper():
                saldo_val = (
                    cell_saldo
                    if isinstance(cell_saldo, (int, float)) and cell_saldo != ""
                    else None
                )
                if saldo_val is not None and saldo_val != "":
                    saldo_anterior = float(saldo_val)
                    first_tx_date = iso_date
                continue

            # --- SALDO TOTAL DISPONÍVEL DIA ---
            desc_upper = cell_desc.upper()
            if (
                "SALDO TOTAL DISPON" in desc_upper
                or "SALDO DO DIA" in desc_upper
                or "SALDO TOTAL DISPONÍVEL DIA" in desc_upper
                or "SALDO TOTAL DISPONIVEL DIA" in desc_upper
            ):
                saldo_val = (
                    cell_saldo
                    if isinstance(cell_saldo, (int, float)) and cell_saldo != ""
                    else None
                )
                if saldo_val is not None and saldo_val != "":
                    saldo_final = float(saldo_val)
                    last_tx_date = iso_date
                continue

            # --- Regular transaction ---
            if isinstance(cell_valor, (int, float)) and cell_valor != "":
                valor = float(cell_valor)
            elif isinstance(cell_valor, str) and cell_valor.strip():
                valor = parse_brl(cell_valor)
            else:
                continue

            if valor is None:
                continue

            result["transacoes"].append(
                {
                    "data": iso_date,
                    "descricao": cell_desc,
                    "valor": valor,
                }
            )

            if first_tx_date is None:
                first_tx_date = iso_date
            last_tx_date = iso_date

        # --- Derive saldos ---
        if saldo_anterior is not None:
            result["saldo_inicial"] = saldo_anterior
        if saldo_final is not None:
            result["saldo_final"] = saldo_final

        # --- Derive periodo from actual transaction dates ---
        if first_tx_date and (
            not result["periodo"]["inicio"] or result["periodo"]["inicio"] > first_tx_date
        ):
            result["periodo"]["inicio"] = first_tx_date
        if last_tx_date and (
            not result["periodo"]["fim"] or result["periodo"]["fim"] < last_tx_date
        ):
            result["periodo"]["fim"] = last_tx_date

        # --- Sheet: Posição Consolidada (optional enrichment) ---
        if "Posição Consolidada" in wb.sheet_names():
            try:
                sh_pos = wb.sheet_by_name("Posição Consolidada")
                for r in range(8, sh_pos.nrows):
                    desc = str(sh_pos.cell(r, 0).value).strip().lower()
                    val = sh_pos.cell(r, 3).value if sh_pos.ncols > 3 else ""
                    if "(=) saldo total disponível" in desc and isinstance(val, (int, float)):
                        if result["saldo_final"] is None:
                            result["saldo_final"] = float(val)
            except Exception:
                pass

        # A39.l7 · ADR-342: saldo_inicial (SALDO ANTERIOR) e saldo_final vêm de
        # células independentes (não derivados) → declara verificabilidade p/ o
        # gate HARD graduar conservação. Wise/Rico ficam fora (saldo derivado).
        if (
            result.get("saldo_inicial") is not None
            and result.get("saldo_final") is not None
            and result["transacoes"]
        ):
            result["conservacao_verificavel"] = True

    except Exception as e:
        log(LOG_PREFIX_EXTRATO, "ERROR", f"  Falha ao processar XLS {filename}: {e}")
        result["notas"].append(f"Erro no parsing XLS: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX_EXTRATO, "INFO", f"  → {len(result['transacoes'])} transações extraídas do XLS")
    return result


# ---------------------------------------------------------------------------
# Extrato conta — PDF
# ---------------------------------------------------------------------------


def parse_itau(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú bank statement."""
    is_personnalite = "personnalite" in filename.lower()
    tipo = "extratocontapersonnalite" if is_personnalite else "extratoconta"

    log(LOG_PREFIX_EXTRATO, "INFO", f"Parsing Itaú ({tipo}): {filename}")
    result = make_result_template(BANCO_ITAU, tipo, "BRL")
    result["tipo_conta"] = "corrente"

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_text = pdf.pages[0].extract_text() or ""
            result["titular"] = detect_member_from_text(first_text)
            result["numero_conta"] = extract_account_number(first_text, "itau")
            ag_m = re.search(r"Ag[êe]ncia[:\s]+(\d+)", first_text)
            if ag_m:
                result["agencia"] = ag_m.group(1)

            if is_itau_layout_2026(first_text):
                # extract_tables() fragmenta este layout e perdia ~50% das
                # linhas (A38.l2) — caminho line-based dedicado.
                fill_result_layout_2026(pdf, first_text, result)
                log(
                    LOG_PREFIX_EXTRATO,
                    "INFO",
                    f"  → {len(result['transacoes'])} transações extraídas (layout 2026)",
                )
                return result

            pm = re.search(
                r"Per[ií]odo[:\s]+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})", first_text
            )
            if pm:
                parts1 = pm.group(1).split("/")
                parts2 = pm.group(2).split("/")
                result["periodo"]["inicio"] = f"{parts1[2]}-{parts1[1]}-{parts1[0]}"
                result["periodo"]["fim"] = f"{parts2[2]}-{parts2[1]}-{parts2[0]}"

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

                while len(cols) < 4:
                    cols.append("")

                date_str, descricao, valor_str, saldo_str = cols[0], cols[1], cols[2], cols[3]

                if date_str.lower() in ("data", ""):
                    if descricao.lower() in ("lançamentos", "lancamentos", ""):
                        continue

                if not date_str and not descricao:
                    continue

                date_match = re.match(r"(\d{2}/\d{2}/\d{4})", date_str)
                if not date_match:
                    continue

                parts = date_match.group(1).split("/")
                iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"

                if "SALDO DO DIA" in descricao.upper():
                    saldo_val = parse_brl(saldo_str) or parse_brl(valor_str)
                    if saldo_val is not None:
                        saldo_values.append((iso_date, saldo_val))
                    continue

                valor = parse_brl(valor_str)
                if valor is None:
                    continue

                result["transacoes"].append(
                    {
                        "data": iso_date,
                        "descricao": descricao,
                        "valor": valor,
                    }
                )

            if saldo_values:
                saldo_values.sort(key=lambda x: x[0])
                result["saldo_inicial"] = saldo_values[0][1]
                result["saldo_final"] = saldo_values[-1][1]

    except Exception as e:
        log(LOG_PREFIX_EXTRATO, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX_EXTRATO, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# ---------------------------------------------------------------------------
# CDB investment — HTML-as-XLS
# ---------------------------------------------------------------------------


def parse_itau_cdb_html_xls(xls_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú CDB investment extract from HTML-as-XLS export.

    These .xls files from Itaú internet banking are actually HTML tables.
    Extracts position data, balances, and summary for CDB investments.
    Output is compatible with E4's build_investimentos_unified().
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log(
            LOG_PREFIX_EXTRATO,
            "ERROR",
            "beautifulsoup4 not installed. Run: pip install beautifulsoup4",
        )
        return {"requires_llm_fallback": True, "tipo": "cdbresumo"}

    log(LOG_PREFIX_EXTRATO, "INFO", f"Parsing Itaú CDB HTML-XLS: {filename}")

    result = {
        # ADR-284/A24.l7: `banco` aditivo ao lado de `instituicao` (valor idêntico)
        # — satisfaz required do e2_extract.schema.json; E4 lê `instituicao or banco`.
        "banco": BANCO_ITAU,
        "instituicao": BANCO_ITAU,
        "tipo": "cdbresumo",
        "tipo_produto": None,
        "tipo_conta": "investimento",
        "membro": None,
        "moeda": "BRL",
        "numero_conta": None,
        "agencia": None,
        "data_referencia": None,
        "periodo": {"inicio": None, "fim": None},
        "saldo_anterior": None,
        "saldo_atual": None,
        "resumo": {},
        "posicoes": [],
        "notas": [],
    }

    try:
        # Alguns exports do Itaú são XLS binário real (CDFV2 / "Microsoft Excel"),
        # não HTML-as-XLS — abrir como texto crasha com UnicodeDecodeError. Sniff
        # pelos magic bytes e delega para LLM fallback quando não for HTML.
        with open(xls_path, "rb") as f:
            head = f.read(8)
        if head.startswith(b"\xd0\xcf\x11\xe0") or head.startswith(b"PK"):
            result["notas"].append(
                "Arquivo XLS binário (não HTML) — parser determinístico não suporta"
            )
            result["requires_llm_fallback"] = True
            return result

        with open(xls_path, "r", encoding="windows-1252", errors="replace") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")

        if not tables:
            result["notas"].append("Nenhuma tabela encontrada no HTML")
            result["requires_llm_fallback"] = True
            return result

        main_table = tables[0]
        rows = main_table.find_all("tr")

        def get_cells(row):
            """Extract text from all cells in a row."""
            return [c.get_text(strip=True) for c in row.find_all(["td", "th"])]

        # --- Parse structured data by scanning rows ---
        for i, row in enumerate(rows):
            cells = get_cells(row)
            if not cells or not any(cells):
                continue

            if len(cells) >= 1 and "Extrato de movimentação mensal" in cells[0]:
                title = cells[0]
                dash_idx = title.find(" - ")
                if dash_idx >= 0:
                    result["tipo_produto"] = title[dash_idx + 3 :].strip()

            if len(cells) >= 3 and cells[1] == "Nome:":
                nome = cells[2]
                result["membro"] = detect_member_from_text(nome)

            if len(cells) >= 5 and cells[1] == "Agência:" and cells[3] == "Conta:":
                result["agencia"] = cells[2]
                result["numero_conta"] = cells[4]

            if len(cells) >= 3 and cells[1] == "Período:":
                periodo_str = cells[2]
                m = re.search(r"(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})", periodo_str)
                if m:
                    p1, p2 = m.group(1).split("/"), m.group(2).split("/")
                    result["periodo"]["inicio"] = f"{p1[2]}-{p1[1]}-{p1[0]}"
                    result["periodo"]["fim"] = f"{p2[2]}-{p2[1]}-{p2[0]}"
                    result["data_referencia"] = result["periodo"]["fim"]

            if len(cells) >= 3 and "SALDO ANTERIOR" in cells[1].upper():
                val = parse_brl(cells[2])
                if val is not None:
                    result["saldo_anterior"] = val

            if len(cells) >= 3 and "SALDO FINAL" in cells[1].upper():
                result["saldo_atual"] = parse_brl(cells[2])

            if len(cells) >= 9 and cells[0] == "Total:":
                result["resumo"] = {
                    "saldo_anterior": parse_brl(cells[1]),
                    "aplicacoes": parse_brl(cells[2]),
                    "resgates": parse_brl(cells[3]),
                    "vencimentos": parse_brl(cells[4]),
                    "rendimento_acumulado": parse_brl(cells[5]),
                    "saldo_bruto_final": parse_brl(cells[6]),
                    "impostos_estimados": parse_brl(cells[7]),
                    "saldo_final_liquido": parse_brl(cells[8]),
                }

            if len(cells) >= 8 and re.match(r"^\d{10,}$", cells[0]):
                n_operacao = cells[0]
                data_vencimento_raw = cells[1]
                data_aplicacao_raw = cells[2]
                valor_aplicacao = parse_brl(cells[3])
                remuneracao_pct = parse_brl(cells[4])
                valor_anterior = parse_brl(cells[5])
                valor_atual = parse_brl(cells[6])
                rentab_periodo = parse_brl(cells[7])

                def convert_date(d):
                    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d)
                    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else d

                posicao = {
                    "nome": f"{result.get('tipo_produto', 'CDB')} - Op. {n_operacao}",
                    "tipo": result.get("tipo_produto", "CDB"),
                    "n_operacao": n_operacao,
                    "data_vencimento": convert_date(data_vencimento_raw),
                    "data_aplicacao": convert_date(data_aplicacao_raw),
                    "valor_aplicacao": valor_aplicacao,
                    "remuneracao_pct": remuneracao_pct,
                    "valor_anterior": valor_anterior,
                    "valor_total": valor_atual,
                    "valor_atual": valor_atual,
                    "rentabilidade_periodo_pct": rentab_periodo,
                }
                result["posicoes"].append(posicao)

    except Exception as e:
        log(LOG_PREFIX_EXTRATO, "ERROR", f"  Falha ao processar CDB HTML-XLS {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    n_pos = len(result["posicoes"])
    saldo = result.get("saldo_atual", 0) or 0
    log(LOG_PREFIX_EXTRATO, "INFO", f"  → {n_pos} posições CDB, saldo R$ {saldo:,.2f}")
    # Escopo bruto: Σ valor_atual (cells[6]) casa com saldo_bruto_final, NUNCA
    # com SALDO FINAL líquido (saldo_atual) — ADR-342 §Emenda 2026-07-23.
    apply_cdb_checksum(result, (result.get("resumo") or {}).get("saldo_bruto_final"))
    return result


# ---------------------------------------------------------------------------
# Fatura Pão de Açúcar — PDF
# ---------------------------------------------------------------------------


def parse_itau_paoacucar(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú Pão de Açúcar credit card invoice.

    Key challenge: pdfplumber merges left and right columns into single lines.
    The "Lançamentos" table (left) and "Encargos" table (right) get concatenated.
    We handle this by matching transaction patterns at the START of lines and
    truncating any right-column junk.
    """
    log(LOG_PREFIX_FATURA, "INFO", f"Parsing Itaú Pão de Açúcar: {filename}")

    # Token ancorado ao fim do stem (documents.period via routing) — busca livre
    # de 6 dígitos casava o prefixo sha256[:12] e gerava 2100/1899 (A32.l3).
    ref_year, ref_month = infer_fatura_ref_from_filename(filename)

    result = {
        "banco": BANCO_ITAU,
        "tipo": "faturapaoacucar",
        "cartao": CARTAO_PDA,
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
        _itau_regex = TITULAR.get("regex_nome_fatura", {}).get("itau_paoacucar", "")
        m = re.search(_itau_regex, full_text) if _itau_regex else None
        if m:
            result["titular"] = m.group(1)

        m = re.search(r"Vencimento:\s*(\d{2}/\d{2}/\d{4})", full_text)
        if m:
            parts = m.group(1).split("/")
            result["data_vencimento"] = f"{parts[2]}-{parts[1]}-{parts[0]}"

        m = re.search(r"Total desta fatura\s+([\d.,]+)", full_text)
        if m:
            result["saldo_atual"] = parse_brl(m.group(1))

        m = re.search(r"Total da fatura anterior\s+([\d.,]+)", full_text)
        if m:
            result["saldo_anterior"] = parse_brl(m.group(1))

        m = re.search(r"Pagamento efetuado em \d+/\d+/\d+\s+(-?\s*[\d.,]+)", full_text)
        if m:
            val = parse_brl(m.group(1))
            result["pagamentos"] = -abs(val) if val else None

        m = re.search(r"Lançamentos atuais\s+([\d.,]+)", full_text)
        if m:
            result["total_compras"] = parse_brl(m.group(1))

        m = re.search(r"Cartão\s+([\d.X]+)", full_text)
        if m:
            result["numero_cartao"] = m.group(1)

        # --- Transactions ---
        tx_pattern = re.compile(
            r"(?:@\s*)?(\d{2}/\d{2})\s+"  # date
            r"(.+?)\s+"  # description (lazy)
            r"(\d{1,2}/\d{1,2})\s+"  # parcela (NN/NN)
            r"([\d.,]+)"  # value
        )
        tx_simple = re.compile(
            r"(?:@\s*)?(\d{2}/\d{2})\s+"  # date
            r"(.+?)\s+"  # description (lazy)
            r"([\d.,]+)"  # value
        )

        current_card = None
        in_lancamentos = False
        in_parceladas = False

        for line in full_text.split("\n"):
            if "Lançamentos: compras e saques" in line or "Lançamentos:compras e saques" in line:
                in_lancamentos = True
                in_parceladas = False
                continue
            if "Lançamentos internacionais" in line:
                in_lancamentos = True
                in_parceladas = False
                continue
            if "Compras parceladas" in line and "próximas faturas" in line:
                in_lancamentos = False
                in_parceladas = True
                continue
            has_card_header = bool(re.search(r"\(final\s+\d+\)", line))
            has_tx_date = bool(re.match(r"\s*(?:@\s*)?\d{2}/\d{2}\s", line.strip()))
            if not has_card_header and not has_tx_date:
                if any(
                    s in line
                    for s in [
                        "Fique atento",
                        "Continua...",
                        "Pagamentos em",
                        "lojas são aceitos",
                        "apenas em dinheiro",
                        "cartão de débito",
                        "Não são aceitos",
                    ]
                ):
                    in_lancamentos = False
                    in_parceladas = False
                    continue
                if re.match(r"^\s*Limites de crédito\s*$", line):
                    in_lancamentos = False
                    in_parceladas = False
                    continue

            if not (in_lancamentos or in_parceladas):
                continue

            card_m = re.search(r"([A-Z][\w\s]+)\(final\s+(\d+)\)", line)
            if card_m:
                current_card = f"{card_m.group(1).strip()} (final {card_m.group(2)})"

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

        log(
            LOG_PREFIX_FATURA,
            "INFO",
            f"  → {len(result['transacoes'])} transações, {len(result['compras_parceladas_futuras'])} parceladas futuras",
        )
    except Exception as e:
        log(LOG_PREFIX_FATURA, "ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    return result


# ---------------------------------------------------------------------------
# Fatura Itaú (cartão não-cobranded) — PDF via extract_words
# ---------------------------------------------------------------------------
#
# O layout Itaú funde duas tabelas lado-a-lado (Lançamentos à esquerda;
# Limites/Encargos/CET à direita) e ainda tem um sub-layout SEM ESPAÇOS (o
# pdfplumber concatena frases inteiras num só "word"). extract_text() perde a
# separação de coluna; extract_words() preserva o x de cada token → filtrar
# `x0 < _ITAU_COL_SPLIT` descarta a poluição da direita mesmo no sub-layout
# denso. O valor R$ é sempre o token monetário mais à direita da coluna
# esquerda (a descrição vem antes).
_ITAU_COL_SPLIT = 360.0
_ITAU_DATE_RE = re.compile(r"^(\d{2})/(\d{2})$")
_ITAU_MONEY_RE = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d{2}$")
_ITAU_SUMMARY_PREFIXES = (
    "lançamentosnocartão",
    "total",  # Total transações inter., Total lançamentos inter., Total dos lançamentos atuais
    "ltotal",
    "dólardeconversão",
    "dolardeconversão",
    "próximafatura",
    "proximafatura",
    "demaisfaturas",
    "dataestabelecimento",
)


def _itau_norm(joined: str) -> str:
    return re.sub(r"\s+", "", joined).lower()


def _itau_left_lines(page: Any) -> List[List[Dict[str, Any]]]:
    """Reconstrói as linhas da coluna esquerda (tx) agrupando words por `top`.
    Descarta a coluna direita (x0 ≥ split) — poluição de Limites/Encargos/CET."""
    words = sorted(
        (w for w in page.extract_words() if w["x0"] < _ITAU_COL_SPLIT),
        key=lambda w: (round(w["top"]), w["x0"]),
    )
    lines: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    cur_top: Optional[int] = None
    for w in words:
        top = round(w["top"])
        if cur_top is not None and abs(top - cur_top) > 3:
            lines.append(cur)
            cur = []
        cur.append(w)
        cur_top = top
    if cur:
        lines.append(cur)
    return lines


def _itau_line_value(words: List[Dict[str, Any]]) -> Optional[float]:
    """Valor R$ = token monetário mais à direita (descrição/US$ vêm antes)."""
    money = [w for w in words if _ITAU_MONEY_RE.match(w["text"])]
    return parse_brl(max(money, key=lambda w: w["x0"])["text"]) if money else None


def _itau_fatura_section(nline: str, current: str) -> str:
    if nline.startswith("lançamentos:comprasesaques") or nline.startswith(
        "lançamentoscomprasesaques"
    ):
        return "nacional"
    if nline.startswith("lançamentosinternacionais"):
        return "internacional"
    if nline.startswith("comprasparceladas"):
        return "future"
    if nline.startswith("limitesdecrédito") or nline.startswith("encargoscobrados"):
        return "stop"
    return current


def _itau_fatura_tx(words: List[Dict[str, Any]], val: float, ref_year, ref_month) -> Dict[str, Any]:
    dm = _ITAU_DATE_RE.match(words[0]["text"])
    dd, mm = int(dm.group(1)), int(dm.group(2))
    desc = " ".join(w["text"] for w in words[1:] if not _ITAU_MONEY_RE.match(w["text"]))
    return {
        "data": resolve_date_ddmm(dd, mm, ref_year, ref_month),
        "descricao": desc.strip(),
        "valor": val,
        "escopo": "lancamentos_atuais",
    }


def _itau_iof_tx(val: float, data_venc) -> Dict[str, Any]:
    return {
        "data": data_venc,
        "descricao": "Repasse de IOF",
        "valor": val,
        "escopo": "lancamentos_atuais",
    }


def _append_itau_fatura_tx(
    words: List[Dict[str, Any]],
    nline: str,
    section: str,
    result: Dict[str, Any],
    ref_year,
    ref_month,
) -> None:
    """Datada (nacional/intl) → tx; "Repasse de IOF" (sem data, só internacional)
    → tx de IOF (o emissor o conta em "Total lançamentos inter.", parte do total)."""
    if _ITAU_DATE_RE.match(words[0]["text"]):
        val = _itau_line_value(words)
        if val is not None:
            result["transacoes"].append(_itau_fatura_tx(words, val, ref_year, ref_month))
    elif section == "internacional" and nline.startswith("repassedeiof"):
        val = _itau_line_value(words)
        if val is not None:
            result["transacoes"].append(_itau_iof_tx(val, result.get("data_vencimento")))


def _consume_itau_fatura_line(
    words: List[Dict[str, Any]], section: str, result: Dict[str, Any], ref_year, ref_month
) -> str:
    nline = _itau_norm(" ".join(w["text"] for w in words))
    new_section = _itau_fatura_section(nline, section)
    if new_section != section:
        return new_section  # linha de header não carrega tx
    if section in ("nacional", "internacional") and not (
        "(final" in nline or nline.startswith(_ITAU_SUMMARY_PREFIXES)
    ):
        _append_itau_fatura_tx(words, nline, section, result, ref_year, ref_month)
    return section


def _fill_itau_fatura_header(result: Dict[str, Any], full_text: str) -> None:
    m = re.search(r"Vencimento:\s*(\d{2}/\d{2}/\d{4})", full_text)
    if m:
        d, mo, y = m.group(1).split("/")
        result["data_vencimento"] = f"{y}-{mo}-{d}"
    m = re.search(r"Total\s*desta\s*fatura\s+([\d.,]+)", full_text)
    if m:
        result["saldo_atual"] = parse_brl(m.group(1))
    m = re.search(r"Total\s*da\s*fatura\s*anterior\s+([\d.,]+)", full_text)
    if m:
        result["saldo_anterior"] = parse_brl(m.group(1))
    m = re.search(r"Pagamento\s*efetuado\s*em\s*\d+/\d+/\d+\s*(-?\s*[\d.,]+)", full_text)
    if m:
        val = parse_brl(m.group(1).replace(" ", ""))
        result["pagamentos"] = -abs(val) if val else None
    # Âncora do checksum: "Lançamentos atuais" (compras do período, exclui
    # rotativo/saldo financiado — ADR-342 proíbe usar "Total desta fatura").
    m = re.search(r"Lan[çc]amentos\s*atuais\s+([\d.,]+)", full_text)
    if m:
        result["total_compras"] = parse_brl(m.group(1))


def _new_itau_fatura_result() -> Dict[str, Any]:
    return {
        "banco": BANCO_ITAU,
        "tipo": "faturaitau",
        "cartao": "Itaú",
        "titular": None,
        "moeda": "BRL",
        "data_vencimento": None,
        "saldo_anterior": None,
        "total_compras": None,
        "pagamentos": None,
        "saldo_atual": None,
        "transacoes": [],
    }


def _extract_itau_fatura(pdf: Any, result: Dict[str, Any], ref_year, ref_month) -> None:
    full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    m = re.search(r"Titular\s+([A-ZÀ-Ú][A-ZÀ-Ú ]+)", full_text)
    if m:
        result["titular"] = m.group(1).strip()
    _fill_itau_fatura_header(result, full_text)
    section = ""
    for page in pdf.pages:
        for words in _itau_left_lines(page):
            section = _consume_itau_fatura_line(words, section, result, ref_year, ref_month)
    if result["total_compras"] is not None:
        result["total_lancamentos_conferivel"] = {
            "valor_cents": round(result["total_compras"] * 100),
            "escopo": "lancamentos_atuais",
        }


def parse_itau_fatura(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú credit-card invoice (cartão não-cobranded; layout denso)."""
    log(LOG_PREFIX_FATURA, "INFO", f"Parsing Itaú Fatura: {filename}")
    ref_year, ref_month = infer_fatura_ref_from_filename(filename)
    result = _new_itau_fatura_result()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            _extract_itau_fatura(pdf, result, ref_year, ref_month)
    except Exception as e:
        log(LOG_PREFIX_FATURA, "ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}
    log(LOG_PREFIX_FATURA, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result


# ---------------------------------------------------------------------------
# Fatura Pão de Açúcar — CSV
# ---------------------------------------------------------------------------


def parse_itau_paoacucar_csv(csv_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Itaú Pão de Açúcar credit card invoice from CSV export.

    CSV structure:
      - UTF-8 BOM header
      - 3 columns: data, lançamento, valor
      - Dates already in ISO format (YYYY-MM-DD)
      - Values as plain decimals (negative = payments/credits)
      - Filename encodes due date: fatura-YYYYMMDD.csv
    """
    log(LOG_PREFIX_FATURA, "INFO", f"Parsing Itaú Pão de Açúcar CSV: {filename}")

    data_vencimento = None
    is_fatura_aberta = False

    m = re.search(r"fatura-(\d{8})", filename)
    if m:
        date_str = m.group(1)
        if date_str == "99999999":
            is_fatura_aberta = True
        else:
            y, mo, d = date_str[:4], date_str[4:6], date_str[6:8]
            data_vencimento = f"{y}-{mo}-{d}"

    if not data_vencimento and not is_fatura_aberta:
        # Token ancorado ao fim do stem (documents.period via routing) — busca
        # livre de 6 dígitos casava o prefixo sha256[:12] e gerava 2100/1899
        # (A32.l3).
        ref_year, ref_month = infer_fatura_ref_from_filename(filename)
        if ref_year and ref_month:
            data_vencimento = f"{ref_year}-{ref_month:02d}-{VENC_PDA:02d}"

    result = {
        "banco": BANCO_ITAU,
        "tipo": "faturapaoacucar",
        "cartao": CARTAO_PDA,
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
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()

        if not lines:
            log(LOG_PREFIX_FATURA, "WARN", f"  CSV vazio: {filename}")
            return result

        header = lines[0].strip().lower()
        if "data" not in header or "valor" not in header:
            log(LOG_PREFIX_FATURA, "WARN", f"  Header CSV inesperado: {header}")
            result["notas"] = result.get("notas", []) + [f"Header inesperado: {header}"]
            return result

        total_pagamentos = 0.0
        total_compras = 0.0

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            parts = line.split(",")
            if len(parts) < 3:
                continue

            data = parts[0].strip()
            valor_str = parts[-1].strip()
            descricao = ",".join(parts[1:-1]).strip()

            if not re.match(r"\d{4}-\d{2}-\d{2}$", data):
                continue

            try:
                valor = float(valor_str)
            except ValueError:
                valor = parse_brl(valor_str)
                if valor is None:
                    continue

            parcela = None
            parcela_m = re.search(r"(\d{1,2}/\d{1,2})$", descricao)
            if parcela_m:
                parcela = parcela_m.group(1)

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

            if is_pagamento:
                total_pagamentos += valor
            elif valor < 0 and not is_estorno:
                total_pagamentos += valor
            else:
                total_compras += valor

        if total_pagamentos != 0:
            result["pagamentos"] = total_pagamentos
        if total_compras != 0:
            result["total_compras"] = total_compras

        result["saldo_atual"] = (
            round(total_compras + total_pagamentos, 2) if result["transacoes"] else None
        )

        if not result["titular"]:
            result["titular"] = TITULAR.get("variantes_nome", [TITULAR.get("nome_completo")])[0]

    except Exception as e:
        log(LOG_PREFIX_FATURA, "ERROR", f"  Falha ao processar CSV {filename}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    log(LOG_PREFIX_FATURA, "INFO", f"  → {len(result['transacoes'])} transações extraídas do CSV")
    return result


# ---------------------------------------------------------------------------
# CDB — posição/movimentação em PDF ("Extrato de movimentação mensal") — A38.l12
# ---------------------------------------------------------------------------

_ITAU_CDB_PRODUTO_RE = re.compile(
    r"Extrato\s+de\s+movimenta[çc][ãa]o\s+mensal\s*-\s*(.+)", re.IGNORECASE
)
_ITAU_CDB_SALDO_FINAL_RE = re.compile(r"SALDO\s+FINAL\s+([\d.,]+)", re.IGNORECASE)
# Linha da "Posição em": <n_op> <venc> <aplic> <valor_aplic> <remun%> <valor_ant> <valor_atual> <rentab%>
_ITAU_CDB_POSICAO_RE = re.compile(
    r"^\d{6,}\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)"
)


def _iso_br(d: str) -> str:
    p = d.split("/")
    return f"{p[2]}-{p[1]}-{p[0]}" if len(p) == 3 else d


def _cdb_empty_reason() -> Dict[str, str]:
    return {"code": "extract.empty_result", "message": "CDB sem SALDO FINAL — escalado (ADR-342)"}


def _itau_cdb_posicao(full_text: str) -> Optional[Dict[str, Any]]:
    """Posição única do CDB (valor = SALDO FINAL); None se não há saldo final."""
    saldo_m = _ITAU_CDB_SALDO_FINAL_RE.search(full_text)
    saldo_final = parse_brl(saldo_m.group(1)) if saldo_m else None
    if saldo_final is None:
        return None
    prod_m = _ITAU_CDB_PRODUTO_RE.search(full_text)
    posicao: Dict[str, Any] = {
        "nome": re.sub(r"\s+", " ", prod_m.group(1)).strip() if prod_m else "CDB",
        "valor_atual": saldo_final,
    }
    pos_m = _ITAU_CDB_POSICAO_RE.search(full_text)
    if pos_m:
        posicao["data_vencimento"] = _iso_br(pos_m.group(1))
        posicao["data_aplicacao"] = _iso_br(pos_m.group(2))
    return posicao


def parse_itau_cdb_pdf(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Posição de CDB Itaú em PDF (movimentação mensal); emite cdbresumo + posicoes (ADR-342)."""
    log(LOG_PREFIX_EXTRATO, "INFO", f"Parsing Itaú CDB PDF: {filename}")
    result = new_cdb_position_result(BANCO_ITAU)
    full_text = read_pdf_text(pdf_path)
    if not full_text:
        result["requires_llm_fallback"] = True
        return result

    result["titular"] = detect_member_from_text(full_text)
    posicao = _itau_cdb_posicao(full_text)
    if posicao is None:
        result["requires_llm_fallback"] = True
        result["escalation_reason"] = _cdb_empty_reason()
    else:
        result["posicoes"].append(posicao)

    log(LOG_PREFIX_EXTRATO, "INFO", f"  → {len(result['posicoes'])} posição(ões) de CDB")
    return result


# Total (col após Livres/Bloqueadas) é o inteiro imediatamente antes do ticker;
# `Preferencial778` cola Tipo+Livres no extract_words, então contar 3 ints falha
# — ancorar no ticker é robusto ao sub-layout sem espaços (ADR-346 · A39.l9).
_ITAU_RV_TICKER_RE = re.compile(r"^(.*?)\s+(\d+)\s+([A-Z]{4}\d{1,2})\s*$")
_ITAU_RV_ROW_END_RE = re.compile(r"[A-Z]{4}\d{1,2}\s*$")


def _itau_rv_lines(pdf: Any) -> List[str]:
    """Reconstrói linhas via extract_words (agrupa por `top`) — extract_text
    intercala colunas do layout de custódia."""
    lines: List[str] = []
    for page in pdf.pages:
        words = sorted(page.extract_words(), key=lambda w: (round(w["top"]), w["x0"]))
        cur: List[str] = []
        cur_top: Optional[int] = None
        for w in words:
            top = round(w["top"])
            if cur_top is not None and abs(top - cur_top) > 3:
                lines.append(" ".join(cur))
                cur = []
            cur.append(w["text"])
            cur_top = top
        if cur:
            lines.append(" ".join(cur))
    return lines


def _itau_rv_position(line: str) -> Optional[Dict[str, Any]]:
    m = _ITAU_RV_TICKER_RE.match(line)
    if not m:
        return None
    # `nome` (não `empresa`): campo de rótulo canônico das 3 famílias de posição
    # (CDB/Rico/Itaú) — o badge de ressalva em E4 lê `nome` (senão mostra "?").
    nome = re.sub(r"[\d\s]+$", "", m.group(1)).strip()
    return {"ticker": m.group(3), "nome": nome, "quantidade": int(m.group(2))}


def _extract_itau_rv(lines: List[str]) -> Tuple[List[Dict[str, Any]], int]:
    """Posições + n_papéis observado (linha terminada em ticker, exceto TOTAL)."""
    posicoes: List[Dict[str, Any]] = []
    raw_detected = 0
    for line in lines:
        if line.upper().startswith("TOTAL") or not _ITAU_RV_ROW_END_RE.search(line):
            continue
        raw_detected += 1
        pos = _itau_rv_position(line)
        if pos is not None:
            posicoes.append(pos)
    return posicoes, raw_detected


def parse_itau_investimentosposicao(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Posição acionária Itaú (custódia escritural): só-quantidade, sem valor (ADR-346)."""
    log(LOG_PREFIX_EXTRATO, "INFO", f"Parsing Itaú posição acionária: {filename}")
    result = new_investment_position_result(BANCO_ITAU)
    if pdfplumber is None:
        result["requires_llm_fallback"] = True
        return result
    with pdfplumber.open(pdf_path) as pdf:
        lines = _itau_rv_lines(pdf)
    result["titular"] = detect_member_from_text("\n".join(lines))
    result["posicoes"], raw_detected = _extract_itau_rv(lines)
    apply_rv_count_checksum(result, raw_detected)
    log(LOG_PREFIX_EXTRATO, "INFO", f"  → {len(result['posicoes'])} posição(ões) RV")
    return result
