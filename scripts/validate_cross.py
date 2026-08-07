#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
E7 Cross-Validation — checks determinísticos (CV1–CV17; CV15 reservado) sobre o E5.

Após ADR-199 (parecer planejador supersede review_finances), este script
ficou só com a parte de cross-validation (`run_crossval`). As funções de
review LLM (build template, validate review, apply review) foram removidas
junto com o stage ``review_finances`` em A12.X.

Wrapper canônico: ``pipeline/stages/validate_cross.py::run``, que chama
``main_with_store(ctx, mode="crossval")`` aqui dentro.

Renomeado de ``e7_review.py`` → ``validate_cross.py`` em F9.4 (ADR-093),
espelhando E7-crossval → validate_cross; o conteúdo é exclusivamente crossval.
"""

import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml

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


# Layout é artefato do produto, versionado no repo (ADR-076) — não config de
# tenant. O override DB de ``report_layout`` não afeta o renderer React
# (`ReportShell` importa `@/generated/report-layout`), então o YAML é a fonte
# correta hoje; se o renderer passar a ler o layout do DB, este leitor segue.
def _load_report_layout() -> dict:
    """``config/report_layout.yaml`` do REPO (não do workspace)."""
    path = _pc._REPO_ROOT / "config" / "report_layout.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _init_config(base_dir: Path) -> None:
    """(Re)carrega paths e configs a partir de um root_dir."""
    global PROJECT_DIR, E5_JSON_PATH
    global FAMILY_CONFIG_PATH, SCORING_CONFIG_PATH, PIPELINE_CONFIG_PATH
    global REPORT_SPEC_PATH, OUTPUT_DIR
    global _SCORING_CONFIG, _PIPELINE_CONFIG, _QA_THRESHOLDS, _REPORT_LAYOUT

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
    _REPORT_LAYOUT = _load_report_layout()


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
_REPORT_LAYOUT: dict = _load_report_layout()


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
    # ADR-333: espelhar EXATAMENTE a fórmula do motor (RatiosCalculator) — janela 12m +
    # despesa_consumo (aporte fora). Antes usava despesa_total full-window → falso-negativo crônico.
    src = fluxo.get("janela_12m") or fluxo
    rec_recorrente = src.get("receita_recorrente", 0)
    despesa = src.get("despesa_consumo", src.get("despesa_total", 0))
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
    # casa o campo do if_pct (investivel_efetivo, analyze_finances.py:1197) — A36.l3
    pat_investivel = pat.get("investivel_efetivo", 0)
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


# Denominador é o inventário do CONSUMIDOR (layout), não do produtor. Lê o
# YAML — não o módulo Python gerado (importá-lo acoplaria pipeline→backend).
#
# ``summary: true`` é o que faz o "entregues=N" ser honesto: a flag é o
# inventário de render sites, e a correspondência flag ⟺
# ``<SectionSummary sectionId="…">`` é enforçada em PR pela regra 6 de
# ``dev/check_chart_conclusion_parity.py``. Sem essa premissa o CV9 mediria só
# produtor × mapa (o join), enquanto o nome prometia render.
def _summary_render_destinations() -> dict[str, str]:
    """``{section_id: summary_source}`` das entradas que REALMENTE renderizam."""
    return {
        e["id"]: e["summary_source"]
        for e in _summary_entries()
        if e.get("enabled") and e.get("summary") and e.get("summary_source")
    }


def _summary_entries() -> list[dict]:
    estrategico = (_REPORT_LAYOUT or {}).get("estrategico") or {}
    entries = [*(estrategico.get("sections") or []), *(estrategico.get("appendices") or [])]
    return [e for e in entries if isinstance(e, dict)]


def _summary_source_sem_render() -> dict[str, str]:
    """Destinos declarados em entrada que não exibe parágrafo — gerado e não entregue."""
    return {
        e["id"]: e["summary_source"]
        for e in _summary_entries()
        if e.get("summary_source") and not (e.get("enabled") and e.get("summary"))
    }


def _delivered(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


# Render site existir não é o mesmo que o parágrafo aparecer. A S9 curto-circuita
# em ``<EmptyState/>`` quando o ``bubble_riscos`` vem ``data_state: "empty"`` e
# NÃO imprime o ``s9`` nesse ramo — a mensagem já é o empty state (ADR-356 §D7).
# A primeira versão do CV9 devolvia ``entregues=7/7`` num run que renderizava 6:
# ela media produtor × mapa, e o 4º predicado só olhava flags ESTÁTICAS do
# layout, cegas a supressão condicional.
#
# O gate é declarado no layout (``summary_suppressed_by``) e a regra 7 de
# ``dev/check_chart_conclusion_parity.py`` exige a correspondência com o
# ``<SectionSummary>`` condicionado no TSX, nas duas direções — sem isso a
# declaração derivaria do código em silêncio.
def _suppressed_destinations(e5: dict, destinos: dict[str, str]) -> dict[str, str]:
    """Destinos que ESTE run não entrega porque a seção está em empty state."""
    charts = (e5.get("narrativas") or {}).get("charts") or {}
    out = {}
    for entry in _summary_entries():
        gate = entry.get("summary_suppressed_by")
        sid = entry.get("id")
        if not gate or sid not in destinos:
            continue
        chart = charts.get(gate)
        if isinstance(chart, dict) and chart.get("data_state") == "empty":
            out[sid] = destinos[sid]
    return out


# CV9 mede o que o renderer consegue EXIBIR, não o que o produtor gerou.
# Presença + não-vazio de ``s1..s10`` já é hard-fail de ``validate_narrativas``
# a montante, então o CV9 antigo era verde por construção. As quatro direções
# aqui não tinham gate nenhum: (1) destino declarado no layout sem texto
# (layout aponta ``s11``, ou produtor renomeia chave ⇒ parágrafo vazio em
# silêncio); (2) chave emitida sem destino e sem razão na allowlist de órfãs;
# (3) shape inválido — ``{context, conclusion}`` sob ``summaries.sN`` passa
# pelo ``validate_narrativas`` e cai no fallback derivado sem sinal; (4)
# destino mapeado numa seção que não exibe parágrafo (``summary: false`` ou
# ``enabled: false``) — texto gerado, mapeado e invisível, a direção que o nome
# "delivery" prometia e nenhuma perna cobria.
def _delivery_failures(summaries: dict, destinos: dict[str, str]) -> dict[str, list[str]]:
    """Os quatro predicados de FALHA, cada um com as chaves ofensoras."""
    from pipeline.domain.services.narrativas import ORPHAN_SUMMARY_KEYS

    esperadas = set(destinos.values())
    sem_render = _summary_source_sem_render()
    return {
        "sem_texto": sorted(k for k in esperadas if k not in summaries),
        "shape_invalido": sorted(
            k for k in esperadas if k in summaries and not _delivered(summaries[k])
        ),
        "orfas": sorted(
            set(summaries) - esperadas - set(sem_render.values()) - set(ORPHAN_SUMMARY_KEYS)
        ),
        "sem_render": sorted(f"{sid}->{key}" for sid, key in sem_render.items()),
    }


# ``suprimido`` sai do NUMERADOR mas não reprova: a supressão é a decisão de
# produto da §D7 (o empty state é a mensagem), não um defeito. Reprovar deixaria
# o CV9 vermelho em todo workspace sem risco cadastrado — trocaria um verde
# decorativo por um vermelho decorativo. O que o nome "entregues" promete é o
# número que o render produz, e é esse que sai: 6/7 quando a S9 suprime.
# Contagem por SEÇÃO (não por chave): o denominador é o inventário de render
# sites, e duas seções podem, em teoria, declarar o mesmo `summary_source`.
def _nao_entregues(
    destinos: dict[str, str], fail: dict[str, list[str]], suprimido: dict[str, str]
) -> set[str]:
    """Seções cujo parágrafo não chegou ao render neste run."""
    sem_texto_ou_shape = set(fail["sem_texto"]) | set(fail["shape_invalido"])
    return {sid for sid, key in destinos.items() if key in sem_texto_ou_shape} | set(suprimido)


def _cv9_summaries_delivery(e5: dict) -> CrossValidationResult:
    """CV9 — ENTREGA das narrativas de seção (A40.l4 · ADR-356 §D6)."""
    summaries = (e5.get("narrativas") or {}).get("summaries") or {}
    destinos = _summary_render_destinations()
    fail = _delivery_failures(summaries, destinos)
    suprimido = _suppressed_destinations(e5, destinos)
    entregues = len(destinos) - len(_nao_entregues(destinos, fail, suprimido))
    detalhe = {**fail, "suprimido": sorted(f"{k}->{v}" for k, v in suprimido.items())}
    passed = not any(fail.values())
    return CrossValidationResult(
        "CV9",
        "Narrativas delivery (destino declarado × render site do layout)",
        "info" if passed else "error",
        passed,
        f"entregues={entregues}/esperadas={len(destinos)}; "
        + "; ".join(f"{k}={v or 'nenhuma'}" for k, v in detalhe.items()),
        ["narrativas"],
    )


_REQUIRED_CHARTS = [
    "score_gauge",
    "patrimonio_doughnut",
    "alocacao_atual_vs_alvo",
    "fluxo_mensal",
    "receita_bar",
    "receita_despesa_mensal",
    "despesas_doughnut",
]


def _chart_incomplete(charts: dict, chart_id: str) -> bool:
    cv = charts.get(chart_id)
    return isinstance(cv, dict) and (not cv.get("context") or not cv.get("conclusion"))


def _cv10_charts_completeness(e5: dict) -> CrossValidationResult:
    narr = e5.get("narrativas", {})
    charts = narr.get("charts", {})
    missing_charts = [c for c in _REQUIRED_CHARTS if c not in charts]
    # Completude só dos obrigatórios: charts opcionais (impostos_pj,
    # wise_fiscal_flags…) são legitimamente vazios sem a seção (A36.l3 FU-1).
    incomplete_charts = [c for c in _REQUIRED_CHARTS if _chart_incomplete(charts, c)]
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


def _cv16_receita_natureza(e5: dict) -> CrossValidationResult | None:
    # ADR-330: baldes explícitos (pj/clt/aluguel) do bloco receita_por_natureza não podem
    # exceder receita_total — resíduo negativo = dupla-contagem. Cents inteiros, tolerância
    # zero. (CV15 reservado pela ADR-327.)
    fluxo = e5.get("fluxo_caixa", {})
    nat = fluxo.get("receita_por_natureza")
    if not nat:
        return None

    def _c(v: object) -> int:
        return int(round(float(v or 0) * 100))

    explicit = (
        _c(nat.get("receita_pj")) + _c(nat.get("receita_clt")) + _c(nat.get("receita_aluguel"))
    )
    total = _c(fluxo.get("receita_total"))
    passed = explicit <= total
    return CrossValidationResult(
        "CV16",
        "Conservação receita_por_natureza",
        "info" if passed else "error",
        passed,
        f"pj+clt+aluguel ({explicit / 100:,.2f}) <= receita_total ({total / 100:,.2f})",
        ["fluxo_caixa"],
    )


def _cents(value: object) -> int:
    # ADR-090: Decimal via str(v) no call-site — nunca float em comparação monetária.
    return int((Decimal(str(value or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# A37.l7 (CTO-01 + PR-2): conservação da renda passiva observada — pós-shape
# auto-conservativo o dict de fontes contém SÓ yield recorrente (excluídos por
# design — ADR-191/ADR-336 — vivem em irmãos explícitos fora do dict), então
# Σ(fontes) == headline sem subtração. Um componente excluído re-injetado no
# dict (shape antigo) quebra a igualdade → error. Cents inteiros via Decimal,
# tolerância zero — simétrico ao CV16.
def _cv17_renda_passiva_conservacao(e5: dict) -> CrossValidationResult | None:
    pi = e5.get("passive_income")
    fontes = (pi or {}).get("renda_passiva_por_fonte_brl")
    if not fontes:
        return None
    esperado = sum(_cents(v) for v in fontes.values())
    headline = _cents(pi.get("renda_passiva_anual_brl"))
    passed = esperado == headline
    return CrossValidationResult(
        "CV17",
        "Conservação renda passiva",
        "info" if passed else "error",
        passed,
        f"Σ(fontes) ({esperado / 100:,.2f}) == renda_passiva_anual_brl ({headline / 100:,.2f})",
        ["passive_income"],
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
    _cv16_receita_natureza,
    _cv17_renda_passiva_conservacao,
)
# Classe de RENDER: só avaliável se as narrativas chegaram ao E5. Sem elas,
# `generate_narratives` degradou (A40.l18 · ADR-357) e rodar estes checks
# conflacionaria "a narrativa não veio" com "regressão de render" — o E5 não
# carrega discriminador nenhum entre as duas causas.
_CV_RENDER_CHECKS = (
    _cv9_summaries_delivery,
    _cv10_charts_completeness,
    _cv14_monetary_format,
)
_CV_ALWAYS_CHECKS = (
    _cv11_tarefas_structure,
    _cv12_diagnostico,
    _cv13_score_label,
)

# Checks numéricos de conservação que PAUSAM o run como needs_review quando
# falham (A36.l3). Gatilhar por check-id, NÃO por severity=="error": CV9/CV10
# são `error` mas de render (narrativa/gráfico ausente) e falham em run
# incremental que reusa narrativa — gatilhar neles pausaria 100% dos runs.
# Medição sobre 27 runs de dogfood: 0 pausas neste conjunto. Ver ADR-272 §Emenda.
_CONSERVATION_CHECKS: frozenset[str] = frozenset({"CV1", "CV2", "CV3", "CV6"})


def _conservation_validation(cv_results: list[CrossValidationResult]) -> dict:
    """Bloco ``validation`` lido por ``_has_validation_errors``: pausa o run se um
    check de conservação falhou. Render (CV9/CV10) fica advisory, fora do gate."""
    failures = [r for r in cv_results if not r.passed and r.check_id in _CONSERVATION_CHECKS]
    return {
        "valid": not failures,
        "errors": [f"[{r.check_id}] {r.name}: {r.details}" for r in failures],
    }


def has_narrativas(e5: dict) -> bool:
    """Narrativas chegaram ao E5 — predicado de avaliabilidade da classe de render."""
    narr = e5.get("narrativas") or {}
    return bool(narr.get("summaries")) and bool(narr.get("charts"))


def run_cross_validation(e5: dict) -> list[CrossValidationResult]:
    """Run all deterministic cross-validation checks on E5 data."""
    results: list[CrossValidationResult] = []
    for check in _CV_OPTIONAL_CHECKS:
        result = check(e5)
        if result is not None:
            results.append(result)
    if has_narrativas(e5):
        results.extend(check(e5) for check in _CV_RENDER_CHECKS)
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
    """Roda os checks CV1–CV17 (CV15 reservado) sobre o E5 do workspace.

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

    e5 = store.read("analyze_finances", "analise_financeira") or {}
    if not e5:
        print("  [ERRO] E5 artifact 'analise_financeira' não encontrado.")
        return {"success": False, "reason": "e5_not_found"}

    # A40.l18 · ADR-357 §Delta item 4 — o early-return `missing_narrativas` foi
    # REMOVIDO. Ele transformava a degradação de `generate_narratives` numa
    # segunda lacuna: derrubava o E7 (e, com `stop_on_error=True` default,
    # também o parecer, que vem depois em FULL_ORDER) e apagava a row em
    # `reports`. A conservação não depende de narrativa nenhuma — só a classe
    # de render depende, e essa agora skipa.
    render_avaliado = has_narrativas(e5)
    if render_avaliado:
        print(f"  ✓ E5 JSON: {len(e5)} top-level keys, narrativas presentes")
    else:
        print("  [AVISO] E5 sem narrativas — classe de render (CV9/CV10/CV14) não avaliada.")

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
        # Sem isto, `checks_total` menor é indistinguível de "checks passaram":
        # quem ler o payload precisa saber que a classe de render não foi julgada.
        "render_avaliado": render_avaliado,
        "validation": _conservation_validation(cv_results),
        "results": [r.to_dict() for r in cv_results],
    }
