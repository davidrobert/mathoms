#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
E7 Cross-Validation — 14 checks determinísticos sobre o E5.

Após ADR-199 (parecer planejador supersede review_finances), este script
ficou só com a parte de cross-validation (`run_crossval`). As funções de
review LLM (build template, validate review, apply review) foram removidas
junto com o stage ``review_finances`` em A12.X.

Wrapper canônico: ``pipeline/stages/validate_cross.py::run``, que chama
``main_with_store(ctx, mode="crossval")`` aqui dentro.

O nome do arquivo (``e7_review.py``) é mantido por compat histórica
com import paths legados; o conteúdo é exclusivamente crossval.
"""

import json
import re
from pathlib import Path

import scripts.pipeline_common as _pc

# =============================================================================
# Paths — all relative to workspace root (MATHOMS_WORKSPACE_ROOT)
# =============================================================================
_DEFAULT_BASE_DIR = _pc._REPO_ROOT

PROJECT_DIR: Path
E5_JSON_PATH: Path
FAMILY_CONFIG_PATH: Path
SCORING_CONFIG_PATH: Path
PIPELINE_CONFIG_PATH: Path
REPORT_SPEC_PATH: Path
OUTPUT_DIR: Path


def _load_json_config(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _init_config(base_dir: Path) -> None:
    """(Re)carrega paths e configs a partir de um root_dir."""
    global PROJECT_DIR, E5_JSON_PATH
    global FAMILY_CONFIG_PATH, SCORING_CONFIG_PATH, PIPELINE_CONFIG_PATH
    global REPORT_SPEC_PATH, OUTPUT_DIR
    global _SCORING_CONFIG, _PIPELINE_CONFIG, _QA_THRESHOLDS

    PROJECT_DIR = base_dir
    E5_JSON_PATH = base_dir / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    FAMILY_CONFIG_PATH = base_dir / "config" / "family_members.json"
    SCORING_CONFIG_PATH = base_dir / "config" / "scoring.json"
    PIPELINE_CONFIG_PATH = base_dir / "config" / "pipeline.json"
    REPORT_SPEC_PATH = base_dir / "config" / "report_spec.md"
    OUTPUT_DIR = base_dir / "output"

    _SCORING_CONFIG = _load_json_config(SCORING_CONFIG_PATH)
    _PIPELINE_CONFIG = _load_json_config(PIPELINE_CONFIG_PATH)
    _QA_THRESHOLDS = _PIPELINE_CONFIG.get("qa_thresholds", {})


# =============================================================================
# Module-level defaults (Sessão A6d.1 — eliminado side-effect no import)
# =============================================================================
PROJECT_DIR = _DEFAULT_BASE_DIR
E5_JSON_PATH = PROJECT_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
FAMILY_CONFIG_PATH = PROJECT_DIR / "config" / "family_members.json"
SCORING_CONFIG_PATH = PROJECT_DIR / "config" / "scoring.json"
PIPELINE_CONFIG_PATH = PROJECT_DIR / "config" / "pipeline.json"
REPORT_SPEC_PATH = PROJECT_DIR / "config" / "report_spec.md"
OUTPUT_DIR = PROJECT_DIR / "output"
_SCORING_CONFIG: dict = {}
_PIPELINE_CONFIG: dict = {}
_QA_THRESHOLDS: dict = {}


# =============================================================================
# Cross-validation results
# =============================================================================


class CrossValidationResult:
    """Holds results of a single cross-validation check."""

    def __init__(
        self,
        check_id: str,
        name: str,
        severity: str,
        passed: bool,
        details: str,
        sections: list[str] | None = None,
    ):
        self.check_id = check_id
        self.name = name
        self.severity = severity  # "error", "warning", "info"
        self.passed = passed
        self.details = details
        self.sections = sections or []

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "severity": self.severity,
            "passed": self.passed,
            "details": self.details,
            "sections": self.sections,
        }


def _cv1_score_formula(e5: dict) -> CrossValidationResult | None:
    score_data = e5.get("score", {})
    componentes = score_data.get("componentes", [])
    if not componentes:
        return None
    weighted_sum = sum(c.get("nota", 0) * c.get("peso", 0) for c in componentes)
    total_weight = sum(c.get("peso", 0) for c in componentes)
    if total_weight <= 0:
        return None
    calculated_score = round(weighted_sum / total_weight, 1)
    reported_score = score_data.get("valor", 0)
    diff = abs(calculated_score - reported_score)
    threshold = _QA_THRESHOLDS.get("score_diff_max", 0.5)
    return CrossValidationResult(
        "CV1",
        "Score formula consistency",
        "error" if diff > threshold else "info",
        diff <= threshold,
        f"Score reportado: {reported_score}, calculado: {calculated_score}, diff: {diff:.1f}",
        ["score"],
    )


def _cv2_patrimonio_composicao(e5: dict) -> CrossValidationResult | None:
    pat = e5.get("patrimonio", {})
    composicao = pat.get("composicao", [])
    if not composicao:
        return None
    comp_sum = sum(c.get("valor", 0) for c in composicao if isinstance(c, dict))
    bruto = pat.get("bruto", 0)
    if bruto <= 0:
        return None
    diff_pct = abs(comp_sum - bruto) / bruto * 100
    threshold = _QA_THRESHOLDS.get("patrimonio_composicao_diff_pct_max", 5)
    return CrossValidationResult(
        "CV2",
        "Patrimônio composição vs bruto",
        "warning" if diff_pct > threshold else "info",
        diff_pct <= threshold,
        f"Soma composição: R$ {comp_sum:,.0f}, bruto: R$ {bruto:,.0f}, diff: {diff_pct:.1f}%",
        ["patrimonio"],
    )


def _cv3_fluxo_aritmetica(e5: dict) -> CrossValidationResult | None:
    fluxo = e5.get("fluxo_caixa", {})
    receita = fluxo.get("receita_total", 0)
    despesa = fluxo.get("despesa_total", 0)
    fluxo_liq = fluxo.get("fluxo_liquido", 0)
    if receita <= 0 and despesa <= 0:
        return None
    expected_fluxo = receita - despesa
    diff = abs(expected_fluxo - fluxo_liq)
    threshold = _QA_THRESHOLDS.get("cv_fluxo_diff_max", 100)
    return CrossValidationResult(
        "CV3",
        "Fluxo de caixa aritmética",
        "warning" if diff > threshold else "info",
        diff <= threshold,
        f"Receita ({receita:,.0f}) - Despesa ({despesa:,.0f}) = {expected_fluxo:,.0f}, reportado: {fluxo_liq:,.0f}",
        ["fluxo_caixa"],
    )


def _cv4_taxa_poupanca(e5: dict) -> CrossValidationResult | None:
    fluxo = e5.get("fluxo_caixa", {})
    ratios = e5.get("ratios", {})
    tp_pct = ratios.get("taxa_poupanca_recorrente_pct", None)
    rec_recorrente = fluxo.get("receita_recorrente", 0)
    despesa = fluxo.get("despesa_total", 0)
    if tp_pct is None or rec_recorrente <= 0:
        return None
    calculated_tp = ((rec_recorrente - despesa) / rec_recorrente) * 100
    diff = abs(calculated_tp - tp_pct)
    threshold = _QA_THRESHOLDS.get("cv_taxa_poupanca_diff_pp_max", 5)
    return CrossValidationResult(
        "CV4",
        "Taxa poupança recorrente",
        "warning" if diff > threshold else "info",
        diff <= threshold,
        f"Calculada: {calculated_tp:.1f}%, reportada: {tp_pct:.1f}%, diff: {diff:.1f}pp",
        ["ratios", "fluxo_caixa"],
    )


def _cv5_if_monthly(e5: dict) -> CrossValidationResult | None:
    goals = e5.get("goals", {})
    if_meta = goals.get("if_meta", 0)
    if_trs = goals.get("if_trs", 0)
    if_monthly = goals.get("if_trs_monthly_value", 0)
    if if_meta <= 0 or if_trs <= 0:
        return None
    expected_monthly = (if_meta * if_trs / 100) / 12
    diff = abs(expected_monthly - if_monthly)
    threshold = _QA_THRESHOLDS.get("cv_if_monthly_diff_max", 500)
    return CrossValidationResult(
        "CV5",
        "IF meta × TRS = renda mensal",
        "warning" if diff > threshold else "info",
        diff <= threshold,
        f"Meta R$ {if_meta:,.0f} × {if_trs}% / 12 = R$ {expected_monthly:,.0f}/mês, "
        f"reportado: R$ {if_monthly:,.0f}/mês",
        ["goals"],
    )


def _cv6_if_progress(e5: dict) -> CrossValidationResult | None:
    goals = e5.get("goals", {})
    pat = e5.get("patrimonio", {})
    if_meta = goals.get("if_meta", 0)
    if_pct = goals.get("if_pct", 0)
    pat_investivel = pat.get("investivel", 0)
    if if_meta <= 0:
        return None
    calculated_pct = (pat_investivel / if_meta) * 100
    diff = abs(calculated_pct - if_pct)
    threshold = _QA_THRESHOLDS.get("cv_if_progress_diff_pct_max", 2)
    return CrossValidationResult(
        "CV6",
        "Progresso IF vs patrimônio investível",
        "warning" if diff > threshold else "info",
        diff <= threshold,
        f"Investível/Meta = {calculated_pct:.1f}%, reportado: {if_pct:.1f}%",
        ["goals", "patrimonio"],
    )


def _cv7_endividamento(e5: dict) -> CrossValidationResult | None:
    endiv = e5.get("endividamento", {})
    pat = e5.get("patrimonio", {})
    total_dividas = endiv.get("total_dividas", 0)
    endiv_pct = endiv.get("percentual_patrimonio", 0)
    bruto = pat.get("bruto", 0)
    if bruto <= 0:
        return None
    calculated_endiv = (total_dividas / bruto) * 100
    diff = abs(calculated_endiv - endiv_pct)
    threshold = _QA_THRESHOLDS.get("cv_endividamento_diff_pct_max", 1)
    return CrossValidationResult(
        "CV7",
        "Taxa endividamento vs patrimônio",
        "warning" if diff > threshold else "info",
        diff <= threshold,
        f"Dívidas/Bruto = {calculated_endiv:.1f}%, reportado: {endiv_pct:.1f}%",
        ["endividamento", "patrimonio"],
    )


def _cv8_reserva_cobertura(e5: dict) -> CrossValidationResult | None:
    reserva = e5.get("reserva_emergencia", {})
    total_liquida = reserva.get("total_liquida", 0)
    despesas_mensais = reserva.get("despesas_mensais", 0)
    cobertura = reserva.get("cobertura_meses", 0)
    if despesas_mensais <= 0:
        return None
    calculated_cob = total_liquida / despesas_mensais
    diff = abs(calculated_cob - cobertura)
    return CrossValidationResult(
        "CV8",
        "Cobertura reserva emergência",
        "warning" if diff > 1 else "info",
        diff <= 1,
        f"Líquida/Despesas = {calculated_cob:.1f} meses, reportado: {cobertura:.1f}",
        ["reserva_emergencia"],
    )


def _cv9_summaries_completeness(e5: dict) -> CrossValidationResult:
    narr = e5.get("narrativas", {})
    summaries = narr.get("summaries", {})
    missing_summaries = [f"s{i}" for i in range(1, 11) if f"s{i}" not in summaries]
    empty_summaries = [k for k, v in summaries.items() if not v or not v.strip()]
    severity = "error" if missing_summaries else ("warning" if empty_summaries else "info")
    return CrossValidationResult(
        "CV9",
        "Narrativas completeness (summaries)",
        severity,
        not missing_summaries and not empty_summaries,
        f"Missing: {missing_summaries or 'nenhum'}, Empty: {empty_summaries or 'nenhum'}",
        ["narrativas"],
    )


_REQUIRED_CHARTS = [
    "score_gauge",
    "patrimonio_doughnut",
    "alocacao_atual",
    "alocacao_alvo",
    "fluxo_mensal",
    "receita_bar",
    "receita_despesa_mensal",
    "despesas_doughnut",
]


def _cv10_charts_completeness(e5: dict) -> CrossValidationResult:
    narr = e5.get("narrativas", {})
    charts = narr.get("charts", {})
    missing_charts = [c for c in _REQUIRED_CHARTS if c not in charts]
    incomplete_charts = []
    for ck, cv in charts.items():
        if isinstance(cv, dict):
            if not cv.get("context") or not cv.get("conclusion"):
                incomplete_charts.append(ck)
    severity = "error" if missing_charts else ("warning" if incomplete_charts else "info")
    return CrossValidationResult(
        "CV10",
        "Charts completeness",
        severity,
        not missing_charts and not incomplete_charts,
        f"Missing: {missing_charts or 'nenhum'}, Incomplete: {incomplete_charts or 'nenhum'}",
        ["narrativas"],
    )


def _cv11_tarefas_structure(e5: dict) -> CrossValidationResult:
    tarefas = e5.get("tarefas", [])
    tarefas_ok = (
        all(isinstance(t, dict) and "t" in t and "p" in t for t in tarefas) if tarefas else False
    )
    return CrossValidationResult(
        "CV11",
        "Tarefas structure",
        "warning" if not tarefas_ok else "info",
        tarefas_ok,
        f"{len(tarefas)} tarefas encontradas, structure OK: {tarefas_ok}",
        ["tarefas"],
    )


def _cv12_diagnostico(e5: dict) -> CrossValidationResult:
    diag = e5.get("diagnostico_comportamental", [])
    return CrossValidationResult(
        "CV12",
        "Diagnóstico comportamental presente",
        "warning" if not diag else "info",
        bool(diag),
        f"{len(diag)} padrão(ões) detectado(s)"
        if diag
        else "Nenhum padrão — verificar se intencional",
        ["diagnostico_comportamental"],
    )


def _cv13_score_label(e5: dict) -> CrossValidationResult:
    score_data = e5.get("score", {})
    score_val = score_data.get("valor", 0)
    score_label = score_data.get("classificacao", "")
    expected_label = _score_classification(score_val)
    label_match = expected_label.lower() == score_label.lower()
    return CrossValidationResult(
        "CV13",
        "Score classification label",
        "warning" if not label_match else "info",
        label_match,
        f"Score {score_val} → esperado: '{expected_label}', reportado: '{score_label}'",
        ["score"],
    )


def _cv14_monetary_format(e5: dict) -> CrossValidationResult:
    narr = e5.get("narrativas", {})
    format_issues = _check_narrativas_monetary_format(narr)
    return CrossValidationResult(
        "CV14",
        "Monetary format in narrativas",
        "warning" if format_issues else "info",
        not format_issues,
        f"{len(format_issues)} issue(s): {format_issues[:3]}" if format_issues else "Formato OK",
        ["narrativas"],
    )


_CV_OPTIONAL_CHECKS = (
    _cv1_score_formula,
    _cv2_patrimonio_composicao,
    _cv3_fluxo_aritmetica,
    _cv4_taxa_poupanca,
    _cv5_if_monthly,
    _cv6_if_progress,
    _cv7_endividamento,
    _cv8_reserva_cobertura,
)
_CV_ALWAYS_CHECKS = (
    _cv9_summaries_completeness,
    _cv10_charts_completeness,
    _cv11_tarefas_structure,
    _cv12_diagnostico,
    _cv13_score_label,
    _cv14_monetary_format,
)


def run_cross_validation(e5: dict) -> list[CrossValidationResult]:
    """Run all deterministic cross-validation checks on E5 data."""
    results: list[CrossValidationResult] = []
    for check in _CV_OPTIONAL_CHECKS:
        result = check(e5)
        if result is not None:
            results.append(result)
    for check in _CV_ALWAYS_CHECKS:
        results.append(check(e5))
    return results


def _score_classification(score: float) -> str:
    """Map score value to classification label. Loaded from scoring.json."""
    classificacao = _SCORING_CONFIG.get("score_classificacao", [])
    if classificacao:
        for entry in reversed(classificacao):
            if score >= entry.get("min", 0):
                return entry.get("label", "")
        return classificacao[0].get("label", "Crítico")
    if score >= 8:
        return "Excelente"
    elif score >= 6:
        return "Bom"
    elif score >= 4:
        return "Regular"
    elif score >= 2:
        return "Atenção"
    return "Crítico"


def _check_narrativas_monetary_format(narr: dict) -> list[str]:
    """Check for common monetary formatting issues in narrativas text."""
    issues = []

    def _check_text(text: str, field: str):
        if not text:
            return
        # Invalid KM suffix
        if re.search(r"R\$\s*[\d.,]+\s*KM", text, re.IGNORECASE):
            issues.append(f"{field}: sufixo 'KM' inválido")
        # Space between value and k/M
        if re.search(r"R\$\s*[\d.,]+\s+[kM]", text):
            issues.append(f"{field}: espaço entre valor e sufixo k/M")

    # Check summaries
    for k, v in narr.get("summaries", {}).items():
        if isinstance(v, str):
            _check_text(v, f"summaries.{k}")

    # Check charts
    for ck, cv in narr.get("charts", {}).items():
        if isinstance(cv, dict):
            _check_text(cv.get("context", ""), f"charts.{ck}.context")
            _check_text(cv.get("conclusion", ""), f"charts.{ck}.conclusion")

    # Check perfil_familia
    pf = narr.get("perfil_familia", {})
    for side in ["left", "right"]:
        if isinstance(pf.get(side), str):
            _check_text(pf[side], f"perfil_familia.{side}")

    return issues


# =============================================================================
# main_with_store
# =============================================================================


def main_with_store(ctx, *, mode: str = "crossval") -> dict:
    """Roda os 14 checks CV1-CV14 sobre o E5 do workspace.

    O ``mode`` é mantido por compat de assinatura; só ``"crossval"`` é aceito
    (modos ``apply`` e ``review`` foram removidos junto com o stage
    ``review_finances`` em A12.X — ADR-199).
    """
    _pc._init_config(ctx.root)
    _init_config(ctx.root)

    if mode != "crossval":
        return {"success": False, "reason": f"unknown_mode:{mode}"}

    store = ctx.get_artifact_store()
    print("=" * 70)
    print("  E7 CROSS-VALIDATION")
    print("=" * 70)
    print(f"[E7.0] Workspace root: {ctx.root}")
    print(f"[E7.0] Store impl:     {type(store).__name__}")

    e5 = store.read("E5", "analise_financeira") or {}
    if not e5:
        print("  [ERRO] E5 artifact 'analise_financeira' não encontrado.")
        return {"success": False, "reason": "e5_not_found"}

    narr = e5.get("narrativas", {})
    has_narrativas = bool(narr.get("summaries")) and bool(narr.get("charts"))
    if not has_narrativas:
        print("  [ERRO] E5 sem narrativas. Execute E5.N antes de E7.")
        return {"success": False, "reason": "missing_narrativas"}

    print(f"  ✓ E5 JSON: {len(e5)} top-level keys, narrativas presentes")

    cv_results = run_cross_validation(e5)
    passed = sum(1 for r in cv_results if r.passed)
    failed = sum(1 for r in cv_results if not r.passed)
    errors_list = [r for r in cv_results if not r.passed and r.severity == "error"]
    warnings_list = [r for r in cv_results if not r.passed and r.severity == "warning"]

    print(f"  Checks: {len(cv_results)} total, {passed} passed, {failed} failed")
    if errors_list:
        print(f"\n  ERROS ({len(errors_list)}):")
        for r in errors_list:
            print(f"    [{r.check_id}] {r.name}: {r.details}")
    if warnings_list:
        print(f"\n  AVISOS ({len(warnings_list)}):")
        for r in warnings_list:
            print(f"    [{r.check_id}] {r.name}: {r.details}")

    print("=" * 70)

    return {
        "success": True,
        "mode": "crossval",
        "checks_total": len(cv_results),
        "checks_passed": passed,
        "checks_failed": failed,
        "errors_count": len(errors_list),
        "warnings_count": len(warnings_list),
        "results": [r.to_dict() for r in cv_results],
    }
