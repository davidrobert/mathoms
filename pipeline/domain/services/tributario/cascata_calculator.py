"""Calculator canônico da cascata fiscal PJ — ADR-236 §D3 (rules-as-code, ADR-143)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Optional

from pipeline.domain.models.transaction import Money
from pipeline.domain.services.tributario.cascata_triggers import (
    CascataTrigger,
    TriggerContext,
    compute_triggers,
)

# =============================================================================
# Constantes regulatórias 2026 (validadas com financial-planner 2026-05-21)
# =============================================================================

#: Anexo III — (RBT12_limite, alíq_nominal, parc_a_deduzir). LC 123 art. 18.
SIMPLES_ANEXO_III: tuple[tuple[Decimal, Decimal, Decimal], ...] = (
    (Decimal("180000"), Decimal("0.0600"), Decimal("0")),
    (Decimal("360000"), Decimal("0.1120"), Decimal("9360")),
    (Decimal("720000"), Decimal("0.1350"), Decimal("17640")),
    (Decimal("1800000"), Decimal("0.1600"), Decimal("35640")),
    (Decimal("3600000"), Decimal("0.2100"), Decimal("125640")),
    (Decimal("4800000"), Decimal("0.3300"), Decimal("648000")),
)

#: Anexo V — (RBT12_limite, alíq_nominal, parc_a_deduzir). LC 123 art. 18.
SIMPLES_ANEXO_V: tuple[tuple[Decimal, Decimal, Decimal], ...] = (
    (Decimal("180000"), Decimal("0.1550"), Decimal("0")),
    (Decimal("360000"), Decimal("0.1800"), Decimal("4500")),
    (Decimal("720000"), Decimal("0.1950"), Decimal("9900")),
    (Decimal("1800000"), Decimal("0.2050"), Decimal("17100")),
    (Decimal("3600000"), Decimal("0.2300"), Decimal("62100")),
    (Decimal("4800000"), Decimal("0.3050"), Decimal("540000")),
)

#: IRRF mensal — (base_mensal_limite, alíquota, parc_deduzir). MP 1.294/2025.
IRRF_TABELA_MENSAL: tuple[tuple[Decimal, Decimal, Decimal], ...] = (
    (Decimal("2428.80"), Decimal("0"), Decimal("0")),
    (Decimal("2826.65"), Decimal("0.075"), Decimal("182.16")),
    (Decimal("3751.05"), Decimal("0.15"), Decimal("394.16")),
    (Decimal("4664.68"), Decimal("0.225"), Decimal("675.49")),
)
IRRF_FAIXA_TOPO: tuple[Decimal, Decimal] = (Decimal("0.275"), Decimal("908.73"))

#: Teto contributivo INSS empregado 2026 (Portaria MPS dez/2025).
INSS_TETO_MENSAL: Decimal = Decimal("8157.41")
INSS_EMPREGADO_ALIQ: Decimal = Decimal("0.11")
INSS_PATRONAL_ALIQ: Decimal = Decimal("0.20")

#: MEI 2026 — DAS serviços (base SM R$ 1.518 + R$ 5 ISS). Comércio = R$ 75,90.
MEI_DAS_MENSAL_SERVICOS: Decimal = Decimal("79.90")
MEI_TETO_ANUAL: Decimal = Decimal("81000.00")

#: Presumido (serviços, presunção 32%). Lei 9.249/95 art. 15.
PRESUMIDO_PIS: Decimal = Decimal("0.0065")
PRESUMIDO_COFINS: Decimal = Decimal("0.03")
PRESUMIDO_PRESUNCAO_SERVICOS: Decimal = Decimal("0.32")
PRESUMIDO_IRPJ_BASICO: Decimal = Decimal("0.15")
PRESUMIDO_IRPJ_ADICIONAL: Decimal = Decimal("0.10")
PRESUMIDO_IRPJ_ADICIONAL_LIMITE_TRIM: Decimal = Decimal("60000")
PRESUMIDO_CSLL: Decimal = Decimal("0.09")

#: Fator-R — LC 123 §5º-J/K + Resolução CGSN 140/2018 art. 26.
FATOR_R_LIMIAR: Decimal = Decimal("0.28")

#: PGBL — art. 11 Lei 9.532/97.
PGBL_LIMITE_PCT: Decimal = Decimal("0.12")


# =============================================================================
# Value objects
# =============================================================================


@dataclass(frozen=True)
class CascataInput:
    """Input value object — ADR-236 §D3 + ADR-089 (ISP)."""

    regime: Optional[Literal["mei", "simples", "lucro_presumido", "lucro_real"]] = None
    anexo_simples: Optional[Literal["III", "V"]] = None
    iss_aliquota_pct: Optional[Decimal] = None
    tipo_declaracao_ir: Literal["completa", "simplificada"] = "completa"
    receita_pj_anual: Money = field(default_factory=lambda: Money.zero("BRL"))
    pro_labore_mensal: Money = field(default_factory=lambda: Money.zero("BRL"))
    lucros_distribuidos_mensal: Money = field(default_factory=lambda: Money.zero("BRL"))
    folha_pj_mensal: Money = field(default_factory=lambda: Money.zero("BRL"))
    das_pago_mensal: Money = field(default_factory=lambda: Money.zero("BRL"))
    iss_pago_mensal: Money = field(default_factory=lambda: Money.zero("BRL"))
    outras_rendas_tributaveis_pf_anual: Money = field(default_factory=lambda: Money.zero("BRL"))
    imoveis_alugados_count: int = 0
    receita_aluguel_anual: Money = field(default_factory=lambda: Money.zero("BRL"))


@dataclass(frozen=True)
class CascataOutput:
    """Cascata fiscal canônica — ADR-236 §D3."""

    regime: Optional[str]
    regime_label: str
    regime_nao_suportado: bool = False
    motivo_nao_suportado: Optional[str] = None
    receita_bruta: Money = field(default_factory=lambda: Money.zero("BRL"))
    tributos_federais: Money = field(default_factory=lambda: Money.zero("BRL"))
    iss_total: Money = field(default_factory=lambda: Money.zero("BRL"))
    lucro_contabil_pj: Money = field(default_factory=lambda: Money.zero("BRL"))
    pro_labore_bruto: Money = field(default_factory=lambda: Money.zero("BRL"))
    inss_patronal: Money = field(default_factory=lambda: Money.zero("BRL"))
    inss_empregado: Money = field(default_factory=lambda: Money.zero("BRL"))
    irrf_pro_labore: Money = field(default_factory=lambda: Money.zero("BRL"))
    lucros_distribuidos: Money = field(default_factory=lambda: Money.zero("BRL"))
    renda_pf_tributavel_total: Money = field(default_factory=lambda: Money.zero("BRL"))
    carga_total_pct: Decimal = Decimal("0")
    pgbl_base_anual: Money = field(default_factory=lambda: Money.zero("BRL"))
    pgbl_limite_anual: Money = field(default_factory=lambda: Money.zero("BRL"))
    pgbl_aplicavel: bool = False
    pgbl_motivo_inaplicavel: Optional[str] = None
    fator_r_pct: Optional[Decimal] = None
    fator_r_faixa: Optional[Literal["anexo_iii", "anexo_v"]] = None
    fator_r_break_even_mensal: Optional[Money] = None
    triggers: tuple[CascataTrigger, ...] = ()


@dataclass(frozen=True)
class _ProLaboreCargas:
    """Cargas anualizadas sobre pró-labore (intermediário)."""

    bruto_anual: Money
    inss_empregado_anual: Money
    irrf_anual: Money
    inss_patronal_anual: Money


# =============================================================================
# Helpers progressivos
# =============================================================================


def compute_irrf_mensal(base_tributavel_mensal: Money) -> Money:
    """IRRF mensal sobre base tributável (já deduzido INSS empregado) — MP 1.294/2025."""
    base = base_tributavel_mensal.amount
    if base <= IRRF_TABELA_MENSAL[0][0]:
        return Money.zero("BRL")
    for limite, aliq, deduzir in IRRF_TABELA_MENSAL[1:]:
        if base <= limite:
            return Money.brl(base * aliq - deduzir)
    aliq_topo, deduzir_topo = IRRF_FAIXA_TOPO
    return Money.brl(base * aliq_topo - deduzir_topo)


def compute_simples_aliquota_efetiva(
    rbt12: Money, tabela: tuple[tuple[Decimal, Decimal, Decimal], ...]
) -> Decimal:
    """Alíquota efetiva Simples — (RBT12 × nom − parc_deduzir) / RBT12."""
    rbt = rbt12.amount
    if rbt <= 0:
        return Decimal("0")
    for limite, aliq_nom, parc in tabela:
        if rbt <= limite:
            efetiva = (rbt * aliq_nom - parc) / rbt
            return max(Decimal("0"), efetiva)
    return Decimal("0")  # Acima do teto Simples — caller trata.


def _compute_pro_labore_cargas(pro_labore_mensal: Money, regime: str) -> _ProLaboreCargas:
    """Cargas anuais sobre pró-labore. CPP patronal só em Presumido (Simples inclui no DAS)."""
    bruto = pro_labore_mensal.amount
    pro_labore_para_inss = min(bruto, INSS_TETO_MENSAL)
    inss_emp_mensal = pro_labore_para_inss * INSS_EMPREGADO_ALIQ
    irrf_base_mensal = bruto - inss_emp_mensal
    irrf_mensal = compute_irrf_mensal(Money.brl(irrf_base_mensal))
    patronal_anual = (
        Money.brl(bruto * INSS_PATRONAL_ALIQ * Decimal(12))
        if regime == "lucro_presumido"
        else Money.zero("BRL")
    )
    return _ProLaboreCargas(
        bruto_anual=Money.brl(bruto * Decimal(12)),
        inss_empregado_anual=Money.brl(inss_emp_mensal * Decimal(12)),
        irrf_anual=Money.brl(irrf_mensal.amount * Decimal(12)),
        inss_patronal_anual=patronal_anual,
    )


# =============================================================================
# Regime-specific cascata builders
# =============================================================================


def _regime_label(regime: Optional[str] = None, anexo: Optional[str] = None) -> str:
    if regime == "simples":
        return f"Simples Nacional — Anexo {anexo}" if anexo else "Simples Nacional"
    if regime == "lucro_presumido":
        return "Lucro Presumido"
    if regime == "mei":
        return "MEI"
    if regime == "lucro_real":
        return "Lucro Real"
    return "Perfil tributário incompleto"


def _build_simples_tributos(receita: Money, anexo: str) -> tuple[Money, Money]:
    tabela = SIMPLES_ANEXO_III if anexo == "III" else SIMPLES_ANEXO_V
    aliq_efetiva = compute_simples_aliquota_efetiva(receita, tabela)
    tributos = Money.brl(receita.amount * aliq_efetiva)
    return tributos, Money.zero("BRL")  # ISS embutido no DAS


def _build_presumido_tributos(
    receita: Money, iss_aliquota_pct: Optional[Decimal] = None
) -> tuple[Money, Money]:
    receita_amt = receita.amount
    pis = receita_amt * PRESUMIDO_PIS
    cofins = receita_amt * PRESUMIDO_COFINS
    receita_trim = receita_amt / Decimal(4)
    base_presumida_trim = receita_trim * PRESUMIDO_PRESUNCAO_SERVICOS
    irpj_basico_trim = base_presumida_trim * PRESUMIDO_IRPJ_BASICO
    excedente_trim = max(Decimal(0), base_presumida_trim - PRESUMIDO_IRPJ_ADICIONAL_LIMITE_TRIM)
    irpj_adicional_trim = excedente_trim * PRESUMIDO_IRPJ_ADICIONAL
    irpj_anual = (irpj_basico_trim + irpj_adicional_trim) * Decimal(4)
    csll_anual = base_presumida_trim * PRESUMIDO_CSLL * Decimal(4)
    tributos = Money.brl(pis + cofins + irpj_anual + csll_anual)
    iss = (
        Money.brl(receita_amt * (iss_aliquota_pct / Decimal(100)))
        if iss_aliquota_pct
        else Money.zero("BRL")
    )
    return tributos, iss


def _build_mei_tributos() -> tuple[Money, Money]:
    das_anual = MEI_DAS_MENSAL_SERVICOS * Decimal(12)
    return Money.brl(das_anual), Money.zero("BRL")


def _dispatch_tributos(inp: CascataInput) -> tuple[Money, Money]:
    if inp.regime == "simples":
        return _build_simples_tributos(inp.receita_pj_anual, inp.anexo_simples or "V")
    if inp.regime == "lucro_presumido":
        return _build_presumido_tributos(inp.receita_pj_anual, inp.iss_aliquota_pct)
    return _build_mei_tributos()


# =============================================================================
# PGBL + fator-R
# =============================================================================


def _compute_pgbl(
    renda_pf_tributavel_total: Money, tipo_declaracao_ir: str
) -> tuple[Money, bool, Optional[str]]:
    """Retorna (limite_anual, aplicavel, motivo_inaplicavel)."""
    limite = Money.brl(renda_pf_tributavel_total.amount * PGBL_LIMITE_PCT)
    if tipo_declaracao_ir == "simplificada":
        return limite, False, "declaracao_simplificada"
    if renda_pf_tributavel_total.amount <= 0:
        return limite, False, "renda_tributavel_pf_zerada"
    return limite, True, None


def _compute_fator_r(
    folha_pj_mensal: Money, pro_labore_mensal: Money, receita_anual: Money
) -> tuple[Optional[Decimal], Optional[str], Optional[Money]]:
    """Retorna (fator_r_pct, faixa, break_even_mensal)."""
    if receita_anual.amount <= 0:
        return None, None, None
    folha_anual = (folha_pj_mensal.amount + pro_labore_mensal.amount) * Decimal(12)
    fator_r = folha_anual / receita_anual.amount
    faixa = "anexo_iii" if fator_r >= FATOR_R_LIMIAR else "anexo_v"
    break_even_anual = max(Decimal(0), FATOR_R_LIMIAR * receita_anual.amount - folha_anual)
    return fator_r, faixa, Money.brl(break_even_anual / Decimal(12))


def _compute_carga_total_pct(
    receita: Money, tributos: Money, iss: Money, inss_patronal: Money, irrf: Money
) -> Decimal:
    if receita.amount <= 0:
        return Decimal("0")
    return (tributos.amount + iss.amount + inss_patronal.amount + irrf.amount) / receita.amount


# =============================================================================
# API pública
# =============================================================================


def compute(inp: CascataInput) -> CascataOutput:
    """Computa a cascata fiscal canônica — ADR-236 §D3."""
    if inp.regime is None:
        return _output_fallback(inp, "perfil_incompleto")
    if inp.regime == "lucro_real":
        return _output_fallback(inp, "lucro_real")
    if inp.regime == "simples" and inp.anexo_simples is None:
        return _output_fallback(inp, "anexo_simples_pendente")
    return _compute_full_cascata(inp)


@dataclass(frozen=True)
class _ComputedLayers:
    cargas: _ProLaboreCargas
    tributos_federais: Money
    iss_total: Money
    lucros_anual: Money
    lucro_contabil: Money
    renda_pf_tributavel: Money
    pgbl_limite: Money
    pgbl_aplicavel: bool
    pgbl_motivo: Optional[str]
    fator_r_pct: Optional[Decimal]
    fator_r_faixa: Optional[str]
    fator_r_break_even: Optional[Money]


def _compute_lucro_contabil(inp: CascataInput, cargas, tributos, iss) -> Money:
    return Money.brl(
        inp.receita_pj_anual.amount
        - tributos.amount
        - iss.amount
        - cargas.bruto_anual.amount
        - cargas.inss_patronal_anual.amount
    )


def _compute_fator_r_if_simples(inp: CascataInput) -> tuple:
    if inp.regime != "simples":
        return (None, None, None)
    return _compute_fator_r(inp.folha_pj_mensal, inp.pro_labore_mensal, inp.receita_pj_anual)


def _compute_layers(inp: CascataInput) -> _ComputedLayers:
    cargas = _compute_pro_labore_cargas(inp.pro_labore_mensal, inp.regime)
    tributos, iss = _dispatch_tributos(inp)
    renda_pf = Money.brl(cargas.bruto_anual.amount + inp.outras_rendas_tributaveis_pf_anual.amount)
    pgbl_limite, pgbl_aplicavel, pgbl_motivo = _compute_pgbl(renda_pf, inp.tipo_declaracao_ir)
    fator_r = _compute_fator_r_if_simples(inp)
    return _ComputedLayers(
        cargas=cargas,
        tributos_federais=tributos,
        iss_total=iss,
        lucros_anual=Money.brl(inp.lucros_distribuidos_mensal.amount * Decimal(12)),
        lucro_contabil=_compute_lucro_contabil(inp, cargas, tributos, iss),
        renda_pf_tributavel=renda_pf,
        pgbl_limite=pgbl_limite,
        pgbl_aplicavel=pgbl_aplicavel,
        pgbl_motivo=pgbl_motivo,
        fator_r_pct=fator_r[0],
        fator_r_faixa=fator_r[1],
        fator_r_break_even=fator_r[2],
    )


def _build_trigger_context(inp: CascataInput, layers: _ComputedLayers) -> TriggerContext:
    folha_anual = Money.brl(
        (inp.folha_pj_mensal.amount + inp.pro_labore_mensal.amount) * Decimal(12)
    )
    return TriggerContext(
        regime=inp.regime,
        pro_labore_mensal=inp.pro_labore_mensal,
        pgbl_base_anual=layers.renda_pf_tributavel,
        pgbl_limite_anual=layers.pgbl_limite,
        pgbl_aplicavel=layers.pgbl_aplicavel,
        fator_r_pct=layers.fator_r_pct,
        folha_anual=folha_anual,
        receita_anual=inp.receita_pj_anual,
        imoveis_alugados_count=inp.imoveis_alugados_count,
        receita_aluguel_anual=inp.receita_aluguel_anual,
        irrf_table_mensal=IRRF_TABELA_MENSAL,
    )


def _compute_full_cascata(inp: CascataInput) -> CascataOutput:
    layers = _compute_layers(inp)
    triggers = compute_triggers(_build_trigger_context(inp, layers))
    return _assemble_output(inp, layers, triggers)


def _cascata_fields(inp: CascataInput, layers: _ComputedLayers) -> dict:
    return {
        "receita_bruta": inp.receita_pj_anual,
        "tributos_federais": layers.tributos_federais,
        "iss_total": layers.iss_total,
        "lucro_contabil_pj": layers.lucro_contabil,
        "pro_labore_bruto": layers.cargas.bruto_anual,
        "inss_patronal": layers.cargas.inss_patronal_anual,
        "inss_empregado": layers.cargas.inss_empregado_anual,
        "irrf_pro_labore": layers.cargas.irrf_anual,
        "lucros_distribuidos": layers.lucros_anual,
        "renda_pf_tributavel_total": layers.renda_pf_tributavel,
        "carga_total_pct": _compute_carga_total_pct(
            inp.receita_pj_anual,
            layers.tributos_federais,
            layers.iss_total,
            layers.cargas.inss_patronal_anual,
            layers.cargas.irrf_anual,
        ),
    }


def _pgbl_fields(layers: _ComputedLayers) -> dict:
    return {
        "pgbl_base_anual": layers.renda_pf_tributavel,
        "pgbl_limite_anual": layers.pgbl_limite,
        "pgbl_aplicavel": layers.pgbl_aplicavel,
        "pgbl_motivo_inaplicavel": layers.pgbl_motivo,
        "fator_r_pct": layers.fator_r_pct,
        "fator_r_faixa": layers.fator_r_faixa,
        "fator_r_break_even_mensal": layers.fator_r_break_even,
    }


def _assemble_output(
    inp: CascataInput, layers: _ComputedLayers, triggers: tuple[CascataTrigger, ...]
) -> CascataOutput:
    return CascataOutput(
        regime=inp.regime,
        regime_label=_regime_label(inp.regime, inp.anexo_simples),
        regime_nao_suportado=False,
        motivo_nao_suportado=None,
        triggers=triggers,
        **_cascata_fields(inp, layers),
        **_pgbl_fields(layers),
    )


def _output_fallback(inp: CascataInput, motivo: str) -> CascataOutput:
    return CascataOutput(
        regime=inp.regime,
        regime_label=_regime_label(inp.regime, inp.anexo_simples),
        regime_nao_suportado=True,
        motivo_nao_suportado=motivo,
    )
