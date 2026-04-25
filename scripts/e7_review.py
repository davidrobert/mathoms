#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
E7 Review & Refine — Post-report holistic review with persona-driven analysis

Reads the complete E5 JSON (data + narrativas) and performs:
  1. Deterministic cross-validation checks between sections
  2. Consistency analysis between narrativas text and underlying data
  3. Generates a review structure for LLM-driven refinement
  4. Applies LLM refinements back to E5 JSON

Usage:
  python scripts/e7_review.py                       # Cross-validation + review template
  python scripts/e7_review.py --apply REVIEW.json    # Apply review refinements to E5 JSON
  python scripts/e7_review.py --dry-run              # Preview without changes
  python scripts/e7_review.py --strip                # Remove review key from E5 JSON

The E7 stage is an LLM stage. The typical workflow is:
  1. Run `python scripts/e7_review.py` to see cross-validation results
  2. LLM reads results + E5 JSON + methodology.md
  3. LLM creates review JSON using the persona/approach from methodology.md
  4. Run `python scripts/e7_review.py --apply review.json` to apply refinements
     (relatório atualizado disponível em /reports/[id] na UI React)

Author: Pipeline Ferreira Campos
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import scripts.pipeline_common as _pc

# =============================================================================
# Paths — all relative to workspace root (MATHOMS_WORKSPACE_ROOT)
# =============================================================================
_DEFAULT_BASE_DIR = _pc._REPO_ROOT

PROJECT_DIR: Path
E5_JSON_PATH: Path
METHODOLOGY_PATH: Path
DEFINITIONS_PATH: Path
FAMILY_CONFIG_PATH: Path
SCORING_CONFIG_PATH: Path
PIPELINE_CONFIG_PATH: Path
REPORT_SPEC_PATH: Path
OUTPUT_DIR: Path
REVIEW_TEMPLATE_PATH: Path


def _load_json_config(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _init_config(base_dir: Path) -> None:
    """(Re)carrega paths e configs a partir de um root_dir."""
    global PROJECT_DIR, E5_JSON_PATH, METHODOLOGY_PATH, DEFINITIONS_PATH
    global FAMILY_CONFIG_PATH, SCORING_CONFIG_PATH, PIPELINE_CONFIG_PATH
    global REPORT_SPEC_PATH, OUTPUT_DIR, REVIEW_TEMPLATE_PATH
    global _SCORING_CONFIG, _PIPELINE_CONFIG, _QA_THRESHOLDS

    PROJECT_DIR = base_dir
    E5_JSON_PATH = base_dir / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    METHODOLOGY_PATH = base_dir / "config" / "methodology.md"
    DEFINITIONS_PATH = base_dir / "config" / "definitions.md"
    FAMILY_CONFIG_PATH = base_dir / "config" / "family_members.json"
    SCORING_CONFIG_PATH = base_dir / "config" / "scoring.json"
    PIPELINE_CONFIG_PATH = base_dir / "config" / "pipeline.json"
    REPORT_SPEC_PATH = base_dir / "config" / "report_spec.md"
    OUTPUT_DIR = base_dir / "output"
    REVIEW_TEMPLATE_PATH = base_dir / "processed" / "E7_review" / "e7_review_template.json"

    _SCORING_CONFIG = _load_json_config(SCORING_CONFIG_PATH)
    _PIPELINE_CONFIG = _load_json_config(PIPELINE_CONFIG_PATH)
    _QA_THRESHOLDS = _PIPELINE_CONFIG.get("qa_thresholds", {})


# =============================================================================
# Module-level defaults (Sessão A6d.1 — eliminado side-effect no import)
# =============================================================================
#
# Antes de A6d.1: módulo invocava ``_init_config(_pc.PROJECT_DIR)`` no nível
# de módulo. Agora os globals começam com defaults; ``_init_config(base_dir)``
# é invocado por ``main(root_dir=...)`` e ``main_with_store(ctx)``.
PROJECT_DIR = _DEFAULT_BASE_DIR
E5_JSON_PATH = PROJECT_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
METHODOLOGY_PATH = PROJECT_DIR / "config" / "methodology.md"
DEFINITIONS_PATH = PROJECT_DIR / "config" / "definitions.md"
FAMILY_CONFIG_PATH = PROJECT_DIR / "config" / "family_members.json"
SCORING_CONFIG_PATH = PROJECT_DIR / "config" / "scoring.json"
PIPELINE_CONFIG_PATH = PROJECT_DIR / "config" / "pipeline.json"
REPORT_SPEC_PATH = PROJECT_DIR / "config" / "report_spec.md"
OUTPUT_DIR = PROJECT_DIR / "output"
REVIEW_TEMPLATE_PATH = PROJECT_DIR / "processed" / "E7_review" / "e7_review_template.json"
_SCORING_CONFIG: dict = {}
_PIPELINE_CONFIG: dict = {}
_QA_THRESHOLDS: dict = {}

# =============================================================================
# Data loading — everything from files, nothing hardcoded
# =============================================================================


def load_e5_json() -> dict:
    """Load E5 analysis JSON. Returns empty dict if not found."""
    if not E5_JSON_PATH.exists():
        print(f"  [ERRO] E5 JSON não encontrado: {E5_JSON_PATH}")
        return {}
    with open(E5_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_family_config() -> dict:
    """Load family members config."""
    if FAMILY_CONFIG_PATH.exists():
        with open(FAMILY_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_methodology() -> str:
    """Shell loader: lê ``METHODOLOGY_PATH`` se existir, senão string vazia.

    A6d.2: esta é a única função que toca disco para metodologia; o parser
    puro :func:`extract_persona_from_methodology` consome o conteúdo como
    parâmetro. Separação shell↔parser já estava correta — documentada aqui.
    """
    if METHODOLOGY_PATH.exists():
        with open(METHODOLOGY_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def load_latest_report() -> str | None:
    """Find and load the most recent HTML report. Returns content or None."""
    if not OUTPUT_DIR.exists():
        return None
    reports = sorted(OUTPUT_DIR.glob("relatorio_financeiro_*.html"), reverse=True)
    if not reports:
        return None
    with open(reports[0], "r", encoding="utf-8") as f:
        return f.read()


def extract_persona_from_methodology(methodology_text: str) -> dict:
    """Extract persona description and key principles from methodology.md."""
    persona = {
        "description": "",
        "key_principles": [],
        "mandatory_analyses": [],
        "restrictions": [],
    }
    if not methodology_text:
        return persona

    # Extract persona section
    persona_match = re.search(
        r"## PERSONA E ABORDAGEM\s*\n(.*?)(?=\n## |\Z)",
        methodology_text,
        re.DOTALL,
    )
    if persona_match:
        persona["description"] = persona_match.group(1).strip()

    # Extract numbered mandatory analyses
    numbered = re.findall(r"\d+\.\s+(.+?)(?=\n\d+\.|\n\n|\Z)", methodology_text)
    persona["mandatory_analyses"] = [n.strip() for n in numbered if len(n.strip()) > 10]

    # Extract restrictions
    restrict_match = re.search(
        r"## RESTRIÇÕES IMPORTANTES\s*\n(.*?)(?=\n## |\Z)",
        methodology_text,
        re.DOTALL,
    )
    if restrict_match:
        restrictions = re.findall(r"- (.+)", restrict_match.group(1))
        persona["restrictions"] = [r.strip() for r in restrictions]

    return persona


# =============================================================================
# Cross-validation checks — 100% deterministic, data-driven
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
        f"{len(format_issues)} issue(s): {format_issues[:3]}"
        if format_issues
        else "Formato OK",
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
# Review template generation
# =============================================================================


def build_review_template(e5: dict, cv_results: list[CrossValidationResult], persona: dict) -> dict:
    """Build a review template that the LLM will fill in.

    The template contains:
    - Cross-validation results (pre-filled, deterministic)
    - Sections for LLM to fill: refined narrativas, strategic insights, task re-prioritization
    """
    narr = e5.get("narrativas", {})
    summaries = narr.get("summaries", {})
    charts = narr.get("charts", {})
    tarefas = e5.get("tarefas", [])

    template = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "e7_version": "1.0",
            "persona_summary": persona.get("description", "")[:200],
        },
        "cross_validation": {
            "total_checks": len(cv_results),
            "passed": sum(1 for r in cv_results if r.passed),
            "failed": sum(1 for r in cv_results if not r.passed),
            "issues": [r.to_dict() for r in cv_results if not r.passed],
            "all_results": [r.to_dict() for r in cv_results],
        },
        "refinements": {
            "_instructions": (
                "LLM: Preencha as seções abaixo usando a persona e abordagem do methodology.md. "
                "Inclua apenas os itens que precisam de refinamento. "
                "Itens ausentes serão mantidos como estão."
            ),
            "summaries": {
                "_instructions": (
                    "Revise cada summary (s1-s10) considerando o relatório completo. "
                    "Inclua apenas os que precisam de ajuste. "
                    "Mantenha formato monetário brasileiro (R$ Xk, R$ X,YM)."
                ),
                # LLM fills: "s1": "refined text", "s3": "refined text", ...
            },
            "charts": {
                "_instructions": (
                    "Revise context/conclusion de cada gráfico. "
                    "Inclua apenas os que precisam de ajuste."
                ),
                # LLM fills: "chart_key": {"context": "...", "conclusion": "..."}, ...
            },
            "perfil_familia": {
                "_instructions": (
                    "Revise left/right do perfil. Inclua apenas se precisar de ajuste."
                ),
                # LLM fills: "left": "...", "right": "..."
            },
            "tarefas_reorder": {
                "_instructions": (
                    "Se a ordem de prioridade das tarefas precisa mudar, "
                    "liste os números das tarefas na nova ordem. "
                    "Exemplo: [3, 1, 5, 2, 4, ...] para re-priorizar."
                ),
                "new_order": [],  # LLM fills with task numbers
            },
            "strategic_insights": {
                "_instructions": (
                    "Insights estratégicos que emergiram da visão holística "
                    "do relatório completo. São observações que não ficaram claras "
                    "nas análises individuais de cada seção."
                ),
                "insights": [],  # LLM fills: ["insight1", "insight2", ...]
            },
            "inconsistencies_found": {
                "_instructions": (
                    "Inconsistências entre seções que a LLM identificou "
                    "além das detectadas pela cross-validation automática."
                ),
                "items": [],  # LLM fills: [{"sections": [...], "description": "..."}, ...]
            },
        },
        "current_state": {
            "_note": "Snapshot do estado atual para referência da LLM (read-only)",
            "summary_keys": list(summaries.keys()),
            "chart_keys": list(charts.keys()),
            "total_tarefas": len(tarefas),
            "tarefas_alta_prioridade": [
                t for t in tarefas if isinstance(t, dict) and t.get("p") == "alta"
            ],
            "score": e5.get("score", {}).get("valor"),
            "score_label": e5.get("score", {}).get("classificacao"),
            "patrimonio_bruto": e5.get("patrimonio", {}).get("bruto"),
            "patrimonio_investivel": e5.get("patrimonio", {}).get("investivel"),
            "fluxo_liquido": e5.get("fluxo_caixa", {}).get("fluxo_liquido"),
        },
    }

    return template


# =============================================================================
# Apply review refinements
# =============================================================================


def validate_review(review: dict) -> tuple[bool, list[str]]:
    """Validate review JSON structure before applying."""
    errors = []

    if "refinements" not in review:
        errors.append("Missing 'refinements' key")
        return False, errors

    ref = review["refinements"]

    # Validate summaries
    summaries = ref.get("summaries", {})
    for k, v in summaries.items():
        if k.startswith("_"):
            continue
        if not isinstance(v, str):
            errors.append(f"summaries.{k} must be a string")
        elif not v.strip():
            errors.append(f"summaries.{k} is empty")

    # Validate charts
    charts = ref.get("charts", {})
    for ck, cv in charts.items():
        if ck.startswith("_"):
            continue
        if not isinstance(cv, dict):
            errors.append(f"charts.{ck} must be a dict with context/conclusion")
        else:
            if "context" in cv and not isinstance(cv["context"], str):
                errors.append(f"charts.{ck}.context must be a string")
            if "conclusion" in cv and not isinstance(cv["conclusion"], str):
                errors.append(f"charts.{ck}.conclusion must be a string")

    # Validate perfil_familia
    pf = ref.get("perfil_familia", {})
    for side in ["left", "right"]:
        if side in pf and not isinstance(pf[side], str):
            errors.append(f"perfil_familia.{side} must be a string")

    # Validate tarefas_reorder
    reorder = ref.get("tarefas_reorder", {})
    new_order = reorder.get("new_order", [])
    if new_order and not all(isinstance(n, int) for n in new_order):
        errors.append("tarefas_reorder.new_order must be a list of integers")

    # Validate strategic_insights
    insights = ref.get("strategic_insights", {})
    items = insights.get("insights", [])
    if items and not all(isinstance(i, str) for i in items):
        errors.append("strategic_insights.insights must be a list of strings")

    return len(errors) == 0, errors


def apply_review(e5: dict, review: dict, dry_run: bool = False) -> dict:
    """Apply review refinements to E5 JSON. Returns updated E5 data.

    Only modifies fields explicitly provided in the review.
    Original data is preserved for any field not in the review.
    """
    ref = review.get("refinements", {})
    changes = []

    narr = e5.get("narrativas", {})

    # --- Apply summary refinements ---
    summaries = ref.get("summaries", {})
    for k, v in summaries.items():
        if k.startswith("_"):
            continue
        if isinstance(v, str) and v.strip():
            old = narr.get("summaries", {}).get(k, "")
            if old != v:
                if dry_run:
                    print(f"  [DRY-RUN] Refinaria summaries.{k}")
                else:
                    narr.setdefault("summaries", {})[k] = v
                changes.append(f"summaries.{k}")

    # --- Apply chart refinements ---
    charts_ref = ref.get("charts", {})
    for ck, cv in charts_ref.items():
        if ck.startswith("_") or not isinstance(cv, dict):
            continue
        existing = narr.get("charts", {}).get(ck, {})
        changed = False
        for field in ["context", "conclusion"]:
            if field in cv and isinstance(cv[field], str) and cv[field].strip():
                if existing.get(field) != cv[field]:
                    if not dry_run:
                        narr.setdefault("charts", {}).setdefault(ck, {})[field] = cv[field]
                    changed = True
        if changed:
            if dry_run:
                print(f"  [DRY-RUN] Refinaria charts.{ck}")
            changes.append(f"charts.{ck}")

    # --- Apply perfil_familia refinements ---
    pf_ref = ref.get("perfil_familia", {})
    for side in ["left", "right"]:
        if side in pf_ref and isinstance(pf_ref[side], str) and pf_ref[side].strip():
            old = narr.get("perfil_familia", {}).get(side, "")
            if old != pf_ref[side]:
                if dry_run:
                    print(f"  [DRY-RUN] Refinaria perfil_familia.{side}")
                else:
                    narr.setdefault("perfil_familia", {})[side] = pf_ref[side]
                changes.append(f"perfil_familia.{side}")

    # --- Apply tarefas reorder ---
    reorder = ref.get("tarefas_reorder", {})
    new_order = reorder.get("new_order", [])
    if new_order:
        tarefas = e5.get("tarefas", [])
        # Build index by task number
        tarefas_by_n = {t.get("n"): t for t in tarefas if isinstance(t, dict) and "n" in t}
        reordered = []
        seen = set()
        for n in new_order:
            if n in tarefas_by_n and n not in seen:
                task = tarefas_by_n[n].copy()
                task["n"] = len(reordered) + 1  # renumber
                reordered.append(task)
                seen.add(n)
        # Append remaining tasks not in new_order
        for t in tarefas:
            n = t.get("n")
            if n not in seen:
                task = t.copy()
                task["n"] = len(reordered) + 1
                reordered.append(task)
                seen.add(n)
        if reordered and not dry_run:
            e5["tarefas"] = reordered
        if reordered:
            if dry_run:
                print(f"  [DRY-RUN] Re-ordenaria {len(reordered)} tarefas")
            changes.append(f"tarefas (reordered {len(new_order)} items)")

    # --- Store strategic insights ---
    insights = ref.get("strategic_insights", {}).get("insights", [])
    if insights:
        if not dry_run:
            narr["strategic_insights"] = insights
        changes.append(f"strategic_insights ({len(insights)} items)")

    # --- Store inconsistencies found by LLM ---
    inconsistencies = ref.get("inconsistencies_found", {}).get("items", [])
    if inconsistencies:
        if not dry_run:
            narr["inconsistencies_review"] = inconsistencies
        changes.append(f"inconsistencies_review ({len(inconsistencies)} items)")

    # --- Store review metadata ---
    if not dry_run:
        e5["narrativas"] = narr
        e5["review_metadata"] = {
            "timestamp": review.get("metadata", {}).get("timestamp", datetime.now().isoformat()),
            "e7_version": review.get("metadata", {}).get("e7_version", "1.0"),
            "changes_applied": changes,
            "cross_validation_passed": review.get("cross_validation", {}).get("passed", 0),
            "cross_validation_failed": review.get("cross_validation", {}).get("failed", 0),
        }

    return e5


# =============================================================================
# Strip review from E5 JSON
# =============================================================================


def strip_review_from_e5(dry_run: bool = False) -> int:
    """Remove review-related keys from E5 JSON. Returns count of files modified."""
    if not E5_JSON_PATH.exists():
        print("  [WARN] E5 JSON não encontrado")
        return 0

    with open(E5_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    keys_to_remove = ["review_metadata"]
    narr_keys_to_remove = ["strategic_insights", "inconsistencies_review"]

    modified = False
    for k in keys_to_remove:
        if k in data:
            if dry_run:
                print(f"  [DRY-RUN] Removeria '{k}' do E5 JSON")
            else:
                del data[k]
            modified = True

    narr = data.get("narrativas", {})
    for k in narr_keys_to_remove:
        if k in narr:
            if dry_run:
                print(f"  [DRY-RUN] Removeria 'narrativas.{k}' do E5 JSON")
            else:
                del narr[k]
            modified = True

    if modified and not dry_run:
        with open(E5_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return 1 if modified else 0


# =============================================================================
# Main
# =============================================================================


def main_with_store(ctx, *, mode: str = "crossval", review_path: str | None = None) -> dict:
    """E7 Caminho B (Sessão A5e da Fase 8) — cross-validation + apply sobre
    ``ArtifactStore`` em vez de disco direto.

    Modos:
    - ``"crossval"`` (default) — roda 14 checks CV1-CV14 sobre o E5, gera
      template para LLM em ``store.write("E7-crossval", "template", ...)``.
    - ``"apply"`` — aplica review LLM ao E5 e escreve ``E5-revised`` no store.

    O modo ``review`` (geração do template LLM) é parte do ``crossval`` —
    não é um stage separado. O passo LLM propriamente dito é externo ao
    pipeline (operador lê o template, roda LLM, salva review.json).

    Coexiste com ``main(root_dir)`` legado. Wrappers
    ``pipeline/stages/e7.py::run_crossval`` e ``run_apply`` chamam esta
    função direto.

    Args:
        ctx: ``pipeline.context.WorkspaceContext``.
        mode: ``"crossval"`` ou ``"apply"``.
        review_path: caminho para review JSON (obrigatório em ``apply``).

    Returns:
        Dict com resumo do modo executado.
    """
    import scripts.pipeline_common as _pc

    _pc._init_config(ctx.root)
    _init_config(ctx.root)

    store = ctx.get_artifact_store()
    print("=" * 70)
    print(f"  E7 REVIEW & REFINE — Caminho B (mode={mode})")
    print("=" * 70)
    print(f"[E7.0] Workspace root: {ctx.root}")
    print(f"[E7.0] Store impl:     {type(store).__name__}")

    # 1. Lê E5 via store.
    e5 = store.read("E5", "analise_financeira") or {}
    if not e5:
        print("  [ERRO] E5 artifact 'analise_financeira' não encontrado.")
        return {"success": False, "reason": "e5_not_found"}

    # Valida narrativas presentes (pré-requisito E5.N).
    narr = e5.get("narrativas", {})
    has_narrativas = bool(narr.get("summaries")) and bool(narr.get("charts"))
    if not has_narrativas:
        print("  [ERRO] E5 sem narrativas. Execute E5.N antes de E7.")
        return {"success": False, "reason": "missing_narrativas"}

    print(f"  ✓ E5 JSON: {len(e5)} top-level keys, narrativas presentes")

    # 2. Modo apply — aplica review ao E5.
    if mode == "apply":
        if not review_path:
            print("  [SKIP] Modo apply sem review_path — nada a fazer.")
            return {"success": True, "skipped": True, "reason": "no_review_path"}

        review_file = Path(review_path)
        if not review_file.is_absolute():
            review_file = ctx.root / review_path
        if not review_file.exists():
            print(f"  [ERRO] Review file não encontrado: {review_file}")
            return {"success": False, "reason": "review_not_found"}

        with open(review_file, "r", encoding="utf-8") as f:
            review = json.load(f)

        is_valid, errors = validate_review(review)
        if not is_valid:
            print("  [ERRO] Review inválido:")
            for e in errors:
                print(f"    - {e}")
            return {"success": False, "reason": "review_invalid", "errors": errors}

        updated_e5 = apply_review(e5, review, dry_run=False)
        store.write("E5", "analise_financeira", updated_e5)

        changes = review.get("refinements", {})
        change_count = sum(
            1 for k, v in changes.items() if not k.startswith("_") and v and v != {} and v != []
        )
        print(f"  ✓ Aplicados {change_count} refinamento(s) ao E5")
        return {
            "success": True,
            "mode": "apply",
            "refinements_applied": change_count,
            "files_created": ["analise_financeira-5_analysis.json"],
        }

    # 3. Modo crossval — 14 checks + gera template.
    if mode != "crossval":
        return {"success": False, "reason": f"unknown_mode:{mode}"}

    methodology_text = load_methodology()
    persona = extract_persona_from_methodology(methodology_text)
    print(f"  Methodology: {'carregado' if methodology_text else 'não encontrado'}")

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

    # Gera template — grava em disco via path legado para paridade 100% com
    # ``main()``. O template é consumido pelo operador que roda o LLM; não é
    # artifact padrão via ``ArtifactStore``. Apenas o E5 revisado (modo apply)
    # passa pelo store.
    template = build_review_template(e5, cv_results, persona)
    REVIEW_TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _pc.write_json_atomic(REVIEW_TEMPLATE_PATH, template)

    print(f"  ✓ Template gravado em {REVIEW_TEMPLATE_PATH.relative_to(ctx.root)}")
    print("=" * 70)

    return {
        "success": True,
        "mode": "crossval",
        "checks_total": len(cv_results),
        "checks_passed": passed,
        "checks_failed": failed,
        "errors_count": len(errors_list),
        "warnings_count": len(warnings_list),
        "files_created": ["e7_review_template.json"],
    }
