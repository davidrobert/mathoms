"""Decision triggers T1-T5 da cascata fiscal — ADR-236 §D6."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional

from pipeline.domain.models.transaction import Money

#: Pró-labore mensal-alvo do T1 (= teto INSS empregado 2026).
T1_PRO_LABORE_ALVO_MENSAL: Decimal = Decimal("8157.41")
#: T1 só dispara se base PGBL atual < 80% do potencial otimizado.
PGBL_LIMITE_SUBOCUPADO_PCT: Decimal = Decimal("0.80")
#: T2 — proximidade de ±5pp do limiar 28% do fator-R.
T2_PROXIMIDADE_PP: Decimal = Decimal("0.05")
FATOR_R_LIMIAR: Decimal = Decimal("0.28")
#: T3 — IR marginal mínima (PGBL regressiva 10% empata em 22,5%).
T3_IR_MARGINAL_LIMIAR: Decimal = Decimal("0.225")
#: T4 — break-even literatura tributária PJ-aluguel.
T4_RECEITA_ALUGUEL_MIN_ANUAL: Decimal = Decimal("90000")
T4_IMOVEIS_MIN: int = 3
#: T5 — sublimite nacional ICMS/ISS (LC 123 art. 13-A).
SIMPLES_SUBLIMITE_NACIONAL: Decimal = Decimal("3600000")
T5_SUBLIMITE_PROXIMIDADE_PCT: Decimal = Decimal("0.80")
#: INSS patronal CPP — aplica só em Lucro Presumido (Simples inclui no DAS).
INSS_PATRONAL_ALIQ: Decimal = Decimal("0.20")
#: PGBL — art. 11 Lei 9.532/97.
PGBL_LIMITE_PCT: Decimal = Decimal("0.12")


@dataclass(frozen=True)
class CascataTrigger:
    """Decision trigger parametrizado — ADR-236 §D6."""

    code: Literal["T1", "T2", "T3", "T4", "T5"]
    severity: Literal["oportunidade", "atencao", "considere"]
    title: str
    params: dict


def _money_str(amount: Decimal) -> str:
    return str(amount.quantize(Decimal("0.01")))


def _pct_str(ratio: Decimal) -> str:
    return str((ratio * Decimal(100)).quantize(Decimal("0.01")))


def _ir_marginal_anual(renda_anual_brl: Decimal, irrf_table_mensal) -> Decimal:
    """Alíquota IR marginal a partir da renda anual posicionada na escala mensal."""
    if renda_anual_brl <= 0:
        return Decimal("0")
    mensal = renda_anual_brl / Decimal(12)
    if mensal <= irrf_table_mensal[0][0]:
        return Decimal("0")
    for limite, aliq, _ in irrf_table_mensal[1:]:
        if mensal <= limite:
            return aliq
    return Decimal("0.275")  # Faixa topo


def _t1_build_params(delta_anual: Decimal, ir_marginal: Decimal, regime: str) -> dict:
    custo_inss = delta_anual * INSS_PATRONAL_ALIQ if regime == "lucro_presumido" else Decimal(0)
    return {
        "delta_pro_labore_mensal_brl": _money_str(delta_anual / Decimal(12)),
        "delta_pro_labore_anual_brl": _money_str(delta_anual),
        "aporte_pgbl_extra_anual_brl": _money_str(delta_anual * PGBL_LIMITE_PCT),
        "economia_ir_anual_brl": _money_str(delta_anual * PGBL_LIMITE_PCT * ir_marginal),
        "custo_inss_patronal_anual_brl": _money_str(custo_inss),
        "ir_marginal_potencial_pct": _pct_str(ir_marginal),
    }


def _t1_eligible(
    pro_labore_mensal: Money, pgbl_base_anual: Money, pgbl_aplicavel: bool
) -> Optional[Decimal]:
    """Retorna `delta_anual` se T1 elegível, senão None."""
    if not pgbl_aplicavel or pro_labore_mensal.amount >= T1_PRO_LABORE_ALVO_MENSAL:
        return None
    delta_anual = (T1_PRO_LABORE_ALVO_MENSAL - pro_labore_mensal.amount) * Decimal(12)
    potencial = pgbl_base_anual.amount + delta_anual
    if potencial <= 0:
        return None
    if pgbl_base_anual.amount / potencial >= PGBL_LIMITE_SUBOCUPADO_PCT:
        return None
    return delta_anual


def _t1_otimizar_pro_labore(
    pro_labore_mensal: Money,
    pgbl_base_anual: Money,
    pgbl_aplicavel: bool,
    regime: str,
    irrf_table_mensal,
) -> Optional[CascataTrigger]:
    delta_anual = _t1_eligible(pro_labore_mensal, pgbl_base_anual, pgbl_aplicavel)
    if delta_anual is None:
        return None
    potencial = pgbl_base_anual.amount + delta_anual
    ir_marginal = _ir_marginal_anual(potencial, irrf_table_mensal)
    return CascataTrigger(
        code="T1",
        severity="considere",
        title="Considere avaliar a relação pró-labore × lucros distribuídos",
        params=_t1_build_params(delta_anual, ir_marginal, regime),
    )


def _t2_build_params(fator_r_pct: Decimal, delta_folha_anual: Decimal) -> dict:
    return {
        "fator_r_pct": _pct_str(fator_r_pct),
        "fator_r_limiar_pct": _pct_str(FATOR_R_LIMIAR),
        "delta_folha_anual_brl": _money_str(delta_folha_anual),
        "delta_folha_mensal_brl": _money_str(delta_folha_anual / Decimal(12)),
    }


def _t2_fator_r(
    fator_r_pct: Optional[Decimal] = None,
    folha_anual: Optional[Money] = None,
    receita_anual: Optional[Money] = None,
) -> Optional[CascataTrigger]:
    if fator_r_pct is None or receita_anual is None or receita_anual.amount <= 0:
        return None
    delta_pp = fator_r_pct - FATOR_R_LIMIAR
    if abs(delta_pp) > T2_PROXIMIDADE_PP:
        return None
    folha_atual = folha_anual.amount if folha_anual else Decimal(0)
    delta_folha = max(Decimal(0), FATOR_R_LIMIAR * receita_anual.amount - folha_atual)
    return CascataTrigger(
        code="T2",
        severity="atencao" if delta_pp < 0 else "considere",
        title="Sinal de atenção: fator-R próximo do corte Anexo III × V",
        params=_t2_build_params(fator_r_pct, delta_folha),
    )


def _t3_pgbl_marginal(
    pgbl_aplicavel: bool,
    pgbl_base_anual: Money,
    pgbl_limite_anual: Money,
    irrf_table_mensal,
) -> Optional[CascataTrigger]:
    if not pgbl_aplicavel or pgbl_base_anual.amount <= 0:
        return None
    ir_marginal = _ir_marginal_anual(pgbl_base_anual.amount, irrf_table_mensal)
    if ir_marginal < T3_IR_MARGINAL_LIMIAR:
        return None
    return CascataTrigger(
        code="T3",
        severity="oportunidade",
        title="Oportunidade: PGBL dedutível dentro do seu perfil",
        params={
            "ir_marginal_estimado_pct": _pct_str(ir_marginal),
            "pgbl_limite_anual_brl": _money_str(pgbl_limite_anual.amount),
        },
    )


def _t4_holding_alugueis(
    imoveis_count: int, receita_aluguel_anual: Money
) -> Optional[CascataTrigger]:
    if imoveis_count < T4_IMOVEIS_MIN:
        return None
    if receita_aluguel_anual.amount < T4_RECEITA_ALUGUEL_MIN_ANUAL:
        return None
    return CascataTrigger(
        code="T4",
        severity="considere",
        title="Considere avaliar holding patrimonial para aluguéis",
        params={
            "imoveis_alugados_count": imoveis_count,
            "receita_aluguel_anual_brl": _money_str(receita_aluguel_anual.amount),
        },
    )


def _t5_sublimite_simples(regime: str, receita_anual: Money) -> Optional[CascataTrigger]:
    if regime != "simples":
        return None
    threshold = SIMPLES_SUBLIMITE_NACIONAL * T5_SUBLIMITE_PROXIMIDADE_PCT
    if receita_anual.amount < threshold:
        return None
    return CascataTrigger(
        code="T5",
        severity="atencao",
        title="Sinal de atenção: receita próxima do sublimite Simples",
        params={
            "receita_anual_brl": _money_str(receita_anual.amount),
            "sublimite_brl": _money_str(SIMPLES_SUBLIMITE_NACIONAL),
            "distancia_brl": _money_str(SIMPLES_SUBLIMITE_NACIONAL - receita_anual.amount),
        },
    )


@dataclass(frozen=True)
class TriggerContext:
    """Contexto agregado para avaliação dos 5 triggers — ADR-236 §D6."""

    regime: str
    pro_labore_mensal: Money
    pgbl_base_anual: Money
    pgbl_limite_anual: Money
    pgbl_aplicavel: bool
    folha_anual: Money
    receita_anual: Money
    imoveis_alugados_count: int
    receita_aluguel_anual: Money
    irrf_table_mensal: object
    fator_r_pct: Optional[Decimal] = None


def _eval_candidates(ctx: TriggerContext) -> tuple:
    base = ctx.pgbl_base_anual
    aplicavel = ctx.pgbl_aplicavel
    irrf = ctx.irrf_table_mensal
    return (
        _t1_otimizar_pro_labore(ctx.pro_labore_mensal, base, aplicavel, ctx.regime, irrf),
        _t2_fator_r(ctx.fator_r_pct, ctx.folha_anual, ctx.receita_anual),
        _t3_pgbl_marginal(aplicavel, base, ctx.pgbl_limite_anual, irrf),
        _t4_holding_alugueis(ctx.imoveis_alugados_count, ctx.receita_aluguel_anual),
        _t5_sublimite_simples(ctx.regime, ctx.receita_anual),
    )


def compute_triggers(ctx: TriggerContext) -> tuple[CascataTrigger, ...]:
    """Avalia os 5 triggers canônicos T1-T5 — ADR-236 §D6."""
    return tuple(t for t in _eval_candidates(ctx) if t is not None)
