"""Stage wrapper for E7-review — LLM-powered holistic financial review."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger(__name__)


def _load_json_file(data: dict | None) -> str:
    """Serialize an artifact dict to JSON string, or empty placeholder when absent."""
    if data is None:
        return "{}"
    return json.dumps(data, ensure_ascii=False, indent=2)[:60_000]


# Chaves do E5 que importam para o review holístico.
# Tabelas mensais, lista de transações, 41 tarefas e programa de milhas são
# descartados — o consultor decide com base em indicadores agregados.
_E5_COMPACT_TOP_KEYS = (
    "periodo_dados",
    "data_analise",
    "goals",
    "ratios",
    "score",
    "pontos_fortes",
    "pontos_urgentes",
    "alertas",
    "equilibrio_cerbasi",
    "previdencia_pgbl",
    "diagnostico_comportamental",
)

# Subset de chaves para dicts grandes — o resto é agregado redundante.
_E5_SUBKEYS = {
    "patrimonio": ("bruto", "dividas", "liquido", "investivel", "composicao"),
    "fluxo_caixa": (
        "receita_total",
        "receita_recorrente_mensal",
        "despesa_total",
        "despesa_mensal_media",
        "fluxo_liquido",
        "despesas_por_categoria",
    ),
    "reserva_emergencia": (
        "despesas_mensais",
        "cobertura_meses",
        "total_liquida",
        "avaliacao_liquidity",
    ),
    "endividamento": ("total_dividas", "percentual_patrimonio", "dividas"),
    "investimentos": ("total", "tabela_classes"),
    "consumo_consciente": ("folga_mensal", "folga_pct", "analise"),
    "cenarios_mariana": ("labels", "prazos_if", "anos_if", "premissas"),
    "narrativas": ("perfil_familia", "strategic_insights", "inconsistencies_review"),
}


def _build_compact_e5(e5_data: dict) -> dict:
    """Projeta o E5 para os campos que o consultor LLM realmente usa.

    Reduz o payload de ~60k para ~10k chars — menos input tokens, menos latência,
    sem perda analítica relevante (tabelas mês-a-mês e listas de tarefas não agregam
    valor ao review holístico)."""
    compact: dict = {}
    for key in _E5_COMPACT_TOP_KEYS:
        if key in e5_data:
            compact[key] = e5_data[key]
    for key, subkeys in _E5_SUBKEYS.items():
        section = e5_data.get(key)
        if isinstance(section, dict):
            compact[key] = {k: section[k] for k in subkeys if k in section}
    return compact


def _load_e5_compact(data: dict | None) -> str:
    """Project the E5 artifact to its compact form and serialize it."""
    if data is None:
        return "{}"
    compact = _build_compact_e5(data)
    return json.dumps(compact, ensure_ascii=False, indent=2)


def _output_to_review_json(output) -> dict:
    """Convert E7ReviewOutput to the format consumed by E7-apply and the report."""
    insights = []
    for ins in output.insights:
        entry = {
            "categoria": ins.category,
            "severidade": ins.severity,
            "titulo": ins.title,
            "descricao": ins.description,
        }
        if ins.recommendation:
            entry["recomendacao"] = ins.recommendation
        insights.append(entry)

    score_adj = []
    for adj in output.score_adjustments:
        entry = {
            "fator": adj.factor,
            "ajuste": adj.adjustment,
            "razao": adj.reason,
        }
        if adj.original_value is not None:
            entry["valor_original"] = adj.original_value
        score_adj.append(entry)

    narratives = {}
    for ns in output.narrative_sections:
        narratives[ns.section_key] = {
            "titulo": ns.title,
            "conteudo": ns.content,
        }

    return {
        "insights": insights,
        "recomendacoes": output.recommendations,
        "ajustes_score": score_adj,
        "narrativas": narratives,
        "avaliacao_geral": output.overall_assessment,
        "nivel_risco": output.risk_level,
        "_meta": {
            "source": "E7-review-llm",
            "confidence": output.confidence,
        },
    }


def run(ctx: WorkspaceContext) -> dict:
    """Execute E7-review holistic financial analysis via LLM.

    Reads E5 analysis JSON and E7-crossval results, sends to LLM,
    saves review JSON in E7_review/.
    """
    from pipeline.llm.litellm_client import LLMConfig, LLMService
    from pipeline.llm.prompts.e7_review import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from pipeline.llm.schemas.e7_review import E7ReviewOutput

    llm_config_data = ctx.load_config("llm_config.json")
    if not llm_config_data or not llm_config_data.get("api_key"):
        return {"skipped": True, "reason": "No LLM config — free tier"}

    e5_path = ctx.e5_dir / "analise_financeira-5_analysis.json"
    if not e5_path.exists():
        return {"skipped": True, "reason": "E5 analysis not found — run E5 first"}

    e5_json = _load_e5_compact(e5_path)

    crossval_files = list(ctx.e7_dir.glob("*crossval*")) if ctx.e7_dir.exists() else []
    e7_crossval_json = "{}"
    if crossval_files:
        e7_crossval_json = _load_json_file(crossval_files[0])

    family_config = ctx.load_config("family_members.json")
    family_config_str = (
        json.dumps(family_config, ensure_ascii=False, indent=2) if family_config else "{}"
    )

    # JSON aninhado pode conter `{`/`}` — em kwargs do str.format o valor é inserido literalmente.
    user_prompt = USER_PROMPT_TEMPLATE.format(
        e5_analysis_json=e5_json,
        e7_crossval_json=e7_crossval_json,
        family_config=family_config_str,
    )

    config = LLMConfig(**llm_config_data)
    service = LLMService(config)

    # max_tokens=16384 dimensionado para o pior caso do schema (ver schemas/e7_review.py):
    # 8 insights + 6 recs + 5 ajustes + 5 narrativas + assessment cabem com folga.
    # Evita o ciclo truncation → retry → dobra que custava ~3min por patamar.
    result = service.call(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=E7ReviewOutput,
        max_tokens=16384,
        stage="E7-review",
    )

    output: E7ReviewOutput = result.output
    review_json = _output_to_review_json(output)

    ctx.e7_dir.mkdir(parents=True, exist_ok=True)
    out_path = ctx.e7_dir / "review_llm-7_review.json"
    out_path.write_text(json.dumps(review_json, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(
        "E7-review: %d insights, %d recommendations, risk=%s, confidence=%.2f",
        len(output.insights),
        len(output.recommendations),
        output.risk_level,
        output.confidence,
    )

    return {
        "success": True,
        "insights_count": len(output.insights),
        "recommendations_count": len(output.recommendations),
        "score_adjustments": len(output.score_adjustments),
        "risk_level": output.risk_level,
        "confidence": output.confidence,
        "output_file": out_path.name,
        "tokens": {"in": result.tokens_in, "out": result.tokens_out},
        "cost_usd": result.cost_estimate_usd,
    }
