"""Regras canônicas do SuggestionGenerator (ADR-153 / ADR-161).

Funções puras snapshot+config → SuggestionDraft|None. Uma função por
regra. Defensivas — snapshot incompleto retorna None silenciosamente.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any

from pipeline.domain.services.suggestion_config import SuggestionGeneratorConfig
from pipeline.domain.types.suggestion import SuggestionDraft

# =============================================================================
# Helpers de coerção (snapshot é Record<string, unknown> — defensivo)
# =============================================================================


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else []


def _as_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "."))
        except ValueError:
            return None
    return None


def _as_decimal(v: Any) -> Decimal | None:
    f = _as_float(v)
    if f is None:
        return None
    return Decimal(str(f)).quantize(Decimal("0.01"))


# =============================================================================
# Dedup buckets (toleram ruído sem perder gatilhos)
# =============================================================================


def _pct_bucket(pct: float, *, step: float) -> str:
    bucket = round(pct / step) * step
    return f"pct{bucket:.1f}"


def _meses_bucket(meses: float) -> str:
    if meses < 1:
        return "meses-lt1"
    if meses < 3:
        return "meses-1to3"
    if meses < 6:
        return "meses-3to6"
    return "meses-ge6"


def _brl_bucket(value: Decimal | None, *, step: Decimal) -> str:
    if value is None:
        return "brl-none"
    bucket = (value / step).quantize(Decimal("1")) * step
    return f"brl{bucket}"


def _dedup_key(kind: str, *, bucket: str) -> str:
    raw = f"{kind}|{bucket}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


# =============================================================================
# Regras v1 (ADR-153)
# =============================================================================


def rule_trs_desalinhada(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """TRS efetiva > alvo + 15% E progresso ≥ 50% (Perini/AUVP · A8.3 filtro de fase)."""
    goals = _as_dict(snapshot.get("goals"))
    trs_atual = _as_float(goals.get("taxa_retirada_efetiva_pct"))
    if trs_atual is None:
        return None
    progresso = _as_float(goals.get("if_pct")) or 0.0
    if progresso < 50.0:
        return None
    target = cfg.trs_target_pct
    threshold = target * (1 + cfg.trs_drift_tolerance_pct)
    if trs_atual <= threshold:
        return None
    sugestao = round(target, 1)
    title = f"Reduzir taxa de retirada para {sugestao:.1f}% ao ano"
    rationale = (
        f"Taxa de retirada efetiva está em {trs_atual:.1f}% — acima do alvo "
        f"conservador de {sugestao:.1f}% (Perini/AUVP). Ajustar para sustentar "
        f"a renda no longo prazo sem corroer principal."
    )
    return SuggestionDraft(
        section_id="S7",
        kind="trs_desalinhada",
        severity="warning",
        title=title,
        rationale=rationale,
        dedup_key=_dedup_key("trs_desalinhada", bucket=_pct_bucket(trs_atual, step=0.5)),
    )


def rule_reserva_insuficiente(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """Reserva < 6 meses (Perini/Cerbasi) — rationale enriquecido (Onda 10 #5)."""
    reserva = _as_dict(snapshot.get("reserva_emergencia"))
    meses = _as_float(reserva.get("meses_cobertura"))
    if meses is None or meses >= cfg.reserva_target_meses:
        return None
    gap_brl = _as_decimal(reserva.get("gap_brl"))
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    aporte_mensal = _as_decimal(fluxo.get("aporte_meta_mensal")) or _as_decimal(
        fluxo.get("aporte_medio_3m")
    )
    title = f"Reforçar reserva de emergência até {cfg.reserva_target_meses} meses"
    rationale = _build_reserva_rationale(meses, cfg.reserva_target_meses, gap_brl, aporte_mensal)
    severity = "danger" if meses < 3 else "warning"
    return SuggestionDraft(
        section_id="S2",
        kind="reserva_insuficiente",
        severity=severity,
        title=title,
        rationale=rationale,
        amount_brl=gap_brl,
        dedup_key=_dedup_key("reserva_insuficiente", bucket=_meses_bucket(meses)),
    )


def _build_reserva_rationale(
    meses_atual: float,
    meses_alvo: int,
    gap_brl: Decimal | None,
    aporte_mensal: Decimal | None,
) -> str:
    """Onda 10 #5 — rationale enriquecido com gap + ETA do aporte mensal."""
    base = (
        f"Sua reserva atual cobre {meses_atual:.1f} meses de custo essencial, "
        f"abaixo do alvo de {meses_alvo} meses (Perini/Cerbasi)."
    )
    if gap_brl is None or gap_brl <= 0:
        return base + " Reforçar protege o plano contra choque de renda."
    parts = [base, f"Faltam **{_format_brl(gap_brl)}**."]
    parts.append(_reserva_aporte_clause(gap_brl, aporte_mensal))
    return " ".join(p for p in parts if p)


def _reserva_aporte_clause(gap_brl: Decimal, aporte_mensal: Decimal | None) -> str:
    """ETA + CTA quando o aporte está disponível; texto curto caso contrário."""
    if aporte_mensal is None or aporte_mensal <= 0:
        return "Reforçar protege o plano contra choque de renda."
    meses = max(int((gap_brl / aporte_mensal).to_integral_value()), 1)
    aporte_brl = _format_brl(aporte_mensal)
    return (
        f"Aportando {aporte_brl}/mês, completa em ~{meses} meses. "
        f"**Próximo passo:** elevar aporte mensal para reserva ou direcionar "
        f"o próximo aporte de {aporte_brl} integralmente para Tesouro Selic / "
        "CDB liquidez diária."
    )


def rule_alocacao_fora_alvo(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """Pior desvio absoluto > 10pp do alvo (AUVP) — rationale enriquecido (Onda 10 #5)."""
    investimentos = _as_dict(snapshot.get("investimentos"))
    desvios = _as_list(investimentos.get("desvios_alvo"))
    pior = _pick_worst_desvio(desvios)
    if pior is None:
        return None
    desvio_pp = _as_float(pior.get("desvio_pp"))
    if desvio_pp is None or abs(desvio_pp) <= cfg.alocacao_drift_pp:
        return None
    classe = str(pior.get("classe", "alocação"))
    direcao = "reduzir" if desvio_pp > 0 else "aumentar"
    title = f"Rebalancear alocação: {direcao} {classe} ({desvio_pp:+.0f}pp)"
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    proximo_aporte = _as_decimal(fluxo.get("aporte_meta_mensal")) or _as_decimal(
        fluxo.get("aporte_medio_3m")
    )
    rationale = _build_alocacao_rationale(
        classe,
        desvio_pp,
        direcao,
        _as_float(pior.get("atual_pct")),
        _as_float(pior.get("alvo_pct")),
        proximo_aporte,
        desvios,
        cfg.alocacao_drift_pp,
    )
    return SuggestionDraft(
        section_id="S3",
        kind="alocacao_fora_alvo",
        severity="info",
        title=title,
        rationale=rationale,
        dedup_key=_dedup_key(
            "alocacao_fora_alvo",
            bucket=f"{classe}|{_pct_bucket(desvio_pp, step=2.5)}",
        ),
    )


def _pick_worst_desvio(desvios: list[Any]) -> dict[str, Any] | None:
    """Maior |desvio_pp| da lista; None se vazio."""
    if not desvios:
        return None
    pior = max(desvios, key=lambda d: abs(_as_float(_as_dict(d).get("desvio_pp")) or 0.0))
    return _as_dict(pior) or None


def _build_alocacao_rationale(
    classe: str,
    desvio_pp: float,
    direcao: str,
    atual_pct: float | None,
    alvo_pct: float | None,
    proximo_aporte: Decimal | None,
    desvios: list[Any],
    drift_pp: float,
) -> str:
    """Onda 10 #5 — head + drift + CTA + tabela markdown (cada parte opcional)."""
    head = _alocacao_head(classe, desvio_pp, direcao, atual_pct, alvo_pct)
    drift = f"Drift acima da tolerância ({drift_pp:.0f}pp)."
    cta = _alocacao_cta(classe, proximo_aporte)
    table = _format_alocacao_table(desvios)
    return "\n\n".join(p for p in (head, drift, cta, table) if p)


def _alocacao_cta(classe: str, proximo_aporte: Decimal | None) -> str:
    """CTA "Próximo aporte" — vazio quando o aporte mensal não está disponível."""
    if proximo_aporte is None or proximo_aporte <= 0:
        return ""
    return (
        f"**Próximo passo:** o próximo aporte de {_format_brl(proximo_aporte)} "
        f"pode ir integralmente para **{classe}** e iniciar o rebalanceamento."
    )


def _alocacao_head(
    classe: str,
    desvio_pp: float,
    direcao: str,
    atual_pct: float | None,
    alvo_pct: float | None,
) -> str:
    """Frase cabeçalho — anexa atual/alvo se disponível."""
    head = f"Classe **{classe}** está {abs(desvio_pp):.1f}pp {direcao}da do alvo"
    if atual_pct is not None and alvo_pct is not None:
        return head + f" (atual {atual_pct:.1f}% vs alvo {alvo_pct:.1f}%)."
    return head + "."


def _format_alocacao_table(desvios: list[Any]) -> str:
    """Tabela markdown atual/alvo/Δ — só se >=2 entradas com pcts."""
    rows: list[str] = []
    for entry in desvios:
        d = _as_dict(entry)
        atual = _as_float(d.get("atual_pct"))
        alvo = _as_float(d.get("alvo_pct"))
        desvio = _as_float(d.get("desvio_pp"))
        if atual is None or alvo is None or desvio is None:
            continue
        classe = str(d.get("classe", "—"))
        rows.append(f"| {classe} | {atual:.1f}% | {alvo:.1f}% | {desvio:+.1f}pp |")
    if len(rows) < 2:
        return ""
    header = "| Classe | Atual | Alvo | Δ |\n| --- | --- | --- | --- |"
    return "**Distribuição atual vs alvo:**\n\n" + header + "\n" + "\n".join(rows)


def _format_brl(value: Decimal) -> str:
    """Decimal monetário em formato BR (R$ 1.234,56) sem depender de locale."""
    quantized = value.quantize(Decimal("0.01"))
    formatted = f"{quantized:,.2f}"
    swapped = formatted.replace(",", "_TMP_").replace(".", ",").replace("_TMP_", ".")
    return f"R$ {swapped}"


def rule_aporte_abaixo_meta(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """Média 3m do aporte < 70% da meta (Perini/Cerbasi)."""
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    aporte_medio = _as_decimal(fluxo.get("aporte_medio_3m"))
    aporte_meta = _as_decimal(fluxo.get("aporte_meta_mensal"))
    if aporte_medio is None or aporte_meta is None or aporte_meta <= 0:
        return None
    pct = float(aporte_medio / aporte_meta)
    if pct >= cfg.aporte_min_pct_meta:
        return None
    gap = aporte_meta - aporte_medio
    rationale = (
        f"Aporte médio dos últimos 3 meses está em {pct * 100:.0f}% da meta — "
        f"abaixo do limiar de {cfg.aporte_min_pct_meta * 100:.0f}%. "
        f"Sem disciplina, o ano-IF projetado escorrega."
    )
    return SuggestionDraft(
        section_id="S2",
        kind="aporte_abaixo_meta",
        severity="warning",
        title="Retomar disciplina de aporte mensal",
        rationale=rationale,
        amount_brl=gap if gap > 0 else None,
        dedup_key=_dedup_key(
            "aporte_abaixo_meta",
            bucket=_brl_bucket(gap, step=Decimal("1000")),
        ),
    )


# FP-003 — `rule_dolarizacao_atrasada` removida (USA modo removido em ADR-168).
# Section_id "U1" não existe mais no relatório; regra produzia drafts órfãos.


# =============================================================================
# Regras v2 (ADR-161 — Cerbasi/AUVP/Perini completos)
# =============================================================================


CARRY_TRADE_MARGIN_PP: float = 1.0
"""Margem de segurança (pp) sobre o retorno esperado antes de disparar
carry-trade. Cerbasi (Equilíbrio Financeiro): 'dívida cara > retorno
esperado é destruição de patrimônio'. Margem evita falso-positivo
quando custo está marginalmente acima (ruído de medição/spread).
"""


def rule_endividamento_perigoso(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """Dívidas > 30% do bruto OU carry-trade (custo > retorno + 1pp · FP-009)."""
    endiv = _as_dict(snapshot.get("endividamento"))
    if not endiv:
        return None
    pct = _as_float(endiv.get("percentual_patrimonio"))
    custo = _as_float(endiv.get("custo_medio_pct_aa"))
    retorno = _as_float(_as_dict(snapshot.get("goals")).get("retorno_esperado_pct_aa"))
    triggered_pct = pct is not None and pct > cfg.endividamento_max_pct_patrimonio
    triggered_carry = (
        custo is not None and retorno is not None and custo > retorno + CARRY_TRADE_MARGIN_PP
    )
    if not (triggered_pct or triggered_carry):
        return None
    razao = _endividamento_rationale(cfg, pct, custo, retorno, triggered_pct, triggered_carry)
    return SuggestionDraft(
        section_id="S2",
        kind="endividamento_perigoso",
        severity="danger",
        title="Atacar dívidas antes de aportar mais",
        rationale=razao,
        amount_brl=_as_decimal(endiv.get("total_dividas")),
        dedup_key=_dedup_key(
            "endividamento_perigoso",
            bucket=f"{_pct_bucket(pct or 0, step=5)}|carry={triggered_carry}",
        ),
    )


def _endividamento_rationale(
    cfg: SuggestionGeneratorConfig,
    pct: float | None,
    custo: float | None,
    retorno: float | None,
    triggered_pct: bool,
    triggered_carry: bool,
) -> str:
    if triggered_pct and triggered_carry:
        return (
            f"Dívidas representam {pct:.0f}% do patrimônio bruto "
            f"(alvo ≤{cfg.endividamento_max_pct_patrimonio:.0f}%) **e** "
            f"custo médio ({custo:.1f}% a.a.) supera o retorno esperado "
            f"({retorno:.1f}% a.a. + {CARRY_TRADE_MARGIN_PP:.0f}pp de margem). "
            f"Carrego negativo composto."
        )
    if triggered_pct:
        return (
            f"Dívidas em {pct:.0f}% do patrimônio bruto — "
            f"acima do alvo ≤{cfg.endividamento_max_pct_patrimonio:.0f}% "
            f"(Cerbasi/AUVP). Risco de iliquidez em choque de renda."
        )
    return (
        f"Custo médio das dívidas ({custo:.1f}% a.a.) está acima do "
        f"retorno esperado ({retorno:.1f}% a.a. + {CARRY_TRADE_MARGIN_PP:.0f}pp "
        f"de margem). Patrimônio sangra silenciosamente — quitar é prioridade."
    )


def rule_taxa_poupanca_caindo(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """Taxa de poupança caiu >5pp por 2 trimestres consecutivos (Cerbasi)."""
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    historico = _as_list(fluxo.get("taxa_poupanca_trimestral_historico"))
    if len(historico) < cfg.taxa_poupanca_consecutive_quarters + 1:
        return None
    janela = [_as_float(v) for v in historico[-(cfg.taxa_poupanca_consecutive_quarters + 1) :]]
    if any(v is None for v in janela):
        return None
    if not _quedas_consecutivas(
        janela, cfg.taxa_poupanca_drop_pp_per_quarter, cfg.taxa_poupanca_consecutive_quarters
    ):
        return None
    primeiro, atual = janela[0], janela[-1]
    queda_total = primeiro - atual
    rationale = (
        f"Taxa de poupança caiu {queda_total:.1f}pp em "
        f"{cfg.taxa_poupanca_consecutive_quarters} trimestres consecutivos "
        f"(de {primeiro:.0f}% para {atual:.0f}%). Tendência comportamental — "
        f"Cerbasi alerta para revisão de orçamento e gatilhos de gasto antes "
        f"que vire estrutural."
    )
    return SuggestionDraft(
        section_id="S2",
        kind="taxa_poupanca_caindo",
        severity="warning",
        title="Investigar queda da taxa de poupança",
        rationale=rationale,
        dedup_key=_dedup_key("taxa_poupanca_caindo", bucket=_pct_bucket(atual, step=2.5)),
    )


def _quedas_consecutivas(serie: list[float], drop_pp: float, n_required: int) -> bool:
    consec = 0
    for i in range(1, len(serie)):
        if serie[i] < serie[i - 1] - drop_pp:
            consec += 1
        else:
            consec = 0
    return consec >= n_required


def rule_seguros_insuficientes(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """Renda PJ alta sem seguro vida/invalidez (Cerbasi · proteção)."""
    seguros = _as_dict(snapshot.get("seguros"))
    if not seguros:
        return None
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    renda_pj = _as_float(fluxo.get("renda_pj_mensal")) or _as_float(
        fluxo.get("receita_recorrente_mensal")
    )
    if renda_pj is None or renda_pj < cfg.seguros_renda_pj_threshold_brl:
        return None
    if seguros.get("vida_invalidez") is True:
        return None
    rationale = (
        f"Renda PJ mensal de R$ {renda_pj:,.0f} sem cobertura de "
        f"vida/invalidez detectada. Cerbasi: alta renda sem proteção é o "
        f"ponto cego mais comum em famílias de empresários. Choque de saúde "
        f"compromete o plano inteiro — seguro term é barato em relação ao "
        f"risco coberto."
    ).replace(",", ".")
    return SuggestionDraft(
        section_id="S6",
        kind="seguros_insuficientes",
        severity="danger",
        title="Contratar seguro de vida e invalidez",
        rationale=rationale,
        dedup_key=_dedup_key(
            "seguros_insuficientes",
            bucket=_brl_bucket(_as_decimal(renda_pj), step=Decimal("10000")),
        ),
    )


def rule_concentracao_instituicao(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """Algum banco com >40% do investível (AUVP)."""
    valores = _institutional_breakdown(snapshot)
    if not valores:
        return None
    total = sum(valores.values())
    if total <= 0:
        return None
    pior_banco, pior_valor = max(valores.items(), key=lambda kv: kv[1])
    pior_pct = (pior_valor / total) * 100
    if pior_pct <= cfg.concentracao_max_pct:
        return None
    rationale = (
        f"Instituição {pior_banco} concentra {pior_pct:.0f}% do patrimônio "
        f"investível — acima do limite AUVP de "
        f"{cfg.concentracao_max_pct:.0f}%. Risco institucional (intervenção, "
        f"default, custódia) é não-diversificável se concentrado em um único "
        f"custodian."
    )
    return SuggestionDraft(
        section_id="S3",
        kind="concentracao_instituicao",
        severity="warning",
        title=f"Diluir concentração em {pior_banco} ({pior_pct:.0f}% do investível)",
        rationale=rationale,
        dedup_key=_dedup_key(
            "concentracao_instituicao",
            bucket=f"{pior_banco}|{_pct_bucket(pior_pct, step=5)}",
        ),
    )


def _institutional_breakdown(snapshot: dict[str, Any]) -> dict[str, float]:
    patrimonio = _as_dict(snapshot.get("patrimonio"))
    investimentos = _as_dict(snapshot.get("investimentos"))
    raw = _as_dict(patrimonio.get("por_instituicao") or investimentos.get("por_instituicao"))
    valores: dict[str, float] = {}
    for banco, valor in raw.items():
        v = _as_float(valor)
        if v is not None and v > 0:
            valores[str(banco)] = v
    return valores


def rule_lifestyle_creep(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """Despesa essencial cresce >1.5x a inflação por 6m (Cerbasi/Perini)."""
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    historico = _as_list(fluxo.get("despesa_essencial_historico"))
    if len(historico) < cfg.lifestyle_creep_months:
        return None
    inflacao = _as_dict(snapshot.get("inflacao"))
    inflacao_pct = _as_float(inflacao.get("acumulada_pct_no_periodo"))
    if inflacao_pct is None:
        return None
    serie = [_as_float(v) for v in historico[-cfg.lifestyle_creep_months :]]
    if any(v is None or v <= 0 for v in serie):
        return None
    primeiro, ultimo = serie[0], serie[-1]
    crescimento_pct = (ultimo / primeiro - 1) * 100
    threshold = inflacao_pct * cfg.lifestyle_creep_inflation_multiplier
    if crescimento_pct <= threshold:
        return None
    excesso = crescimento_pct - inflacao_pct
    rationale = (
        f"Despesa essencial cresceu {crescimento_pct:.1f}% em "
        f"{cfg.lifestyle_creep_months} meses, contra {inflacao_pct:.1f}% de "
        f"inflação acumulada — excesso de {excesso:.1f}pp acima do esperado. "
        f"Cerbasi/Perini: aumento estrutural de custo essencial atrasa o "
        f"ano-IF mais que choque pontual; revisar o que virou 'essencial' nos "
        f"últimos meses."
    )
    return SuggestionDraft(
        section_id="S2",
        kind="lifestyle_creep",
        severity="warning",
        title="Investigar lifestyle creep nas despesas essenciais",
        rationale=rationale,
        dedup_key=_dedup_key("lifestyle_creep", bucket=_pct_bucket(excesso, step=2.5)),
    )


def rule_renda_passiva_real_baixa(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    """IF >50% mas renda passiva cobre <30% do custo de vida (Perini "300")."""
    goals = _as_dict(snapshot.get("goals"))
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    # FP-001 — alias defensivo: snapshot real produzido por `build_e5_output`
    # expõe `if_pct` (paridade com IFProjection.to_legacy_dict). Aceitar os
    # dois nomes evita regra dormente quando o pipeline E5 alimenta direto.
    progresso = _as_float(goals.get("progresso_if_pct"))
    if progresso is None:
        progresso = _as_float(goals.get("if_pct"))
    # FP-001 — alias defensivo: snapshot real expõe renda passiva observada
    # em `goals.renda_passiva_mensal_observada_brl` (PassiveIncomeCalculator
    # · A8.3); legado/testes ainda usam `fluxo.renda_passiva_mensal_atual`.
    renda_passiva = _as_float(fluxo.get("renda_passiva_mensal_atual"))
    if renda_passiva is None:
        renda_passiva = _as_float(goals.get("renda_passiva_mensal_observada_brl"))
    # `despesa_mensal_media` está no top-level do fluxo enriquecido. Em snapshots
    # antigos pode estar em `fluxo.janela_12m.despesa_mensal_media`.
    custo_vida = _as_float(fluxo.get("despesa_mensal_media"))
    if custo_vida is None:
        janela = _as_dict(fluxo.get("janela_12m"))
        custo_vida = _as_float(janela.get("despesa_mensal_media"))
    if progresso is None or renda_passiva is None or custo_vida is None:
        return None
    if custo_vida <= 0 or progresso < cfg.renda_passiva_min_progresso_if_pct:
        return None
    ratio = renda_passiva / custo_vida
    if ratio >= cfg.renda_passiva_target_ratio:
        return None
    pct_atual = ratio * 100
    pct_meta = cfg.renda_passiva_target_ratio * 100
    rationale = (
        f"Patrimônio já passou de {progresso:.0f}% da meta IF, mas a renda "
        f"passiva recorrente cobre apenas {pct_atual:.0f}% do custo de vida "
        f"(R$ {renda_passiva:,.0f} vs R$ {custo_vida:,.0f}/mês). "
        f"Perini sugere alvo intermediário de {pct_meta:.0f}% — convém "
        f"realocar parte da carteira para ativos geradores de fluxo (FIIs, "
        f"dividendos, debêntures de pagamento)."
    ).replace(",", ".")
    return SuggestionDraft(
        section_id="S7",
        kind="renda_passiva_real_baixa",
        severity="info",
        title=f"Aumentar geração de renda passiva ({pct_atual:.0f}% do custo)",
        rationale=rationale,
        dedup_key=_dedup_key("renda_passiva_real_baixa", bucket=_pct_bucket(pct_atual, step=5)),
    )


# =============================================================================
# Registry público (tabela ordenada de regras)
# =============================================================================


ALL_RULES = (
    # v1 (ADR-153)
    rule_trs_desalinhada,
    rule_reserva_insuficiente,
    rule_alocacao_fora_alvo,
    rule_aporte_abaixo_meta,
    # FP-003: rule_dolarizacao_atrasada removida (ADR-168 — Modo USA removido).
    # v2 (ADR-161)
    rule_endividamento_perigoso,
    rule_taxa_poupanca_caindo,
    rule_seguros_insuficientes,
    rule_concentracao_instituicao,
    rule_lifestyle_creep,
    rule_renda_passiva_real_baixa,
)
