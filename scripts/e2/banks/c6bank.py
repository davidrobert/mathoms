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
    C6_CSV_LAYOUT,  # consumido pelo parser CSV; PDF migrou para text-based regex
    CARTAO_CARBON,
    FAMILY,
    MESES_BR_INT,
    MESES_BR_STR,
    TITULAR,
    VENC_CARBON,
    detect_member_from_card_name,
    detect_member_from_text,
    extract_account_number,
    infer_fatura_ref_from_filename,
    infer_periodo_from_filename,
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
    # c6bank enumera porque tem roteamento format-specific (PJ-CSV → parser de CSV
    # vs. PDF → parser de PDF). Os patterns format-specific vêm primeiro; o último
    # é um fallback subtipo-agnóstico (sem terminador) que cobre subtipos de moeda
    # em PDF (extratocontausd/brl/eur/...) sem reabrir o furo do anchor `_` final.
    (r"^c6bank_extratocontapj_.*\.csv$", "parse_c6bank_csv"),
    (r"^c6bank_extratoconta_.*\.csv$", "parse_c6bank_csv"),
    (r"^c6bank_extratocontaglobalusd_", "parse_c6bank"),
    (r"^c6bank_extratocontaglobaleur_", "parse_c6bank"),
    (r"^c6bank_extratocontapj_", "parse_c6bank"),
    (r"^c6bank_extratoconta", "parse_c6bank"),
    (r"c6bank_faturacarbon.*\.csv$", "parse_c6_carbon_csv"),
    (r"c6bank_faturacarbon", "parse_c6_carbon"),
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
    result["tipo_conta"] = "pj" if is_pj else "corrente"

    raw_text = csv_path.read_text(encoding="utf-8-sig")
    lines = raw_text.splitlines()

    # --- Parse header metadata ---
    for line in lines[:6]:
        ag_m = re.search(r"Ag[êe]ncia:\s*(\d+)", line)
        if ag_m:
            result["agencia"] = ag_m.group(1)
        conta_m = re.search(r"Conta:\s*(\d+)", line)
        if conta_m:
            result["numero_conta"] = conta_m.group(1)

    for line in lines[:10]:
        periodo_m = re.search(r"Extrato de\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})", line)
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
        if line.strip().startswith("Data Lançamento,") or line.strip().startswith(
            "Data Lancamento,"
        ):
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

        if not re.match(r"\d{2}/\d{2}/\d{4}$", data_lanc_str):
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

        tx = {
            "data": data_iso,
            "descricao": desc_full,
            "valor": valor,
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
    if n_tx == 0:
        # CSV estruturalmente válido mas sem linhas de dado — conta possivelmente inativa no período.
        msg = "WARN: Nenhuma transação encontrada no CSV — verifique se o extrato exportado está completo"
        result["notas"].append(msg)
        log(LOG_PREFIX_EXTRATO, "WARN", f"  {msg}")
    if result["saldo_inicial"] is not None:
        log(LOG_PREFIX_EXTRATO, "INFO", f"  Saldo inicial: {result['saldo_inicial']:.2f}")
    if result["saldo_final"] is not None:
        log(LOG_PREFIX_EXTRATO, "INFO", f"  Saldo final: {result['saldo_final']:.2f}")

    return result


# =============================================================================
# Parser: C6 Bank extrato conta/PJ/global PDF
# =============================================================================


def _sniff_c6_currency(pdf_path: Path) -> Optional[str]:
    """Sniff moeda from first-page text. Returns 'USD', 'EUR' ou None se BRL/indefinido.

    Alguns uploads vêm com filename genérico `c6bank_extratoconta_...` embora
    o PDF seja extrato Global em USD/EUR. Detectamos pelo símbolo monetário.
    """
    if pdfplumber is None:
        return None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            head = pdf.pages[0].extract_text() or ""
    except Exception:
        return None
    has_brl = "R$" in head
    if "US$" in head and not has_brl:
        return "USD"
    if ("€" in head or re.search(r"\bEUR\b", head)) and not has_brl:
        return "EUR"
    return None


# Tipos de lançamento conhecidos no extrato C6 (conta/PJ/global). Ordenados
# por especificidade — substrings mais longas vêm primeiro pra "Saída PIX"
# vencer "Saída" no startswith match.
_C6_KNOWN_TIPOS: Tuple[str, ...] = (
    "Saída PIX",
    "Entrada PIX",
    "Devolução PIX",
    "Saída TED",
    "Entrada TED",
    "Transferência",
    "Outros gastos",
    "Pagamento",
    "Entradas",
    "Compra",
    "Estorno",
    "Resgate",
    "Aplicação",
    "Aplicacao",
    "Tarifa",
    "Débito",
    "Crédito",
    "IOF",
)

# Currency token lookahead — captura BRL ou Global (USD/EUR) no fim da linha.
_C6_CURRENCY = r"(?:R\$|US\$|€|EUR)"

# Linha de transação: "DD/MM DD/MM <tipo> <descrição opcional> [-]R$ XX.XX,XX".
# Ancorada em (data1)(data2)(rest)(valor) — `rest` é greedy mínimo até o
# sinal+moeda no fim, evitando consumir o número como parte da descrição.
_C6_TXN_RE = re.compile(
    rf"^(?P<d1>\d{{2}}/\d{{2}})\s+(?P<d2>\d{{2}}/\d{{2}})\s+"
    rf"(?P<rest>.+?)\s+(?P<sign>-?){_C6_CURRENCY}\s*(?P<valor>[\d.,]+)\s*$"
)

# Linha de saldo: "Saldo do dia DD/MM/YY R$ X.XXX,XX".
_C6_SALDO_RE = re.compile(
    rf"^Saldo do dia\s+(?P<date>\d{{2}}/\d{{2}}/\d{{2,4}})\s+"
    rf"{_C6_CURRENCY}\s*(?P<valor>[\d.,]+)\s*$"
)

# Prefixos de linhas de cabeçalho/rodapé/metadata que NÃO são continuação de
# descrição de transação. Quando o parser encontra uma linha que não casa
# transação nem saldo, mas começa com um destes, ignora (não concatena).
# Usado pela salvaguarda de wrap multi-linha em `_parse_c6_extrato_text`.
_C6_NOISE_PREFIXES: Tuple[str, ...] = (
    "Banco C6",
    "CNPJ:",
    "Período",
    "Periodo",
    "Pagina",
    "Página",
    "Conta:",
    "Agência",
    "Agencia",
    "Extrato",
    "Titular:",
    "CPF:",
    "Status",
    "Cotação",
    "Cotacao",
    "Data Tipo",
    # Cabeçalho de tabela "Data Data Tipo Descrição Valor lançamento contábil"
    # — header repete no topo de cada página do extrato C6 conta-corrente.
    # Sem isso, _ingest_c6_line linha 450-451 trata como continuação de
    # descrição da tx anterior, inflando descricao e quebrando dedup K4
    # (mesma tx em 2 extratos vira hashes distintos). Observado em prod
    # 2026-05-24, workspace 1b9f2cf5 (5 PIXes Arvo duplicados).
    "Data Data",
    # Variante com o mesmo cabeçalho quebrado em 2 linhas pela extração de
    # texto ("Data Data" + "Tipo Descrição Valor lançamento contábil") — a
    # segunda linha escapava do filtro e era concatenada na descrição da tx
    # anterior. Observado em prod 2026-06-12 (PIX Arvo Saúde, mesmo workspace
    # do incidente de 2026-05-24 acima).
    "Tipo Descrição",
    "Tipo Descricao",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Marco",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
    "Sem lançamentos",
    "Sem lancamentos",
)


def _split_c6_tipo_desc(rest: str) -> Tuple[str, str]:
    """Separa `<tipo> <descrição>` testando prefixos conhecidos em `_C6_KNOWN_TIPOS`."""
    rest = rest.strip()
    for tipo in _C6_KNOWN_TIPOS:
        if rest == tipo or rest.startswith(tipo + " "):
            return tipo, rest[len(tipo) :].strip()
    parts = rest.split(None, 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _parse_c6_signed_value(sign: str, valor_str: str) -> Optional[float]:
    """Converte `<sign><moeda> <valor>` em float assinado. `sign` é '-' ou ''."""
    raw = parse_brl(valor_str)
    if raw is None:
        return None
    raw = abs(raw)
    return -raw if sign == "-" else raw


def _build_tx_from_match(
    tx_match: "re.Match[str]",
    periodo_inicio: str,
    periodo_fim: str,
) -> Optional[Dict[str, Any]]:
    """Constrói dict de transação a partir de match do `_C6_TXN_RE`."""
    valor = _parse_c6_signed_value(tx_match.group("sign"), tx_match.group("valor"))
    if valor is None:
        return None
    d1 = tx_match.group("d1")
    dd_i, mm_i = (int(x) for x in d1.split("/"))
    year = resolve_year_from_period(dd_i, mm_i, periodo_inicio, periodo_fim)
    _, desc = _split_c6_tipo_desc(tx_match.group("rest"))
    return {
        "data": safe_date(year, mm_i, dd_i),
        "descricao": desc,
        "valor": valor,
    }


def _is_c6_noise_line(line: str) -> bool:
    """Detecta cabeçalho/rodapé/metadata; NÃO é continuação de descrição."""
    return any(line.startswith(prefix) for prefix in _C6_NOISE_PREFIXES)


def _ingest_c6_line(
    line: str,
    transacoes: List[Dict[str, Any]],
    saldos: List[Tuple[str, float]],
    periodo_inicio: str,
    periodo_fim: str,
) -> None:
    """Despacha 1 linha: saldo, tx, wrap-de-descrição ou ruído ignorado."""
    if (sm := _C6_SALDO_RE.match(line)) is not None:
        if (sv := parse_brl(sm.group("valor"))) is not None:
            saldos.append((sm.group("date"), sv))
    elif (tm := _C6_TXN_RE.match(line)) is not None:
        if (tx := _build_tx_from_match(tm, periodo_inicio, periodo_fim)) is not None:
            transacoes.append(tx)
    elif transacoes and not _is_c6_noise_line(line):
        transacoes[-1]["descricao"] = (transacoes[-1]["descricao"] + " " + line).strip()


def _parse_c6_extrato_text(
    full_text: str,
    periodo_inicio: str,
    periodo_fim: str,
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, float]]]:
    """Parser line-based para extrato C6 — substitui `extract_tables()` bugado."""
    transacoes: List[Dict[str, Any]] = []
    saldos: List[Tuple[str, float]] = []
    for raw in full_text.split("\n"):
        if line := raw.strip():
            _ingest_c6_line(line, transacoes, saldos, periodo_inicio, periodo_fim)
    return transacoes, saldos


def parse_c6bank(pdf_path: Path, filename: str) -> Dict[str, Any]:
    """Parse C6 Bank statement (conta, contapj, contaglobal)."""
    is_global_usd = "extratocontaglobalusd" in filename
    is_global_eur = "extratocontaglobaleur" in filename
    is_pj = "extratocontapj" in filename

    if not (is_global_usd or is_global_eur or is_pj):
        sniffed = _sniff_c6_currency(pdf_path)
        if sniffed == "USD":
            is_global_usd = True
        elif sniffed == "EUR":
            is_global_eur = True

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
    result["tipo_conta"] = "pj" if is_pj else "corrente"

    periodo_inicio, periodo_fim = infer_periodo_from_filename(filename)
    result["periodo"]["inicio"] = periodo_inicio
    result["periodo"]["fim"] = periodo_fim

    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_text = pdf.pages[0].extract_text() or ""
            result["titular"] = detect_member_from_text(first_text)
            result["numero_conta"] = extract_account_number(first_text, "c6bank")
            ag_m = re.search(r"Ag[êe]ncia[:\s•]+(\d+)", first_text)
            if ag_m:
                result["agencia"] = ag_m.group(1)

            periodo_pat = re.compile(
                r"Período\s*•?\s*(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+"
                r"até\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})",
                re.IGNORECASE,
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

            saldo_header = re.search(r"Saldo do dia.*?[•\s]+(R\$|US\$|EUR)\s*([\d.,]+)", first_text)

            full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
            if "Sem lançamentos no mês" in full_text or "sem lançamentos" in full_text.lower():
                empty_months = full_text.lower().count("sem lançamentos")
                result["notas"].append(
                    f"Sem lançamentos no período ({empty_months} mês(es) sem movimentação)"
                )

            if is_global_usd or is_global_eur:
                saldo_text_match = re.search(
                    r"Saldo do dia.*?(?:US\$|€|EUR\s*)\s*([\d.,]+)",
                    full_text,
                )
                if saldo_text_match:
                    raw = saldo_text_match.group(1).replace(".", "").replace(",", ".")
                    try:
                        result["saldo_final"] = float(raw)
                    except ValueError:
                        pass

            # Parser line-based sobre `extract_text()` — substitui o uso anterior
            # de `extract_tables()`, que perdia o valor de transações sempre que
            # duas linhas adjacentes do PDF compartilhavam a mesma `data1` em
            # col0 (pdfplumber colapsava a célula da segunda row em None).
            # Sintoma em produção: ~20% das txs do PDF perdiam o valor e a
            # descrição da row seguinte era concatenada à anterior, gerando
            # categorização errada (ex.: R$ 194.886,65 de Pagamento Itaú
            # virava "Serviços Domésticos" porque a descrição do PIX para
            # Eliane Costa Goncalves era colada na linha do Itaú).
            txs_from_text, saldo_values = _parse_c6_extrato_text(
                full_text,
                periodo_inicio=result["periodo"]["inicio"] or "",
                periodo_fim=result["periodo"]["fim"] or "",
            )
            result["transacoes"].extend(txs_from_text)

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

    # Token ancorado ao fim do stem (documents.period via routing) — busca livre
    # de 6 dígitos casava o prefixo sha256[:12] e gerava 2100/1899 (A32.l3).
    ref_year, ref_month = infer_fatura_ref_from_filename(filename)
    if ref_year and ref_month:
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

        if not re.match(r"\d{2}/\d{2}/\d{4}$", data_str):
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

        result["transacoes"].append(tx)

    result["total_compras_nacionais"] = round(total_nacionais, 2) if total_nacionais else None
    result["total_compras_internacionais"] = (
        round(total_internacionais, 2) if total_internacionais else None
    )
    result["pagamentos"] = round(total_pagamentos, 2) if total_pagamentos else None

    if result["transacoes"]:
        result["saldo_atual"] = round(sum(t["valor"] for t in result["transacoes"]), 2)

    for card_name, subtotal in cards_seen.items():
        result["cartoes"].append(
            {
                "cartao": card_name,
                "subtotal": round(subtotal, 2),
            }
        )

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

    # Token ancorado ao fim do stem (documents.period via routing) — busca livre
    # de 6 dígitos casava o prefixo sha256[:12] e gerava 2100/1899 (A32.l3).
    ref_year, ref_month = infer_fatura_ref_from_filename(filename)

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
                result["titular"] = TITULAR.get(
                    "variantes_nome", [TITULAR.get("nome_completo", "")]
                )[0]

            m = re.search(r"[Vv]encimento[:\s]+(\d{1,2})\s+de\s+(\w+)", full_text)
            if m and ref_year:
                day = int(m.group(1))
                month_name = m.group(2).lower()
                month_num = MESES_BR_STR.get(month_name)
                if month_num:
                    result["data_vencimento"] = f"{ref_year}-{month_num}-{day:02d}"

            m = re.search(r"Valor da fatura:\s*R\$\s*([\d.,]+)", full_text)
            if m:
                result["saldo_atual"] = parse_brl(m.group(1))

            m = re.search(r"Limite total:\s*R\$\s*([\d.,]+)", full_text)
            if m:
                result["limite_total"] = parse_brl(m.group(1))

            m = re.search(r"Compras nacionais\s+([\d.,]+)", full_text)
            if m:
                result["total_compras_nacionais"] = parse_brl(m.group(1))
            m = re.search(r"Compras internacionais\s+([\d.,]+)", full_text)
            if m:
                result["total_compras_internacionais"] = parse_brl(m.group(1))

            m = re.search(r"Estornos\s*/\s*Crédito na Fatura\s+\(?\-?\)?\s*([\d.,]+)", full_text)
            if m:
                result["pagamentos"] = -parse_brl(m.group(1))

            # --- Extract transactions ---
            current_card_name = None
            current_card_subtotal = None

            tx_pattern = re.compile(
                r"^(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s+"
                r"(.+?)\s+"
                r"([\d.,]+)\s*$",
                re.MULTILINE,
            )

            card_pattern = re.compile(
                r"C6 Carbon\s+(?:Virtual\s+)?Final\s+(\d{4})\s*-\s*(.+?)(?:\s+Cartão|\s+Subtotal)",
                re.IGNORECASE,
            )

            subtotal_pattern = re.compile(r"Subtotal deste cartão\s+R\$\s*([\d.,]+)", re.IGNORECASE)

            cards_seen = {}

            for page in all_text:
                lines = page.split("\n")

                for line in lines:
                    card_m = card_pattern.search(line)
                    if card_m:
                        current_card_name = (
                            f"C6 Carbon Final {card_m.group(1)} - {card_m.group(2).strip()}"
                        )

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
                            r"(USD|EUR)\s+([\d.,]+)\s*\|\s*Cotação\s+\w+:\s*R\$\s*([\d.,]+)",
                            raw_desc,
                        )
                        if forex_m:
                            forex_info = {
                                "moeda_original": forex_m.group(1),
                                "valor_original": parse_brl(forex_m.group(2)),
                                "cotacao": parse_brl(forex_m.group(3)),
                            }
                            descricao = raw_desc[: forex_m.start()].strip()

                        iof_m = re.search(r"IOF Transações Exterior", raw_desc)
                        if iof_m:
                            descricao = raw_desc[: iof_m.start()].strip()
                            if not descricao:
                                descricao = "IOF Transações Exterior"

                        parcela_m = re.search(r"-\s*Parcela\s+(\d+/\d+)", raw_desc)
                        if parcela_m:
                            parcela = parcela_m.group(1)
                            descricao = raw_desc[: parcela_m.start()].strip()

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

                        result["transacoes"].append(tx)

            for card_name, subtotal in cards_seen.items():
                result["cartoes"].append(
                    {
                        "cartao": card_name,
                        "subtotal": subtotal,
                    }
                )

        log(LOG_PREFIX_FATURA, "INFO", f"  → {len(result['transacoes'])} transações extraídas")
    except Exception as e:
        log(LOG_PREFIX_FATURA, "ERROR", f"  Falha ao abrir PDF {pdf_path.name}: {e}")
        return {"erro": str(e), "requires_llm_fallback": True, "tipo": "fatura"}

    return result
