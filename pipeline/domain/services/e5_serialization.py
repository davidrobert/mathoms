"""Serialização para o output E5 legado (Sessão A5d · Fase 8).

Extrai helpers de montagem do output ``analise_financeira-5_analysis.json``
de ``scripts/e5_analyze.main()`` (linhas 2525-2560). Funções puras que
consomem os dicts já produzidos pelos `analyze_*` do legado (ou por
services extraídos equivalentes) e montam o JSON final.

Escopo A5d: cobrir o formato "key mapping" + sanity checks; manter paridade
textual com o output do ``main(root_dir)`` legado para o golden.

Funções puras, sem I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# =============================================================================
# Constantes de chave (paridade com legado)
# =============================================================================


E5_OUTPUT_STAGE = "E5"
E5_ARTIFACT_KEY = "analise_financeira"
E5_ARTIFACT_FILENAME = "analise_financeira-5_analysis.json"


# =============================================================================
# Sanity check
# =============================================================================


@dataclass(frozen=True)
class SanityWarning:
    """Aviso produzido por ``run_sanity_checks``."""

    field: str
    message: str


def run_sanity_checks(
    *,
    patrimonio: dict[str, Any],
    fluxo: dict[str, Any],
    ratios: dict[str, Any],
    goals: dict[str, Any],
    score: dict[str, Any],
) -> list[SanityWarning]:
    """Replica os 7 sanity checks do ``main()`` legado
    (e5_analyze.py:2489-2518)."""
    warnings: list[SanityWarning] = []

    pat_bruto = _coerce_number(patrimonio.get("bruto", 0))
    if pat_bruto < 0:
        warnings.append(SanityWarning(
            "patrimonio.bruto",
            f"Patrimônio bruto negativo: R$ {pat_bruto:,.2f}",
        ))

    receita_total = _coerce_number(fluxo.get("receita_total", 0))
    if receita_total < 0:
        warnings.append(SanityWarning(
            "fluxo.receita_total",
            f"Receita total negativa: R$ {receita_total:,.2f}",
        ))

    despesa_total = _coerce_number(fluxo.get("despesa_total", 0))
    if despesa_total < 0:
        warnings.append(SanityWarning(
            "fluxo.despesa_total",
            f"Despesa total negativa: R$ {despesa_total:,.2f}",
        ))

    taxa_poup = ratios.get("taxa_poupanca_recorrente_pct", 0)
    if not isinstance(taxa_poup, str):
        t = _coerce_number(taxa_poup)
        if t < -100 or t > 100:
            warnings.append(SanityWarning(
                "ratios.taxa_poupanca_recorrente_pct",
                f"Taxa poupança fora do range [-100%, 100%]: {t:.1f}%",
            ))

    if_pct = _coerce_number(goals.get("if_pct", 0))
    if if_pct < 0:
        warnings.append(SanityWarning(
            "goals.if_pct",
            f"IF progresso negativo: {if_pct:.1f}%",
        ))

    endiv = ratios.get("endividamento_pct", 0)
    if not isinstance(endiv, str):
        e = _coerce_number(endiv)
        if e > 200:
            warnings.append(SanityWarning(
                "ratios.endividamento_pct",
                f"Endividamento acima de 200%: {e:.1f}%",
            ))

    score_val = _coerce_number(score.get("valor", 0))
    if score_val < 0 or score_val > 10:
        warnings.append(SanityWarning(
            "score.valor",
            f"Score fora do range [0, 10]: {score_val}",
        ))

    return warnings


def _coerce_number(val: Any) -> float:
    if isinstance(val, bool):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


# =============================================================================
# Default tarefas (fallback a partir de pontos_urgentes)
# =============================================================================


def build_default_tarefas(pontos_urgentes: list[dict[str, Any]]) -> list[dict]:
    """Fallback quando ``parse_tarefas_md`` retorna vazio: monta tarefas a
    partir de ``pontos_urgentes``. Paridade com e5_analyze.py:2542-2545.
    """
    return [
        {
            "n": i + 1,
            "t": pu.get("acao", str(pu)),
            "p": pu.get("prioridade", "media").lower(),
            "e": pu.get("prazo", "—"),
            "impacto": pu.get("impacto", ""),
        }
        for i, pu in enumerate(pontos_urgentes or [])
    ]


def build_default_tarefas_status(pontos_urgentes: list[dict[str, Any]]) -> dict[str, str]:
    """Fallback: ``{str(i+1): "pendente"}`` para cada ponto urgente."""
    return {str(i + 1): "pendente" for i in range(len(pontos_urgentes or []))}


def build_alertas(score: dict[str, Any], ratios: dict[str, Any]) -> list[str]:
    """Monta lista de alertas para o template JS (paridade linha 2548-2550)."""
    alertas = [
        f"Score financeiro: {score.get('valor', 0)}/10 "
        f"({score.get('classificacao', '')})"
    ]
    if ratios.get("rentabilidade_pct") == "N/D":
        alertas.append("Rentabilidade: N/D")
    return alertas


# =============================================================================
# build_e5_output
# =============================================================================


@dataclass(frozen=True)
class E5OutputInputs:
    """Todos os sub-resultados que compõem o output final do E5.

    Convertendo o contrato grande do ``main()`` legado em um único
    container tipado para facilitar chamada + testes.
    """

    periodo_dados: str
    data_analise: str
    patrimonio: dict[str, Any]
    goals: dict[str, Any]
    fluxo: dict[str, Any]
    ratios: dict[str, Any]
    score: dict[str, Any]
    orcamento: dict[str, Any]
    reserva: dict[str, Any]
    endividamento: dict[str, Any]
    previdencia: dict[str, Any]
    pontos_fortes: list[dict[str, Any]]
    pontos_urgentes: list[dict[str, Any]]
    investimentos_classes: dict[str, Any]
    equilibrio_cerbasi: dict[str, Any]
    consumo: dict[str, Any]
    diagnostico: list[dict[str, Any]]
    cenarios_conjuge: dict[str, Any]
    cenarios_conjuge_key: str = "cenarios_conjuge"
    programa_milhas: dict[str, Any] | None = None
    tarefas: list[dict[str, Any]] | None = None
    tarefas_status: dict[str, str] | None = None
    existing_narrativas: dict[str, Any] | None = None


def build_e5_output(inputs: E5OutputInputs) -> dict[str, Any]:
    """Monta o dict final ``analise_financeira-5_analysis.json``.

    Paridade linha-a-linha com ``e5_analyze.main()`` 2525-2560. Quando
    ``tarefas``/``tarefas_status`` são ``None`` ou vazios, usa o fallback
    derivado de ``pontos_urgentes``. Se ``existing_narrativas`` é
    fornecido, preserva-o no output (padrão E5.N que adiciona depois).
    """
    tarefas = (
        inputs.tarefas
        if inputs.tarefas
        else build_default_tarefas(inputs.pontos_urgentes)
    )
    tarefas_status = (
        inputs.tarefas_status
        if inputs.tarefas_status
        else build_default_tarefas_status(inputs.pontos_urgentes)
    )

    alertas = build_alertas(inputs.score, inputs.ratios)

    output: dict[str, Any] = {
        "periodo_dados": inputs.periodo_dados,
        "data_analise": inputs.data_analise,
        "patrimonio": inputs.patrimonio,
        "goals": inputs.goals,
        "fluxo_caixa": inputs.fluxo,
        "ratios": inputs.ratios,
        "score": inputs.score,
        "orcamento_prospectivo": inputs.orcamento,
        "reserva_emergencia": inputs.reserva,
        "endividamento": inputs.endividamento,
        "previdencia_pgbl": inputs.previdencia,
        "pontos_fortes": inputs.pontos_fortes,
        "pontos_urgentes": inputs.pontos_urgentes,
        "investimentos": inputs.investimentos_classes,
        "equilibrio_cerbasi": inputs.equilibrio_cerbasi,
        "tarefas": tarefas,
        "tarefas_status": tarefas_status,
        "alertas": alertas,
        "consumo_consciente": inputs.consumo,
        "diagnostico_comportamental": inputs.diagnostico,
        inputs.cenarios_conjuge_key: inputs.cenarios_conjuge,
        "programa_milhas": inputs.programa_milhas or {},
    }

    # Preserva narrativas (E5.N enriquece em run posterior).
    if inputs.existing_narrativas is not None:
        output["narrativas"] = inputs.existing_narrativas

    return output
