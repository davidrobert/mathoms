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


def _apply_fatura_checksum(result: Dict[str, Any], issues: List[str]) -> None:
    """WARN (não escala) por balde cujo Σ lançamentos ≠ subtotal declarado. Opt-in
    por parser via `total_lancamentos_conferivel` — objeto único OU lista (uma
    entrada por seção; A39.l3-c3 verifica exterior além de despesa_brasil). Flip
    HARD por parser após corpus limpo (ADR-342). NUNCA compara com `saldo_atual`."""
    signal = result.get("total_lancamentos_conferivel")
    if signal is None:
        return
    signals = signal if isinstance(signal, list) else [signal]
    txs = result.get("transacoes") or []
    for sig in signals:
        if not isinstance(sig, dict) or sig.get("valor_cents") is None:
            continue
        escopo = sig.get("escopo")
        soma_cents = sum(
            round((t.get("valor") or 0) * 100) for t in txs if t.get("escopo") == escopo
        )
        if soma_cents != sig["valor_cents"]:
            _fatura_mismatch_warn(result, issues, escopo)


def _fatura_mismatch_warn(result: Dict[str, Any], issues: List[str], escopo) -> None:
    msg = f"Σ lançamentos ≠ total declarado no escopo '{escopo}' (checksum de fatura)"
    issues.append(f"WARN: {msg}")
    _warn_reason(result, ReviewReasonCode.extract_fatura_total_mismatch, msg)


def apply_cdb_checksum(result: Dict[str, Any], total_declarado: Optional[float] = None) -> None:
    """Escala (ADR-342 §Emenda l12) se 0 posições, ou Σ posições ≠ total declarado."""
    posicoes = result.get("posicoes") or []
    if not posicoes:
        escalate_result(result, ReviewReasonCode.extract_empty_result, _CDB_EMPTY_MSG)
        return
    if total_declarado is None:
        # A39.l6: total agregado ausente (ex.: Itaú CDB PDF de posição única) →
        # checksum pulado com traço, não no-op silencioso. A certificação passa a
        # distinguir "passou" de "pulou por falta de total".
        result["checksum_skipped_no_total"] = True
        return
    soma_cents = sum(round((p.get("valor_atual") or 0) * 100) for p in posicoes)
    if soma_cents != round(total_declarado * 100):
        escalate_result(result, ReviewReasonCode.extract_investment_sum_mismatch, _CDB_MISMATCH_MSG)
        return
    result["checksum_ok"] = True  # A39.l6: traço positivo do pass


_RV_EMPTY_MSG = "0 posições de renda variável extraídas — escalado (ADR-346 · A39.l9)"
_RV_COUNT_MSG = "n_papéis detectado ≠ posições emitidas — escalado (ADR-346 checksum de contagem)"
_RV_CLASS_MSG = "Σ posições da classe ≠ subtotal declarado (cents) — escalado (ADR-346)"


def apply_rv_count_checksum(result: Dict[str, Any], raw_detected: Optional[int] = None) -> None:
    """Posição só-quantidade (custódia acionária): sem valor a somar; a completude
    é n_papéis observado == posições emitidas. Falha → escala (ADR-346)."""
    posicoes = result.get("posicoes") or []
    if not posicoes:
        escalate_result(result, ReviewReasonCode.extract_empty_result, _RV_EMPTY_MSG)
        return
    if raw_detected is not None and raw_detected != len(posicoes):
        escalate_result(result, ReviewReasonCode.extract_investment_sum_mismatch, _RV_COUNT_MSG)
        return
    result["checksum_ok"] = True


def apply_rv_carteira_checksum(
    result: Dict[str, Any], subtotais_por_classe: Dict[str, float]
) -> None:
    """Carteira valorada (Rico/XP): Σ posições por classe == subtotal declarado da
    classe (int cents, ADR-090). Falha → escala; sem subtotal → skip com traço."""
    posicoes = result.get("posicoes") or []
    if not posicoes:
        escalate_result(result, ReviewReasonCode.extract_empty_result, _RV_EMPTY_MSG)
        return
    if not subtotais_por_classe:
        result["checksum_skipped_no_total"] = True
        return
    for classe, subtotal in subtotais_por_classe.items():
        soma_cents = sum(
            round((p.get("valor_atual") or 0) * 100) for p in posicoes if p.get("classe") == classe
        )
        if soma_cents != round((subtotal or 0) * 100):
            escalate_result(result, ReviewReasonCode.extract_investment_sum_mismatch, _RV_CLASS_MSG)
            return
    result["checksum_ok"] = True


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


# Transitório (ADR-344): backstop de materialidade no ramo NÃO-certificado —
# gap > piso escala p/ needs_review, gap ≤ piso segue WARN (como hoje). Piso de
# materialidade-de-interrupção/leak, NÃO noise floor (ruído é <R$1); a faixa
# R$1–R$100 é drop real pequeno tolerado por design até o parser certificar.
# Absoluto/global único: piso relativo daria à conta MAIOR o MAIOR orçamento de
# drop silencioso (anti-ICP). Constante de módulo (não config) — deletar quando
# os parsers certificarem a semântica de saldo (deleção via código = intencional).
_CONSERVATION_MATERIALITY_PISO_CENTS = 10000  # R$ 100,00


def _apply_conservation_gate(result: Dict[str, Any], issues: List[str]) -> None:
    """Conservação global em cents, tolerância zero no caminho certificado (ADR-342).
    HARD (escala) quando o parser declarou `conservacao_verificavel`; senão, piso de
    materialidade (ADR-344): gap > piso escala, gap ≤ piso WARN. Sem valores na
    mensagem — só o fato e o código."""
    gap = conservation_gap_cents(result)
    if gap is None or gap == 0:
        return
    if result.get("conservacao_verificavel"):
        issues.append("ERROR: conservação global não fecha (saldo_inicial + Σtx ≠ saldo_final)")
        escalate_result(
            result,
            ReviewReasonCode.extract_incomplete_conservation,
            "conservação global não fecha em cents — escalado (ADR-342)",
        )
        return
    _apply_conservation_piso(result, issues, gap)


def _apply_conservation_piso(result: Dict[str, Any], issues: List[str], gap: int) -> None:
    """ADR-344 (transitório): caminho NÃO-certificado — gap > piso escala p/
    needs_review (code próprio), gap ≤ piso segue WARN (drop pequeno tolerado)."""
    if gap > _CONSERVATION_MATERIALITY_PISO_CENTS:
        issues.append("WARN→needs_review: gap de conservação acima do piso de materialidade")
        escalate_result(
            result,
            ReviewReasonCode.extract_conservation_above_piso,
            "conservação não fecha acima do piso de materialidade — escalado (ADR-344, transitório)",
        )
        return
    issues.append(
        "WARN: conservação global não fecha (abaixo do piso; parser sem semântica verificada)"
    )
    _warn_reason(
        result,
        ReviewReasonCode.extract_incomplete_conservation,
        "conservação não fecha abaixo do piso (WARN — gate HARD é opt-in do parser)",
    )


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

    _apply_fatura_checksum(result, issues)
    return result
