#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser Bradesco — extratos de conta corrente e poupança (PDF texto).

Extrai transações do layout multi-linha usado nos PDFs Bradesco.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from scripts.e2.common import (
    BANCO_BRADESCO,
    detect_member_from_text,
    infer_periodo_from_filename,
    log,
    make_result_template,
    parse_brl,
    safe_date,
)

LOG_PREFIX = "E2-EXTRATO"

PARSERS = [
    (r"^bradesco_extratopoupanca_", "parse_bradesco"),
    # Anchor subtipo-agnóstico (sem terminador) — ver bankofamerica.py. Poupança
    # tem stem distinto (`extratopoupanca`) e permanece com anchor próprio acima.
    (r"^bradesco_extratoconta", "parse_bradesco"),
]


def parse_bradesco(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse Bradesco bank statement (conta corrente or poupança)."""
    is_poupanca = "poupanca" in filename.lower()
    tipo = "extratopoupanca" if is_poupanca else "extratoconta"

    log(LOG_PREFIX, "INFO", f"Parsing Bradesco ({tipo}): {filename}")
    result = make_result_template(BANCO_BRADESCO, tipo, "BRL")
    result["tipo_conta"] = "poupanca" if is_poupanca else "corrente"

    if pdfplumber is None:
        log(LOG_PREFIX, "ERROR", "pdfplumber not installed. Run: pip install pdfplumber")
        result["notas"].append("pdfplumber not installed — cannot parse PDF")
        result["requires_llm_fallback"] = True
        return result

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
            m = re.search(r"Ag[:\s]+(\d+)\s*\|\s*Conta[:\s]+([\d-]+)", all_text)
            if m:
                result["agencia"] = m.group(1)
                result["numero_conta"] = m.group(2)

            # Periodo: "Entre DD/MM/YYYY e DD/MM/YYYY"
            pm = re.search(r"Entre\s+(\d{2}/\d{2}/\d{4})\s+e\s+(\d{2}/\d{2}/\d{4})", all_text)
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

            # Bradesco PDF footer/boilerplate patterns to skip
            _bradesco_skip = re.compile(
                r"(?i)"
                r"(?:Fone\s+F[áa]cil|Capitais\s+e\s+Regi|Demais\s+Regi|"
                r"SAC\s+-|Ouvidoria|Se\s+[Pp]referir|BIA\s+pelo|"
                r"Atendimento\s+(?:24h|dispon|eletr|de\s+segunda|personal)|"
                r"fale\s+com\s+a\s+BIA|WhatsApp|Fale\s+Conosco|"
                r"Cancelamento.*reclama|sugest[ãa]o\s+e\s+elogio|"
                r"N[ãa]o\s+h[áa]\s+lan[çc]amentos|Os\s+dados\s+acima|"
                r"Domingos\s+e\s+feriados|Demais\s+telefones|"
                r"Saldo\s+Invest\s+F[áa]cil|"
                r"^\s*0800\s|"
                r"desenho\s+do\s+cadeado|Consulta\s+de\s+saldo|"
                r"Para\s+consultas\s+de\s+um\s+per[íi]odo|"
                r"transa[çc][õo]es\s+financeiras|"
                r"Bradesco\s+Internet\s+Banking|"
                r"Nome:\s+|Extrato\s+de:\s+Ag:|"
                r"^\s*metropolitanas\s*$|^\s*aparecer\s|^\s*Seguran[çc]a\s*$|"
                r"^\s*4002\s+0022\s*$|^\s*elogio\b)"
            )

            # Also track when we hit "Total" line — everything after is boilerplate
            _bradesco_end_marker = re.compile(r"^Total\s+[\d.,]+")

            # Find SALDO ANTERIOR
            for line in lines:
                m = re.match(r"(\d{2}/\d{2}/\d{2})\s+SALDO ANTERIOR\s+([\d.,]+)", line)
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

            tx_date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{2})\s+(.*)")

            # Parse transaction blocks
            # Bradesco multi-line format:
            #   DD/MM/YY desc DOCTO [CREDIT] [- DEBIT] [SALDO]   ← date line
            #   Transfe Pix                                        ← description line
            #   DOCTO - DEBIT_VALUE [SALDO]                        ← amount line
            #   Des: Name DD/MM                                    ← detail line
            #
            # Key: description comes BEFORE the amount line, so we
            # track a 'pending_desc' to carry it forward.

            i = 0
            pending_desc = ""  # accumulates description text for next amount line
            past_end = False  # set True after "Total ..." line

            while i < len(lines):
                line = lines[i].strip()

                # After "Total" summary line, everything is boilerplate
                if _bradesco_end_marker.match(line):
                    past_end = True
                if past_end:
                    # Reset if we hit a new "Extrato de:" header (multi-account PDF)
                    if re.search(r"Entre\s+\d{2}/\d{2}/\d{4}\s+e\s+\d{2}/\d{2}/\d{4}", line):
                        past_end = False
                    else:
                        i += 1
                        continue

                # Skip Bradesco PDF footer/boilerplate lines
                if _bradesco_skip.search(line):
                    i += 1
                    continue

                dm = tx_date_pattern.match(line)

                if dm:
                    date_str = dm.group(1)
                    rest = dm.group(2).strip()
                    dd, mm, yy = date_str.split("/")
                    yy_full = 2000 + int(yy) if int(yy) < 50 else 1900 + int(yy)
                    current_date = safe_date(yy_full, int(mm), int(dd))

                    # Skip non-transaction lines (subtotals, saldo lines)
                    if "SALDO ANTERIOR" in rest or re.match(r"^Total\s", rest):
                        pending_desc = ""
                        i += 1
                        continue

                    # The historico is everything before the first number
                    hist_match = re.match(r"(.+?)\s+(-?\s*\d[\d.,]*)", rest)
                    if hist_match:
                        historico = hist_match.group(1).strip()
                    else:
                        historico = rest.strip()

                    # If historico is just a docto number (5-8 digits), use
                    # pending_desc from the previous continuation line
                    # (Bradesco puts "Receb Pagfor" BEFORE the date line)
                    if re.match(r"^\d{5,8}$", historico) and pending_desc:
                        historico = pending_desc
                    pending_desc = ""  # reset after use

                    # Determine if this line has a complete transaction
                    debit_match = re.search(r"-\s+([\d.,]+)\s+([\d.,]+)\s*$", rest)
                    credit_match = re.search(r"(\d[\d.,]*)\s+([\d.,]+)\s*$", rest)

                    if debit_match:
                        valor = -parse_brl(debit_match.group(1))
                        if valor is not None:
                            transactions.append(
                                {
                                    "data": current_date,
                                    "descricao": historico,
                                    "valor": valor,
                                }
                            )
                    elif credit_match:
                        nums = re.findall(r"[\d.,]+", rest)
                        if len(nums) >= 2:
                            possible_val = parse_brl(nums[-2])
                            possible_saldo = parse_brl(nums[-1])
                            if re.search(r"-\s+" + re.escape(nums[-2]), rest):
                                if possible_val is not None:
                                    transactions.append(
                                        {
                                            "data": current_date,
                                            "descricao": historico,
                                            "valor": -possible_val,
                                        }
                                    )
                            elif possible_val is not None and possible_val != possible_saldo:
                                raw = nums[-2].replace(".", "").replace(",", "")
                                if len(raw) <= 6:
                                    transactions.append(
                                        {
                                            "data": current_date,
                                            "descricao": historico,
                                            "valor": possible_val,
                                        }
                                    )

                elif current_date:
                    # Continuation line (no date prefix)
                    if (
                        line
                        and not line.startswith("Data ")
                        and not line.startswith(BANCO_BRADESCO)
                        and not re.match(r"^Total\s", line)
                    ):
                        # Pattern A: debit with saldo  "TEXT DOCTO - VALUE SALDO"
                        debit_m = re.search(r"-\s+([\d.,]+)\s+([\d.,]+)\s*$", line)
                        # Pattern B: debit WITHOUT saldo "DOCTO - VALUE" (end of line)
                        debit_no_saldo = None
                        if not debit_m:
                            debit_no_saldo = re.match(r"^(\d{5,8})\s+-\s+([\d.,]+)\s*$", line)
                        # Pattern C: credit "DOCTO VALUE [SALDO]"
                        credit_m = None
                        if not debit_m and not debit_no_saldo:
                            credit_m = re.search(r"(\d[\d.,]+)\s+([\d.,]+)\s*$", line)
                        # Pattern D: credit without saldo "DOCTO VALUE"
                        credit_no_saldo = None
                        if not debit_m and not debit_no_saldo and not credit_m:
                            credit_no_saldo = re.match(r"^(\d{5,8})\s+([\d.,]+)\s*$", line)

                        if debit_m or debit_no_saldo:
                            # Extract description from the line itself
                            hist = re.match(r"(.+?)\s+-\s+[\d.,]+", line)
                            line_desc = hist.group(1).strip() if hist else ""
                            line_desc = re.sub(r"^\d{5,8}$", "", line_desc).strip()
                            # Use line's own desc if it has text; otherwise use pending_desc
                            if line_desc and not re.match(r"^\d+$", line_desc):
                                desc = line_desc
                            elif pending_desc:
                                desc = pending_desc
                            else:
                                desc = line_desc if line_desc else line.strip()

                            if debit_m:
                                valor = -parse_brl(debit_m.group(1))
                            else:
                                valor = -parse_brl(debit_no_saldo.group(2))

                            if valor is not None and abs(valor) > 0.001:
                                transactions.append(
                                    {
                                        "data": current_date,
                                        "descricao": desc if desc else line.strip(),
                                        "valor": valor,
                                    }
                                )
                            pending_desc = ""

                        elif credit_m:
                            nums = re.findall(r"[\d.,]+", line)
                            if len(nums) >= 2:
                                possible_val = parse_brl(nums[-2])
                                possible_saldo = parse_brl(nums[-1])
                                if (
                                    possible_val is not None
                                    and possible_saldo is not None
                                    and possible_val != possible_saldo
                                ):
                                    raw = nums[-2].replace(".", "").replace(",", "")
                                    if len(raw) <= 6:
                                        # Line has text desc + value + saldo
                                        line_desc = line[: line.rfind(nums[-2])].strip()
                                        line_desc = re.sub(r"\s*\d{5,8}\s*$", "", line_desc).strip()
                                        if line_desc and not re.match(r"^\d+$", line_desc):
                                            desc = line_desc
                                        elif pending_desc:
                                            desc = pending_desc
                                        else:
                                            desc = line_desc
                                        if desc:
                                            transactions.append(
                                                {
                                                    "data": current_date,
                                                    "descricao": desc,
                                                    "valor": possible_val,
                                                }
                                            )
                                        pending_desc = ""
                                    elif raw.isdigit() and len(raw) >= 5:
                                        # First number is docto (5-8 digits), second
                                        # could be credit WITHOUT saldo (intermediate tx)
                                        credit_val = parse_brl(nums[-1])
                                        if credit_val is not None and credit_val > 0:
                                            # Extract text before first number as desc
                                            first_num = nums[0] if nums else ""
                                            idx = line.find(first_num) if first_num else -1
                                            line_text = line[:idx].strip() if idx > 0 else ""
                                            # Use line text if available, else pending
                                            if line_text and not re.match(r"^\d+$", line_text):
                                                desc = line_text
                                            elif pending_desc:
                                                desc = pending_desc
                                            else:
                                                desc = line_text if line_text else line.strip()
                                            transactions.append(
                                                {
                                                    "data": current_date,
                                                    "descricao": desc,
                                                    "valor": credit_val,
                                                }
                                            )
                                            pending_desc = ""
                                else:
                                    # Values are equal (rare) or not a value line
                                    if not re.match(r"^Des:", line) and not re.match(
                                        r"^Dest\.", line
                                    ):
                                        text_part = re.sub(r"\s+\d{5,8}$", "", line).strip()
                                        if text_part and not re.match(r"^\d+$", text_part):
                                            pending_desc = text_part
                            else:
                                # Single number or pure text — description line
                                if (
                                    not re.match(r"^Des:", line)
                                    and not re.match(r"^Dest\.", line)
                                    and not re.match(r"^\d{5,8}$", line)
                                ):
                                    pending_desc = line

                        elif credit_no_saldo:
                            # "DOCTO VALUE" — credit without saldo
                            credit_val = parse_brl(credit_no_saldo.group(2))
                            if credit_val is not None and credit_val > 0:
                                desc = pending_desc if pending_desc else ""
                                if desc:
                                    transactions.append(
                                        {
                                            "data": current_date,
                                            "descricao": desc,
                                            "valor": credit_val,
                                        }
                                    )
                                pending_desc = ""
                        else:
                            # No number patterns — pure description line
                            # (e.g., "Ted Dif.titul", "Transfe Pix", "Receb Pagfor")
                            if re.match(r"^Des:", line) or re.match(r"^Dest\.", line):
                                # Detail line (PIX/TED recipient) — append to
                                # last transaction for richer description
                                if transactions:
                                    last = transactions[-1]
                                    if last["data"] == current_date:
                                        last["descricao"] += " " + line
                            elif re.match(r"^[A-Z][a-z].*\.$", line):
                                # Company name like "Grpqa Ltda.", "Bradesco C-pmsp sp"
                                # Append to last transaction description so keywords
                                # like "GRPQA" are present for categorization.
                                if transactions:
                                    last = transactions[-1]
                                    if last["data"] == current_date:
                                        last["descricao"] += " " + line
                            else:
                                pending_desc = line

                i += 1

            result["transacoes"] = transactions

            # Try to find saldo final from "Total" line or last saldo
            total_match = re.search(r"Total\s+([\d.,]+)\s+-\s+([\d.,]+)\s+([\d.,]+)", all_text)
            if total_match:
                result["saldo_final"] = parse_brl(total_match.group(3))

    except Exception as e:
        log(LOG_PREFIX, "ERROR", f"  Falha ao processar {filename}: {e}")
        result["notas"].append(f"Erro no parsing: {e}")
        result["requires_llm_fallback"] = True

    log(LOG_PREFIX, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    return result
