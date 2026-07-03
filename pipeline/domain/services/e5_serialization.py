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

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.services.if_projector import MonteCarloIFResult
from pipeline.domain.services.passive_income_calculator import PassiveIncomeResult

_logger = logging.getLogger("mathoms.pipeline.e5_serialization")

# Aliases para boundaries do output legacy (paridade com pattern de
# ``ratios_calculator.py`` — Mapping[str, Any] não dispara P3).
_GoalsPayload = Mapping[str, Any]
_FontesPayload = Mapping[str, Decimal]

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
        warnings.append(
            SanityWarning(
                "patrimonio.bruto",
                f"Patrimônio bruto negativo: R$ {pat_bruto:,.2f}",
            )
        )

    receita_total = _coerce_number(fluxo.get("receita_total", 0))
    if receita_total < 0:
        warnings.append(
            SanityWarning(
                "fluxo.receita_total",
                f"Receita total negativa: R$ {receita_total:,.2f}",
            )
        )

    despesa_total = _coerce_number(fluxo.get("despesa_total", 0))
    if despesa_total < 0:
        warnings.append(
            SanityWarning(
                "fluxo.despesa_total",
                f"Despesa total negativa: R$ {despesa_total:,.2f}",
            )
        )

    taxa_poup = ratios.get("taxa_poupanca_recorrente_pct", 0)
    if not isinstance(taxa_poup, str):
        t = _coerce_number(taxa_poup)
        if t < -100 or t > 100:
            warnings.append(
                SanityWarning(
                    "ratios.taxa_poupanca_recorrente_pct",
                    f"Taxa poupança fora do range [-100%, 100%]: {t:.1f}%",
                )
            )

    if_pct = _coerce_number(goals.get("if_pct", 0))
    if if_pct < 0:
        warnings.append(
            SanityWarning(
                "goals.if_pct",
                f"IF progresso negativo: {if_pct:.1f}%",
            )
        )

    endiv = ratios.get("taxa_endividamento_pct", 0)
    if not isinstance(endiv, str):
        e = _coerce_number(endiv)
        if e > 200:
            warnings.append(
                SanityWarning(
                    "ratios.taxa_endividamento_pct",
                    f"Endividamento acima de 200%: {e:.1f}%",
                )
            )

    score_val = _coerce_number(score.get("valor", 0))
    if score_val < 0 or score_val > 10:
        warnings.append(
            SanityWarning(
                "score.valor",
                f"Score fora do range [0, 10]: {score_val}",
            )
        )

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


def build_alertas(
    score: dict[str, Any],
    ratios: dict[str, Any],
    investimentos_warnings: list[str] | None = None,
) -> list[str]:
    """Monta lista de alertas para o template JS + warnings de classificação de
    ativos (ADR-193). Curadoria A28.l10: o alerta "Score financeiro: X/10" era
    circular (só referencia o próprio score, já exibido no gauge) — não é mais
    emitido; lista vazia é empty state honesto."""
    # `score` fica na assinatura por compat de call-site (A28.l10).
    _ = score
    alertas: list[str] = []
    if ratios.get("rentabilidade_pct") == "N/D":
        alertas.append("Rentabilidade: N/D")
    suspeito_alerta = _alerta_trs_suspeita(ratios)
    if suspeito_alerta:
        alertas.append(suspeito_alerta)
    if investimentos_warnings:
        alertas.extend(investimentos_warnings)
    return alertas


def _alerta_trs_suspeita(ratios: Mapping[str, Any]) -> str | None:
    """Guardrail A28.l2 — TRS suspeita nunca publica silencioso (ADR-191)."""
    nested = ratios.get("rentabilidade")
    if not isinstance(nested, dict) or nested.get("status") != "suspeito":
        return None
    valor = nested.get("valor_pct")
    prefixo = f"TRS efetiva {valor:.2f}% a.a." if isinstance(valor, (int, float)) else "TRS efetiva"
    return (
        f"{prefixo} acima do plausível para yield de carteira — revisar composição "
        "das fontes de renda passiva e do patrimônio gerador antes de usar o número."
    )


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
    programa_milhas: dict[str, Any] | None = None
    tarefas: list[dict[str, Any]] | None = None
    tarefas_status: dict[str, str] | None = None
    existing_narrativas: dict[str, Any] | None = None
    # E1.6 (extract_irpf_full) — try-read opcional. Quando ausente, output
    # omite a chave `irpf_kpis` (workspaces sem IRPF). ADR-157.
    irpf_kpis: dict[str, Any] | None = None
    # A8.3 — KPIs de TRS efetiva + carteira de renda. Quando ``status == "ok"``,
    # ``goals`` é enriquecido com 7 chaves (taxa_retirada_efetiva_pct, …).
    # Status ``"sem_irpf"``/``"gerador_zero"`` não enriquece — UI lida via
    # ``passive_income`` no top-level (chave separada).
    passive_income: PassiveIncomeResult | None = None
    # N3 — Monte Carlo IF cone P10/P50/P90. None quando if_projection indisponível.
    monte_carlo_if: MonteCarloIFResult | None = None
    # ADR-193 — warnings de classificação de ativos (e.g. `Outros` > 5%).
    # Propagado para `alertas[]` via `build_alertas`.
    investimentos_warnings: list[str] | None = None
    # ADR-219 wave 2 — snapshot das premissas econômicas vigentes na data
    # do run (auditoria fiduciária). None quando resolver indisponível
    # (CLI/testes legados); ausência no output deixa UI degradar.
    premissas_economicas: dict[str, Any] | None = None
    # Bloco G plan RESIDENCIA_E_USO — exposição cambial (caixa USD/EUR +
    # ativos com lastro internacional ADR-193). None quando analyzer não
    # foi injetado (CLI legado/testes pré-G).
    exposicao_cambial: dict[str, Any] | None = None
    # ADR-279 (A24.l5) — bloco ``_lineage`` field-level (patrimônio no
    # skeleton). None quando o adapter não produziu (testes legados).
    lineage: dict[str, Any] | None = None
    # A17 L4 (ADR-238 §L4) — yield-on-cost por (ticker, ano_base) dos
    # informes proventos_acoes. None/empty omite a chave no output.
    proventos_por_ativo: tuple | None = None


def build_e5_output(inputs: E5OutputInputs) -> dict[str, Any]:
    """Monta o dict final ``analise_financeira-5_analysis.json``.

    Paridade linha-a-linha com ``e5_analyze.main()`` 2525-2560. Quando
    ``tarefas``/``tarefas_status`` são ``None`` ou vazios, usa o fallback
    derivado de ``pontos_urgentes``. Se ``existing_narrativas`` é
    fornecido, preserva-o no output (padrão E5.N que adiciona depois).
    """
    tarefas = inputs.tarefas if inputs.tarefas else build_default_tarefas(inputs.pontos_urgentes)
    tarefas_status = (
        inputs.tarefas_status
        if inputs.tarefas_status
        else build_default_tarefas_status(inputs.pontos_urgentes)
    )

    alertas = build_alertas(inputs.score, inputs.ratios, inputs.investimentos_warnings)

    goals_enriched = _enrich_goals_with_passive_income(inputs.goals, inputs.passive_income)

    output: dict[str, Any] = {
        "periodo_dados": inputs.periodo_dados,
        "data_analise": inputs.data_analise,
        "patrimonio": inputs.patrimonio,
        "goals": goals_enriched,
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
        "cenarios_conjuge": inputs.cenarios_conjuge,
        "programa_milhas": inputs.programa_milhas or {},
    }
    if inputs.exposicao_cambial is not None:
        output["exposicao_cambial"] = inputs.exposicao_cambial

    # ADR-279: lineage field-level inline — aditivo, declarado no schema E5.
    if inputs.lineage is not None:
        output["_lineage"] = inputs.lineage

    # ADR-166: chave estável universal — confirma em prod que payload migrou.
    _logger.info(
        "e5.cenarios_key",
        extra={"key": "cenarios_conjuge", "has_data": bool(inputs.cenarios_conjuge)},
    )

    # Preserva narrativas (E5.N enriquece em run posterior).
    if inputs.existing_narrativas is not None:
        output["narrativas"] = inputs.existing_narrativas

    # ADR-157: KPIs do IRPF aparecem no output só quando E1.6 produziu artefato.
    if inputs.irpf_kpis is not None:
        output["irpf_kpis"] = inputs.irpf_kpis

    # A17 L4: yield-on-cost por ativo (S3 "viver de renda" — Perini).
    if inputs.proventos_por_ativo:
        output["proventos_por_ativo"] = [
            _proventos_summary_to_dict(s) for s in inputs.proventos_por_ativo
        ]

    # A8.3: top-level ``passive_income`` para UI ler status + 6 fontes
    # mesmo nos casos de empty state (status ``sem_irpf``/``gerador_zero``).
    if inputs.passive_income is not None:
        output["passive_income"] = _passive_income_to_dict(inputs.passive_income)

    # ADR-219 wave 2: snapshot de premissas econômicas vigentes no run.
    # Quando o resolver não está injetado (CLI/testes), o chamador passa
    # None e a chave é omitida — UI degrada para "premissas não disponíveis".
    if inputs.premissas_economicas is not None:
        output["premissas_economicas"] = inputs.premissas_economicas

    # N3: Monte Carlo IF — cone P10/P50/P90 + caminhos ano→BRL.
    if inputs.monte_carlo_if is not None:
        mc = inputs.monte_carlo_if
        output["if_monte_carlo"] = {
            "p10_ano_if": mc.p10_ano_if,
            "p50_ano_if": mc.p50_ano_if,
            "p90_ano_if": mc.p90_ano_if,
            "prob_if_ate_idade_meta": mc.prob_if_ate_idade_meta,
            "idade_meta_usada": mc.idade_meta_usada,
            "sigma_usado": mc.sigma_usado,
            "exibir_cone": mc.exibir_cone,
            "aporte_mensal_usado": float(mc.aporte_mensal_usado),
            "motivo_sem_cone": mc.motivo_sem_cone,
            "caminho_p10": [list(p) for p in mc.caminho_p10],
            "caminho_p50": [list(p) for p in mc.caminho_p50],
            "caminho_p90": [list(p) for p in mc.caminho_p90],
        }

    return output


# =============================================================================
# A8.3 — TRS efetiva (Lane A8.3 PR-C)
# =============================================================================


def _enrich_goals_with_passive_income(
    goals: _GoalsPayload, passive_income: PassiveIncomeResult | None
) -> _GoalsPayload:
    """Adiciona 7 KPIs de TRS efetiva ao ``goals`` quando status ``"ok"``."""
    if passive_income is None or passive_income.status != "ok":
        return dict(goals or {})
    enriched = dict(goals or {})
    enriched["taxa_retirada_efetiva_pct"] = float(passive_income.trs_efetiva_pct)
    enriched["renda_passiva_anual_observada_brl"] = float(passive_income.renda_passiva_anual_brl)
    enriched["renda_passiva_mensal_observada_brl"] = float(passive_income.renda_passiva_mensal_brl)
    enriched["patrimonio_gerador_brl"] = float(passive_income.patrimonio_gerador_brl)
    enriched["acumuladores_pct_gerador"] = float(passive_income.acumuladores_pct_gerador)
    enriched["ano_referencia_irpf"] = passive_income.ano_referencia_irpf
    enriched["defasagem_meses"] = passive_income.defasagem_meses
    enriched["janela"] = _janela_irpf(passive_income.ano_referencia_irpf)
    enriched["janela_meses"] = 12
    return enriched


def _proventos_summary_to_dict(s) -> _GoalsPayload:
    """Wire JSON number (ADR-090 §consequências): Decimal → float só na borda."""
    return {
        "ticker": s.ticker,
        "ano_base": s.ano_base,
        "total_proventos_brl": float(s.total_proventos_brl),
        "ir_retido_brl": float(s.ir_retido_brl),
        "custo_total_brl": float(s.custo_total_brl) if s.custo_total_brl is not None else None,
        "yield_on_cost_pct": (
            float(s.yield_on_cost_pct) if s.yield_on_cost_pct is not None else None
        ),
    }


def _janela_irpf(ano_referencia: int | None) -> str:
    """Rótulo de janela para mensalizações fiscais (ADR-306 §D1 família iii)."""
    return f"irpf_{ano_referencia}" if ano_referencia is not None else "irpf"


def _passive_income_to_dict(pi: PassiveIncomeResult) -> _GoalsPayload:
    """Serializa ``PassiveIncomeResult`` para o JSON top-level (UI consome)."""
    return {
        "status": pi.status,
        "renda_passiva_anual_brl": float(pi.renda_passiva_anual_brl),
        "renda_passiva_mensal_brl": float(pi.renda_passiva_mensal_brl),
        "renda_passiva_por_fonte_brl": _decimals_to_float(pi.renda_passiva_por_fonte_brl),
        "patrimonio_gerador_brl": float(pi.patrimonio_gerador_brl),
        "trs_efetiva_pct": float(pi.trs_efetiva_pct),
        "ano_referencia_irpf": pi.ano_referencia_irpf,
        "defasagem_meses": pi.defasagem_meses,
        "acumuladores_pct_gerador": float(pi.acumuladores_pct_gerador),
        "janela": _janela_irpf(pi.ano_referencia_irpf),
        "janela_meses": 12,
    }


def _decimals_to_float(d: _FontesPayload) -> dict[str, float]:
    return {k: float(v) for k, v in d.items()}
