#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Itaú — extrato conta corrente layout 2026, parse por linhas de texto:
`extract_tables()` fragmenta este layout (células multi-linha) e perdia ~50%
das transações (A38.l2; mesmo modo de falha do C6 em `_parse_c6_extrato_text`)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from scripts.e2.common import parse_brl

_LINE_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d.]+,\d{2})$")
_PERIODO_RE = re.compile(
    r"per[ií]odo de visualiza[çc][ãa]o:\s*(\d{2}/\d{2}/\d{4})\s*at[ée]\s*(\d{2}/\d{2}/\d{4})",
    re.I,
)
_AGENCIA_CONTA_RE = re.compile(r"ag[êe]ncia:\s*(\d+)\s+conta:\s*([\d.-]+)", re.I)
_LAYOUT_MARKERS = ("extrato conta / lancamentos", "data lancamentos valor (r$) saldo (r$)")
_SALDO_PREFIXES = ("SALDO DO DIA", "SALDO ANTERIOR")


def _fold(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in norm if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped.lower())


def is_itau_layout_2026(first_page_text: str) -> bool:
    """Detecta o layout 2026 pelo cabeçalho normalizado (case/acento/whitespace)."""
    probe = _fold(first_page_text)
    return any(marker in probe for marker in _LAYOUT_MARKERS)


def _iso(br_date: str) -> str:
    day, month, year = br_date.split("/")
    return f"{year}-{month}-{day}"


def _parse_line(raw: str) -> Optional[Tuple[str, str, float]]:
    match = _LINE_RE.match(raw.strip())
    if not match:
        return None
    valor = parse_brl(match.group(3))
    if valor is None:
        return None
    return _iso(match.group(1)), match.group(2).strip(), valor


def parse_extrato_2026_text(text: str) -> Tuple[List[Dict], List[Tuple[str, float]]]:
    """Retorna (transações ascendentes, âncoras de saldo ascendentes) das linhas
    `dd/mm/yyyy DESCRIÇÃO [-]1.234,56` — exatamente 1 valor por linha;
    `SALDO DO DIA`/`SALDO ANTERIOR` são âncoras, nunca transação."""
    txs: List[Dict] = []
    saldos: List[Tuple[str, float]] = []
    for raw in text.splitlines():
        parsed = _parse_line(raw)
        if parsed is None:
            continue
        data, descricao, valor = parsed
        if descricao.upper().startswith(_SALDO_PREFIXES):
            saldos.append((data, valor))
        else:
            txs.append({"data": data, "descricao": descricao, "valor": valor})
    txs.sort(key=lambda t: t["data"])
    saldos.sort()
    return txs, saldos


def summarize_saldos(
    txs: List[Dict], saldos: List[Tuple[str, float]]
) -> Tuple[Optional[float], Optional[float]]:
    """`saldo_inicial` = âncora do 1º dia − Σtx desse dia (a âncora é
    fechamento); `saldo_final` = última âncora; assim
    `saldo_inicial + Σtx == saldo_final` fecha."""
    if not saldos:
        return None, None
    first_date, first_saldo = saldos[0]
    first_day_sum = sum(t["valor"] for t in txs if t["data"] == first_date and t["valor"])
    return round(first_saldo - first_day_sum, 2), saldos[-1][1]


def fill_result_layout_2026(pdf: Any, first_page_text: str, result: Dict) -> Dict:
    """Preenche o result template E2 a partir do texto de todas as páginas."""
    all_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    _fill_periodo(all_text, result)
    _fill_agencia_conta(first_page_text, result)
    txs, saldos = parse_extrato_2026_text(all_text)
    saldos = _drop_anchors_beyond_periodo(saldos, result["periodo"].get("fim"))
    saldos = _drop_trailing_informational_anchor(saldos, txs)
    result["transacoes"] = txs
    saldo_inicial, saldo_final = summarize_saldos(txs, saldos)
    if saldo_inicial is not None:
        result["saldo_inicial"] = saldo_inicial
        result["saldo_final"] = saldo_final
        # ADR-342: opt-in do gate HARD de conservação. Este layout tem saldo
        # observado (âncoras `SALDO DO DIA`) e semântica verificada — se a
        # conservação global não fechar, é row-drop real, escala (não é o
        # falso-positivo tautológico dos parsers de saldo derivado).
        result["conservacao_verificavel"] = True
    return result


def _drop_anchors_beyond_periodo(
    saldos: List[Tuple[str, float]], periodo_fim: Optional[str] = None
) -> List[Tuple[str, float]]:
    """A âncora `SALDO DO DIA` da data de EMISSÃO (saldo atual) cai quando é
    posterior ao fim do período de visualização: os movimentos dessa janela
    não estão listados e usá-la como `saldo_final` quebraria a conservação
    por design — fora do período ⇒ fora do razão."""
    if not periodo_fim:
        return saldos
    return [(data, valor) for data, valor in saldos if data <= periodo_fim]


def _drop_trailing_informational_anchor(
    saldos: List[Tuple[str, float]], txs: List[Dict]
) -> List[Tuple[str, float]]:
    """Âncora datada após a última transação é o "saldo atual" na emissão —
    o export não lista os movimentos entre o último dia liquidado e a emissão;
    o razão honesto termina no último dia com movimento, e continuidade além
    disso é papel do validator cross-statement do E3."""
    if not txs or not saldos:
        return saldos
    last_tx_date = max(t["data"] for t in txs)
    kept = [(data, valor) for data, valor in saldos if data <= last_tx_date]
    return kept or saldos


def _fill_periodo(all_text: str, result: Dict) -> None:
    match = _PERIODO_RE.search(all_text)
    if match:
        result["periodo"]["inicio"] = _iso(match.group(1))
        result["periodo"]["fim"] = _iso(match.group(2))


def _fill_agencia_conta(first_page_text: str, result: Dict) -> None:
    match = _AGENCIA_CONTA_RE.search(first_page_text)
    if match:
        result["agencia"] = match.group(1)
        result["numero_conta"] = match.group(2)
