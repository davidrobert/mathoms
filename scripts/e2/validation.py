#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2 Validation — post-parse quality checks for extraction results.

Consolidates validate_result() from e2_extract_extratos.py and
validate_parse_result() from e2_extract_faturas.py.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from pipeline.domain.review_reason import ReviewReasonCode
from scripts.e2.common import MIN_CSV_BYTES, MIN_XLS_BYTES

# ADR-342: o gate HARD de conservação é opt-in POR PARSER — o parser declara
# `conservacao_verificavel=True` no result quando a semântica de saldo é
# observada e verificada (hoje: Itaú layout 2026). Refinamento do "allowlist
# por banco" da ADR: o layout antigo do Itaú tem saldo_inicial com semântica
# de fechamento do 1º dia (conservação global nunca fechou lá) e Wise/Rico
# derivam saldo_inicial de saldo_final−Σtx (check tautológico) — todos ficam
# em WARN (telemetria) até o parser correspondente verificar a semântica.


def conservation_gap_cents(result: Dict[str, Any]) -> Optional[int]:
    """Gap da conservação global em cents; None quando não verificável."""
    saldo_ini = result.get("saldo_inicial")
    saldo_fim = result.get("saldo_final")
    txs = result.get("transacoes") or []
    if saldo_ini is None or saldo_fim is None or not txs:
        return None
    soma = sum(t.get("valor") or 0 for t in txs)
    return round(abs((saldo_ini + soma) - saldo_fim) * 100)


def escalate_result(result: Dict[str, Any], code: ReviewReasonCode, message: str) -> None:
    """Escalação anti-silêncio (ADR-342): flippa o contrato existente
    `requires_llm_fallback` (E2-llm one-shot; depois `needs_review`) e registra
    razão estruturada top-level — sem mudança no schema `e2_extract`."""
    result["requires_llm_fallback"] = True
    result["escalation_reason"] = {"code": code.value, "message": message}


def _warn_reason(result: Dict[str, Any], code: ReviewReasonCode, message: str) -> None:
    result.setdefault("warn_reasons", []).append({"code": code.value, "message": message})


def _is_dormant_by_observation(result: Dict[str, Any]) -> bool:
    """Dormância (0 tx que NÃO escala) só quando o parser observou **0 linhas
    candidatas** (`raw_rows_detected == 0`). Parser que não reporta (`None`) ⇒
    fail-safe: não é dormante ⇒ escala. `raw_rows_detected > 0` ⇒ viu linhas e
    converteu zero (falha silenciosa) ⇒ escala. Substitui o substring-match em
    `notas`, que uma nota parcial de mês vazio derrotava (ADR-342 §Emenda
    A38.l14 — dormência é observação do parser, não conclusão em texto livre)."""
    return result.get("raw_rows_detected") == 0


# `total_declarado` deve ter ESCOPO IGUAL ao das linhas (bruto vs bruto); total de
# conta agregado (saldos não itemizados) não entra aqui. Soma em int cents por
# posição (ADR-090) — float acumulado dispara falso-fire com muitas posições.
_CDB_EMPTY_MSG = "0 posições de CDB extraídas — escalado (ADR-342)"
_CDB_MISMATCH_MSG = "Σ posições ≠ total declarado (cents) — escalado (ADR-342 §Emenda l12)"


def apply_cdb_checksum(result: Dict[str, Any], total_declarado: Optional[float] = None) -> None:
    """Escala (ADR-342 §Emenda l12) se 0 posições, ou Σ posições ≠ total declarado."""
    posicoes = result.get("posicoes") or []
    if not posicoes:
        escalate_result(result, ReviewReasonCode.extract_empty_result, _CDB_EMPTY_MSG)
        return
    if total_declarado is None:
        return
    soma_cents = sum(round((p.get("valor_atual") or 0) * 100) for p in posicoes)
    if soma_cents != round(total_declarado * 100):
        escalate_result(result, ReviewReasonCode.extract_investment_sum_mismatch, _CDB_MISMATCH_MSG)


def validate_extrato_result(
    result: Dict[str, Any], file_path: Path, is_csv: bool = False
) -> List[str]:
    """Validate extraction result for extratos. Returns list of warnings/errors."""
    issues = []

    # A38.l12: artefato de POSIÇÃO (CDB/investimento) não tem transações por
    # design — a completude dele é o checksum Σ posições == total, feito no
    # próprio parser. O gate de completude de transação (0 tx ⇒ escala) não se
    # aplica; sem esta guarda, todo CDB (0 `transacoes`) escalaria em falso.
    if result.get("tipo") == "cdbresumo" or result.get("posicoes"):
        return issues

    n_tx = len(result.get("transacoes", []))
    periodo = result.get("periodo", {})

    if not periodo.get("inicio"):
        issues.append("WARN: periodo.inicio ausente")
    if not periodo.get("fim"):
        issues.append("WARN: periodo.fim ausente")

    if is_csv:
        try:
            total_chars = file_path.stat().st_size
        except Exception:
            total_chars = 0

        is_xls = str(file_path).endswith(".xls")
        size_threshold = MIN_XLS_BYTES if is_xls else MIN_CSV_BYTES

        if n_tx == 0 and total_chars > size_threshold and not _is_dormant_by_observation(result):
            issues.append(
                f"ERROR: 0 transações extraídas de {'XLS' if is_xls else 'CSV'} com {total_chars} bytes "
                f"— provável falha de parsing"
            )
            escalate_result(
                result,
                ReviewReasonCode.extract_empty_result,
                "0 transações com conteúdo substancial — escalado (ADR-342)",
            )
    else:
        if pdfplumber is None:
            total_chars = 0
            n_pages = 0
        else:
            try:
                with pdfplumber.open(file_path) as pdf:
                    total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)
                    n_pages = len(pdf.pages)
            except Exception:
                total_chars = 0
                n_pages = 0

        if (
            n_tx == 0
            and total_chars > 500
            and n_pages > 0
            and not _is_dormant_by_observation(result)
        ):
            issues.append(
                f"ERROR: 0 transações extraídas de PDF com {total_chars} chars / "
                f"{n_pages} páginas — provável falha de parsing"
            )
            escalate_result(
                result,
                ReviewReasonCode.extract_empty_result,
                "0 transações com conteúdo substancial — escalado (ADR-342)",
            )

    none_vals = sum(1 for t in result.get("transacoes", []) if t.get("valor") is None)
    if none_vals > 0:
        issues.append(f"WARN: {none_vals} transações com valor None")

    seen = set()
    dupes = 0
    for t in result.get("transacoes", []):
        key = (t.get("data"), t.get("valor"), t.get("descricao", "")[:30])
        if key in seen:
            dupes += 1
        seen.add(key)
    if dupes > 0:
        issues.append(f"INFO: {dupes} possíveis duplicatas intra-arquivo")

    _apply_conservation_gate(result, issues)

    return issues


def _apply_conservation_gate(result: Dict[str, Any], issues: List[str]) -> None:
    """Conservação global em cents, tolerância zero (ADR-342). HARD (escala)
    só quando o parser declarou `conservacao_verificavel`; demais em WARN
    (telemetria). Sem mensagem com valores — só o fato e o código."""
    gap = conservation_gap_cents(result)
    if gap is None or gap == 0:
        return
    code = ReviewReasonCode.extract_incomplete_conservation
    if result.get("conservacao_verificavel"):
        issues.append("ERROR: conservação global não fecha (saldo_inicial + Σtx ≠ saldo_final)")
        escalate_result(result, code, "conservação global não fecha em cents — escalado (ADR-342)")
        return
    issues.append("WARN: conservação global não fecha (parser sem semântica verificada)")
    _warn_reason(result, code, "conservação não fecha (WARN — gate HARD é opt-in do parser)")


def validate_fatura_result(result: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Validate fatura parse result: sets parse_quality and appends issues to notas."""
    issues = result.setdefault("notas", []) if isinstance(result.get("notas"), list) else []
    if not isinstance(result.get("notas"), list):
        result["notas"] = issues = []

    saldo = result.get("saldo_atual") or 0
    txns = len(result.get("transacoes", []))
    itens = len(result.get("itens", []))
    venc = result.get("data_vencimento", "")

    if saldo == 0 and txns == 0 and itens == 0 and not venc:
        result["parse_quality"] = "empty_result"
        issues.append(
            f"ERROR: fatura vazia — saldo=0, transacoes=0, sem data_vencimento ({filename})"
        )
        escalate_result(
            result,
            ReviewReasonCode.extract_empty_result,
            "fatura vazia — escalado (ADR-342, contrato único extrato+fatura)",
        )
    elif saldo > 0 and txns == 0 and itens == 0:
        result["parse_quality"] = "missing_transactions"
        issues.append(
            f"ERROR: fatura com saldo {saldo} mas 0 transações/itens — provável falha de parsing ({filename})"
        )
        escalate_result(
            result,
            ReviewReasonCode.extract_empty_result,
            "fatura com saldo e 0 lançamentos — escalado (ADR-342)",
        )
    else:
        result["parse_quality"] = "ok"

    if not venc and txns > 0:
        issues.append(f"WARN: data_vencimento ausente na fatura ({filename})")

    none_vals = sum(1 for t in result.get("transacoes", []) if t.get("valor") is None)
    if none_vals > 0:
        issues.append(f"WARN: {none_vals} transações com valor None ({filename})")

    return result
